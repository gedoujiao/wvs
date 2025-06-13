##资产扫描模块
###输入ip*/域名*/邮箱/用户名/公司名……
###扫描1.子域名 2.公司相关服务器 3.开放端口、开放服务……
###输出一个csv文件

from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3

asset_bp = Blueprint('asset', __name__)


@asset_bp.route('/asset', methods=['GET', 'POST'])
def asset():
    print("hi")
    
