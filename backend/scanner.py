# backend/scanner.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, send_file
import os
import subprocess
import uuid
import requests
import re
import csv
import threading
from io import StringIO

scanner_bp = Blueprint('scanner', __name__, url_prefix='/scanner')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

scan_tasks = {}  # 内存中保存任务状态和结果

@scanner_bp.route('/', methods=['GET'])
def scanner_home():
    return render_template('scanner.html')

@scanner_bp.route('/', methods=['POST'])
def start_scan():
    file = request.files.get('target_file')
    manual_targets = request.form.get('manual_targets', '').strip()
    targets = []

    if file and file.filename.endswith(('.txt', '.csv')):
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            targets.extend([line.strip() for line in f if line.strip()])

    if manual_targets:
        targets.extend([line.strip() for line in manual_targets.splitlines() if line.strip()])

    targets = list(set(targets))

    task_id = uuid.uuid4().hex
    scan_tasks[task_id] = {'progress': 0, 'status': 'running', 'results': []}

    threading.Thread(target=background_scan, args=(task_id, targets)).start()
    return jsonify({'task_id': task_id})

@scanner_bp.route('/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    task = scan_tasks.get(task_id)
    if not task:
        return jsonify({'progress': 0, 'status': 'not_found'})
    return jsonify({
        'progress': task['progress'],
        'status': task['status'],
        'current_target': task.get('current_target', '未知')
    })
@scanner_bp.route('/results/<task_id>', methods=['GET'])
def get_results_by_task(task_id):
    task = scan_tasks.get(task_id)
    if not task:
        flash("任务未找到", "danger")
        return redirect(url_for('scanner.scanner_home'))
    return render_template('scanner.html', results=task['results'], task_id=task_id)

from io import BytesIO, TextIOWrapper

from io import BytesIO

@scanner_bp.route('/results/export/<task_id>', methods=['GET'])
def export_csv(task_id):
    task = scan_tasks.get(task_id)
    if not task:
        return "任务不存在", 404

    # 使用字符串缓冲区写入数据，避免 TextIOWrapper 关闭底层 BytesIO
    output_str = "目标,省份,漏洞名称,严重等级,位置/描述\n"
    for item in task['results']:
        for vuln in item.get('details', []):
            row = f"{item['target']},{item['province']},{vuln['name']},{vuln['severity']},{vuln['location']}\n"
            output_str += row

    output_bytes = BytesIO()
    output_bytes.write(output_str.encode('utf-8-sig'))
    output_bytes.seek(0)

    return send_file(output_bytes, mimetype='text/csv', as_attachment=True, download_name='scan_results.csv')




def background_scan(task_id, targets):
    total = len(targets)
    results = []
    for i, target in enumerate(targets):
        print(f"[{task_id}] 正在扫描：{target}")
        scan_tasks[task_id]['current_target'] = target
        raw_output = run_nuclei(target)
        summary, details = analyze_nuclei_output(raw_output)
        province = get_province_from_ip(target)

        results.append({
            'target': target,
            'province': province,
            'vuln_count': summary['count'],
            'severities': summary['severities'],
            'raw': raw_output,
            'details': details
        })

        scan_tasks[task_id]['progress'] = int(((i + 1) / total) * 100)

    scan_tasks[task_id]['status'] = 'finished'
    scan_tasks[task_id]['results'] = results
    scan_tasks[task_id]['current_target'] = None
    

    print(f"[{task_id}] 扫描完成")

def run_nuclei(domain):
    nuclei_path = r"D:\\Desktop\\wvs\\tools\\nuclei\\nuclei.exe"
    try:
        result = subprocess.check_output(
            [nuclei_path, "-u", domain, "-severity", "low,medium,high,critical"],
            stderr=subprocess.STDOUT,
            timeout=300
        )
        return strip_ansi_codes(result.decode('utf-8'))
    except subprocess.TimeoutExpired:
        return "[Nuclei 扫描超时]"
    except subprocess.CalledProcessError as e:
        return f"[Nuclei 扫描失败] {strip_ansi_codes(e.output.decode('utf-8'))}"
    except Exception as e:
        return f"[系统错误] {str(e)}"

def strip_ansi_codes(text):
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

def analyze_nuclei_output(output):
    severities = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
    count = 0
    details = []

    for line in output.splitlines():
        match = re.search(r'\[(low|medium|high|critical)\]', line, re.IGNORECASE)
        if match:
            sev = match.group(1).lower()
            if sev in severities:
                severities[sev] += 1
                count += 1
                vuln_name = re.search(r'^\[?([^\]:]+)', line)
                location = re.search(r'(https?://[^\s]+|[\d\.]+:\d+)', line)
                details.append({
                    'name': vuln_name.group(1) if vuln_name else '未知',
                    'severity': sev,
                    'location': location.group(1) if location else ''
                })

    return {'count': count, 'severities': severities}, details

def get_province_from_ip(ip_or_domain):
    try:
        url = f"http://ip-api.com/json/{ip_or_domain}?lang=zh-CN"
        response = requests.get(url, timeout=5)
        data = response.json()
        return data.get("regionName", "未知") if data.get("status") == "success" else "未知"
    except Exception:
        return "未知"
