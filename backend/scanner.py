##漏洞扫描模块
###输入csv或者txt的域名
###调用漏洞库自动进行扫描，这一步可以直接放简单的web攻击（一些直接改搜索的域名就攻击成功的），也可以调用playwright
###调用open source工具如Xray、Nuclei、自定义poc

from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3

scanner_bp = Blueprint('scanner', __name__)
