from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_cors import CORS
import subprocess
import socket
import csv
import re
from io import StringIO
from flask import Blueprint


asset_bp = Blueprint('asset', __name__)

CORS(asset_bp)

def is_ip(addr):
    pattern = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')
    return pattern.match(addr) is not None

def scan_ports(ip):
    ports = ['80', '443']
    scan_result = ""
    try:
        nmap_result = subprocess.check_output(['nmap', '-p', ','.join(ports), ip], timeout=60)
        scan_result = nmap_result.decode()
    except subprocess.TimeoutExpired:
        scan_result = "nmap扫描超时"
    except Exception as e:
        scan_result = f"扫描错误: {e}"
    return scan_result

@asset_bp.route('/collect', methods=['GET', 'POST'])
def collect():
    data = request.json
    target = data.get('target')

    if not target:
        return jsonify({"status": "error", "message": "请输入目标信息"}), 400

    assets = []

    try:
        if is_ip(target):
            scan_res = scan_ports(target)
            assets.append({
                'type': 'IP',
                'value': target,
                'scan': scan_res
            })
        else:
            amass_result = subprocess.check_output(
                ['amass', 'enum', '-passive', '-d', target],
                timeout=180
            )
            subdomains = amass_result.decode().splitlines()

            for sub in subdomains[:3]:
                ip = None
                try:
                    ip = socket.gethostbyname(sub)
                except Exception:
                    ip = None

                scan_res = scan_ports(ip) if ip else "无法解析IP，跳过扫描"

                assets.append({
                    'type': 'Subdomain',
                    'value': sub,
                    'ip': ip,
                    'scan': scan_res
                })

    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "扫描过程超时"}), 504
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(['资产类型', '资产', 'IP', '扫描结果摘要'])

    for asset in assets:
        scan_summary = asset['scan'].split('\n')[0]
        writer.writerow([
            asset.get('type', ''),
            asset.get('value', ''),
            asset.get('ip', ''),
            scan_summary
        ])

    csv_buffer.seek(0)

    return jsonify({
        "status": "success",
        "target": target,
        "assets": assets,
        "csv": csv_buffer.getvalue()
    })

@asset_bp.route('/asset', methods=['GET'])
def asset_page():
    return render_template('asset.html')


