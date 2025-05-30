from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uvicorn
from datetime import datetime, timedelta
from typing import List, Optional
import asyncio
import logging

from database import get_db, engine, Base
from auth.models import User
from auth.schemas import UserCreate, UserResponse, Token
from auth.utils import create_access_token, verify_password, get_password_hash, verify_token
from scanner.models import ScanTask, Vulnerability
from scanner.schemas import ScanTaskCreate, ScanTaskResponse, ScanReportResponse
from scanner.scanner_engine import VulnerabilityScanner

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Web漏洞挖掘系统API",
    description="面向开发者与安全测试人员的Web漏洞挖掘平台后端API",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT认证
security = HTTPBearer()

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 依赖注入：获取当前用户
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

@app.get("/")
async def root():
    return {"message": "Web漏洞挖掘系统API", "version": "1.0.0"}

# 用户认证相关接口
@app.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # 检查用户是否已存在
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"New user registered: {user.email}")
    # 将用户对象转换为字典
    user_dict = {
        "id": str(user.id),
        "email": user.email,
        "is_admin": user.is_admin,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }
    return user_dict

@app.post("/login", response_model=Token)
async def login(user_data: UserCreate, db: Session = Depends(get_db)):
    # 验证用户
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # 生成访问令牌
    access_token = create_access_token(data={"sub": str(user.id)})
    
    logger.info(f"User logged in: {user.email}")
    
    # 将用户对象转换为字典
    user_dict = {
        "id": str(user.id),
        "email": user.email,
        "is_admin": user.is_admin,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_dict
    }

@app.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# 扫描任务相关接口
@app.post("/scan", response_model=ScanTaskResponse)
async def create_scan_task(
    scan_data: ScanTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 创建扫描任务
    task = ScanTask(
        url=scan_data.url,
        user_id=current_user.id,
        status="pending",
        created_at=datetime.utcnow()
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # 异步启动扫描
    asyncio.create_task(run_scan_task(task.id, db))
    
    logger.info(f"Scan task created: {task.id} for URL: {scan_data.url}")
    return task

@app.get("/scans", response_model=List[ScanTaskResponse])
async def get_scan_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tasks = db.query(ScanTask).filter(ScanTask.user_id == current_user.id).order_by(ScanTask.created_at.desc()).all()
    return tasks

@app.get("/scan/{task_id}", response_model=ScanReportResponse)
async def get_scan_report(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(ScanTask).filter(
        ScanTask.id == task_id,
        ScanTask.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan task not found"
        )
    
    # 获取漏洞列表
    vulnerabilities = db.query(Vulnerability).filter(Vulnerability.scan_task_id == task_id).all()
    
    return {
        "id": task.id,
        "url": task.url,
        "status": task.status,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
        "vulnerabilities": vulnerabilities
    }

# 异步扫描任务执行
async def run_scan_task(task_id: str, db: Session):
    try:
        # 获取任务
        task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
        if not task:
            return
        
        # 更新状态为运行中
        task.status = "running"
        db.commit()
        
        # 执行扫描
        scanner = VulnerabilityScanner()
        vulnerabilities = await scanner.scan_website(task.url)
        
        # 保存漏洞结果
        for vuln_data in vulnerabilities:
            vulnerability = Vulnerability(
                scan_task_id=task_id,
                type=vuln_data["type"],
                payload=vuln_data["payload"],
                location=vuln_data["location"],
                description=vuln_data["description"],
                severity=vuln_data["severity"]
            )
            db.add(vulnerability)
        
        # 更新任务状态
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.vulnerabilities_count = len(vulnerabilities)
        
        db.commit()
        logger.info(f"Scan task completed: {task_id}, found {len(vulnerabilities)} vulnerabilities")
        
    except Exception as e:
        # 更新任务状态为失败
        task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
        if task:
            task.status = "failed"
            db.commit()
        
        logger.error(f"Scan task failed: {task_id}, error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
