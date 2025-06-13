web_vuln_scanner/
├── main.py                     # 启动入口
├── initsystem.py              # 初始化数据库脚本
├── config.py                  # 配置文件，如数据库、密钥等
├── requirements.txt
├── static/                    # 静态资源（JS、CSS、图标）
├── templates/                 # HTML模板页面
│   ├── base.html              # 基础模板
│   ├── login.html
│   ├── dashboard.html
│   └── ...
├── module/                    # 后端模块
│   ├── __init__.py
│   ├── user.py                # 用户管理模块
│   ├── asset.py               # 资产模块
│   ├── scanner.py             # 扫描功能模块
│   └── report.py             # PDF报告模块
└── models/                    # 数据模型
    ├── __init__.py
    ├── user_model.py
    ├── asset_model.py
    └── scan_model.py
