from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from database import Base

class ScanTask(Base):
    __tablename__ = "scan_tasks"
    
    # 将 UUID 类型替换为 String 类型
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    url = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, failed
    vulnerabilities_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 关系
    vulnerabilities = relationship("Vulnerability", back_populates="scan_task")

class Vulnerability(Base):
    __tablename__ = "vulnerabilities"
    
    # 将 UUID 类型替换为 String 类型
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    scan_task_id = Column(String, ForeignKey("scan_tasks.id"), nullable=False)
    type = Column(String, nullable=False)  # xss, sqli, csrf, etc.
    payload = Column(Text, nullable=False)
    location = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, nullable=False)  # low, medium, high, critical
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    scan_task = relationship("ScanTask", back_populates="vulnerabilities")