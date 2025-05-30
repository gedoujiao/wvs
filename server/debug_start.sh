#!/bin/bash

echo "🚀 启动Web漏洞扫描系统调试模式..."

# 检查Python版本
echo "📋 检查Python版本..."
python --version

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📥 安装Python依赖..."
pip install -r requirements.txt

# 安装Playwright
echo "🎭 安装Playwright浏览器..."
playwright install chromium

# 检查数据库文件
if [ ! -f "vulnerability_scanner.db" ]; then
    echo "🗄️ 初始化数据库..."
    python -c "
from database import engine, Base
from auth.models import User
from scanner.models import ScanTask, Vulnerability
Base.metadata.create_all(bind=engine)
print('数据库初始化完成')
"
fi

# 设置环境变量
export SECRET_KEY="debug-secret-key-change-in-production"
export DATABASE_URL="sqlite:///./vulnerability_scanner.db"

echo "🌐 启动API服务器 (调试模式)..."
echo "📡 API地址: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/docs"
echo "🔍 调试面板: http://localhost:3000/debug"

# 启动服务器
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
