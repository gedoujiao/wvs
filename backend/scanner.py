##漏洞扫描模块
###输入csv或者txt的域名
###调用漏洞库自动进行扫描，这一步可以直接放简单的web攻击（一些直接改搜索的域名就攻击成功的），也可以调用playwright
###调用open source工具如Xray、Nuclei、自定义poc

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import os
import tempfile
import subprocess
import uuid

scanner_bp = Blueprint('scanner', __name__, url_prefix='/scanner')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@scanner_bp.route('/', methods=['GET', 'POST'])
def scanner_home():
    if request.method == 'GET':
        return render_template('scanner.html')

    # POST - 文件上传并执行扫描
    file = request.files.get('target_file')

    if not file:
        flash("请上传 CSV 或 TXT 文件", 'danger')
        return redirect(url_for('scanner.scanner_home'))

    filename = f"{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # 扫描结果保存
    results = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            target = line.strip()
            if not target:
                continue

            # 模拟简单扫描逻辑（你可以换成实际调用）
            result = fake_scan(target)
            results.append({
                'target': target,
                'status': result
            })

    return render_template('scanner.html', results=results)


def fake_scan(domain):
    # 简单模拟漏洞结果（也可以替换为 Xray、Nuclei、Playwright 等）
    if "test" in domain:
        return "发现 SQL 注入"
    elif "admin" in domain:
        return "发现弱口令后台"
    else:
        return "未发现已知漏洞"


import subprocess

def run_nuclei(domain):
    nuclei_path = r"D:\tools\nuclei\nuclei.exe"
    try:
        result = subprocess.check_output(
            [nuclei_path, "-u", domain, "-silent"],
            stderr=subprocess.STDOUT,
            timeout=30
        )
        return result.decode('utf-8') or "未发现漏洞"
    except subprocess.TimeoutExpired:
        return "Nuclei 扫描超时"
    except subprocess.CalledProcessError as e:
        return f"扫描失败: {e.output.decode('utf-8')}"
    except Exception as e:
        return f"系统错误: {str(e)}"
    
import subprocess
import os
import uuid

def run_xray(domain):
    xray_path = r"D:\tools\xray\xray.exe"
    report_path = os.path.join("uploads", f"xray_report_{uuid.uuid4().hex}.html")

    try:
        result = subprocess.run(
            [xray_path, "webscan", "--url", domain, "--html-output", report_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )
        if os.path.exists(report_path):
            return f"生成报告成功: {report_path}"
        else:
            return f"执行完成但未生成报告\n{result.stdout.decode('utf-8')}"
    except subprocess.TimeoutExpired:
        return "Xray 扫描超时"
    except Exception as e:
        return f"Xray 错误: {str(e)}"

