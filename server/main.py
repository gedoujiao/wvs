from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uvicorn
from datetime import datetime, timedelta
from typing import List, Optional
import asyncio
import logging
from passlib.context import CryptContext
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

def model_to_dict(model):
    """将 SQLAlchemy 模型实例转换为字典"""
    data = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        if isinstance(value, datetime):
            # 处理日期时间类型
            value = value.strftime("%Y-%m-%d %H:%M:%S")
        data[column.name] = value
    return data

@app.get("/")
async def root():
    return {"message": "Web漏洞挖掘系统API", "version": "1.0.0"}

@app.get("/users", response_model=List[UserResponse])
async def get_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以访问用户列表"
        )
    users = db.query(User).all()
    return [model_to_dict(user) for user in users]
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# 修改用户信息
@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以修改用户信息"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户未找到"
        )
    # 验证邮箱格式
    if not user_data.email or "@" not in user_data.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="邮箱格式不正确"
        )
    # 验证密码长度
    if len(user_data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="密码长度不能少于6位"
        )
    user.email = user_data.email
    user.hashed_password = pwd_context.hash(user_data.password)
    db.commit()
    db.refresh(user)
    return model_to_dict(user)

# 删除用户
@app.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以删除用户"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户未找到"
        )
    db.delete(user)
    db.commit()
    return {"message": "用户删除成功"}

# 用户认证相关接口
@app.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, is_admin: bool = False, db: Session = Depends(get_db)):
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
        is_admin=is_admin  # 根据参数设置是否为管理员
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
    
    user_dict = model_to_dict(user)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_dict
    }

@app.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return model_to_dict(current_user)

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
    return model_to_dict(task)

@app.get("/scans", response_model=List[ScanTaskResponse])
async def get_scan_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tasks = db.query(ScanTask).filter(ScanTask.user_id == current_user.id).order_by(ScanTask.created_at.desc()).all()
    return [model_to_dict(task) for task in tasks]

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
    
    task_dict = model_to_dict(task)
    task_dict["vulnerabilities"] = [model_to_dict(vuln) for vuln in vulnerabilities]
    
    return task_dict

scan_logs: dict[str, list[str]] = {}

# 异步扫描任务执行
async def run_scan_task(task_id: str, db: Session):
    async def progress_logger(msg: str):
        scan_logs.setdefault(task_id, []).append(msg)

    try:
        task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
        if not task:
            return

        task.status = "running"
        db.commit()

        scanner = VulnerabilityScanner()
        scanner.progress_callback = progress_logger
        vulnerabilities = await scanner.scan_website(task.url)

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

        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.vulnerabilities_count = len(vulnerabilities)

        db.commit()
        logger.info(f"Scan task completed: {task_id}, found {len(vulnerabilities)} vulnerabilities")

    except Exception as e:
        task = db.query(ScanTask).filter(ScanTask.id == task_id).first()
        if task:
            task.status = "failed"
            db.commit()

        logger.error(f"Scan task failed: {task_id}, error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)