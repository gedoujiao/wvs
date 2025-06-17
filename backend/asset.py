from flask import Blueprint, render_template, request, jsonify, send_file, session
import os
import subprocess
import socket
import uuid
import re
import whois
from ipwhois import IPWhois
import csv
from io import StringIO, BytesIO
import threading
import time

asset_bp = Blueprint('asset', __name__, url_prefix='/asset')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

task_results = {}
task_progress = {}

@asset_bp.route('/', methods=['GET'])
def asset_page():
    return render_template('asset.html')


@asset_bp.route('/collect', methods=['POST'])
def collect():
    data = request.get_json()
    targets = data.get('targets', [])

    if not isinstance(targets, list) or not targets:
        return jsonify({'status': 'error', 'message': '目标格式无效'}), 400

    task_id = str(uuid.uuid4())
    task_results[task_id] = []
    task_progress[task_id] = {"total": len(targets), "current": 0}

    def background_collect():
        for domain in targets:
            domain = domain.strip()
            if not domain:
                task_progress[task_id]["current"] += 1
                continue

            # 基础格式校验：域名或 IP
            if not re.match(r'^[\w.-]+\.[a-z]{2,}$', domain) and not re.match(r'^\d+\.\d+\.\d+\.\d+$', domain):
                task_progress[task_id]["current"] += 1
                continue

            asset = collect_single_asset(domain)
            task_results[task_id].append(asset)
            task_progress[task_id]["current"] += 1
            time.sleep(0.1)

    threading.Thread(target=background_collect).start()

    return jsonify({"status": "pending", "task_id": task_id})


@asset_bp.route('/progress/<task_id>', methods=['GET'])
def check_progress(task_id):
    progress = task_progress.get(task_id)
    if not progress:
        return jsonify({"status": "error", "message": "任务不存在"}), 404

    if progress['current'] >= progress['total']:
        assets = task_results[task_id]
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['域名', 'IP', '组织', '邮箱', '注册时间', 'ASN', 'IP组织', '国家', '开放端口'])

        for r in assets:
            writer.writerow([
                r['domain'],
                r['ip'],
                r['whois'].get('org', ''),
                r['whois'].get('email', ''),
                r['whois'].get('creation_date', ''),
                r['ip_info'].get('asn', ''),
                r['ip_info'].get('org', ''),
                r['ip_info'].get('country', ''),
                r['ports'].replace('\n', ' ') if isinstance(r['ports'], str) else ''
            ])

        return jsonify({
            "status": "done",
            "assets": assets,
            "csv": output.getvalue()
        })

    return jsonify({
        "status": "working",
        "current": progress['current'],
        "total": progress['total']
    })


@asset_bp.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if not file:
        return jsonify({'status': 'error', 'message': '未提供文件'}), 400

    try:
        content = file.read().decode('utf-8')
        lines = content.splitlines()
        targets = [line.strip() for line in lines if line.strip()]
        return jsonify({'status': 'success', 'targets': targets})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'文件解析失败：{e}'}), 500


@asset_bp.route('/download_csv', methods=['POST'])
def download_csv():
    content = request.json
    assets = content.get('assets')
    only_ip = content.get('only_ip', False)

    if not assets:
        return jsonify({'status': 'error', 'message': '没有结果可导出'}), 400

    output = StringIO()
    writer = csv.writer(output)

    if only_ip:
        writer.writerow(['IP'])
        for a in assets:
            writer.writerow([a.get('ip', '')])
        filename = 'ips_only.csv'
    else:
        writer.writerow(['域名', 'IP', 'WHOIS-组织', 'WHOIS-邮箱', 'WHOIS-注册时间', 'ASN', '组织', '国家', '开放端口'])
        for r in assets:
            writer.writerow([
                r.get('domain', ''),
                r.get('ip', ''),
                r.get('whois', {}).get('org', ''),
                format_email(r.get('whois', {}).get('email')),
                r.get('whois', {}).get('creation_date', ''),
                r.get('ip_info', {}).get('asn', ''),
                r.get('ip_info', {}).get('org', ''),
                r.get('ip_info', {}).get('country', ''),
                r.get('ports', '').replace('\n', ' ')
            ])
        filename = 'full_asset_results.csv'

    mem = BytesIO()
    mem.write(output.getvalue().encode('utf-8-sig'))
    mem.seek(0)
    output.close()
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=filename)


def collect_single_asset(domain):
    ip = resolve_ip(domain)
    ports = scan_ports(ip) if ip else "无法解析IP"
    whois_info = get_whois_info(domain)
    ip_info = get_ip_info(ip) if ip else {}
    return {
        'domain': domain,
        'ip': ip,
        'ports': ports,
        'whois': whois_info,
        'ip_info': ip_info
    }


def resolve_ip(domain):
    try:
        return socket.gethostbyname(domain)
    except Exception as e:
        print(f"[IP解析失败] {domain}: {e}")
        return None


def scan_ports(ip):
    try:
        result = subprocess.check_output(['nmap', '-Pn', '--top-ports', '10', ip], timeout=15)
        return result.decode('utf-8')
    except Exception as e:
        return f"端口扫描失败：{e}"


import requests

WHOIS_API_KEY = "at_K2J2BnEiE6akdx0EJ7VhZAVD469iJ"  # 

def get_whois_info(domain):
    try:
        url = "https://www.whoisxmlapi.com/whoisserver/WhoisService"
        params = {
            "apiKey": WHOIS_API_KEY,
            "domainName": domain,
            "outputFormat": "JSON"
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json().get("WhoisRecord", {})

        return {
            "org": data.get("registrant", {}).get("organization", ''),
            "email": data.get("contactEmail", ''),
            "creation_date": data.get("createdDate", '')
        }
    except Exception as e:
        print(f"[Whois API 错误] {domain} => {e}")
        return {
            "org": '',
            "email": '',
            "creation_date": ''
        }



def get_ip_info(ip):
    try:
        obj = IPWhois(ip)
        res = obj.lookup_rdap()
        return {
            "asn": res.get("asn", ''),
            "org": res.get("network", {}).get("name", ''),
            "country": res.get("network", {}).get("country", '')
        }
    except Exception as e:
        print(f"[IPWhois失败] {ip}: {e}")
        return {"asn": '', "org": '', "country": ''}


def format_email(email_field):
    if isinstance(email_field, list):
        return ', '.join(email_field)
    return email_field or ''
