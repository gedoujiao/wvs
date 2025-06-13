##用户管理模块
###注册
###用户身份权限管理
###登录
###数据库信息存放
from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3

user_bp = Blueprint('user', __name__)
