# redb.py 文件
from database import engine, Base
from auth.models import User
from scanner.models import ScanTask, Vulnerability

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print('数据库初始化完成')