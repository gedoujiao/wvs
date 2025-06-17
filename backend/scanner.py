from flask import Blueprint, render_template, request, redirect, url_for, flash
import os
import subprocess
import uuid

scanner_bp = Blueprint('scanner', __name__, url_prefix='/scanner')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@scanner_bp.route('/', methods=['GET', 'POST'])
def scanner_home():
    if request.method == 'GET':
        return render_template('scanner.html')

    file = request.files.get('target_file')
    if not file or not file.filename.endswith(('.txt', '.csv')):
        flash("请上传有效的 .csv 或 .txt 文件", 'danger')
        return redirect(url_for('scanner.scanner_home'))

    filename = f"{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    results = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            target = line.strip()
            if not target:
                continue

            raw_output = run_nuclei(target)
            summary = analyze_nuclei_output(raw_output)

            results.append({
                'target': target,
                'vuln_count': summary['count'],
                'severities': summary['severities'],
                'raw': raw_output
            })

    return render_template('scanner.html', results=results)

def run_nuclei(domain):
    nuclei_path = r"D:\Desktop\wvs\tools\nuclei\nuclei.exe"
    try:
        result = subprocess.check_output(
            [nuclei_path, "-u", domain, "-severity", "low,medium,high,critical"],
            stderr=subprocess.STDOUT,
            timeout=60
        )
        return result.decode('utf-8')
    except subprocess.TimeoutExpired:
        return "[Nuclei 扫描超时]"
    except subprocess.CalledProcessError as e:
        return f"[Nuclei 扫描失败] {e.output.decode('utf-8')}"
    except Exception as e:
        return f"[系统错误] {str(e)}"


def analyze_nuclei_output(output):
    severities = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
    count = 0

    for line in output.splitlines():
        if 'severity=' in line:
            count += 1
            for sev in severities:
                if f"severity={sev}" in line:
                    severities[sev] += 1

    return {
        'count': count,
        'severities': severities
    }
