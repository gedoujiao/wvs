#!/bin/bash

# 启动脚本
echo "Starting Web Vulnerability Scanner API..."

# 检查是否安装了依赖
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "Installing dependencies..."
pip install -r requirements.txt

# 安装Playwright浏览器
echo "Installing Playwright browsers..."
playwright install chromium

# 启动API服务器
echo "Starting FastAPI server..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
