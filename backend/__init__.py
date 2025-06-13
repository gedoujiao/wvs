# 导入各个功能模块的蓝图
from .asset import asset_bp
from .scanner import scanner_bp
from .user import user_bp


# 集中暴露所有蓝图列表，用于 main.py 自动注册
blueprints = [
    asset_bp,
    scanner_bp,
    user_bp
]