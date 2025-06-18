from flask import Blueprint, render_template, request, jsonify, send_file, session
import os
import subprocess
import socket
import uuid
import re
from ipwhois import IPWhois
import csv
from io import StringIO, BytesIO
import threading
import time
import requests

asset_bp = Blueprint('asset', __name__, url_prefix='/asset')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

task_results = {}
task_progress = {}

WHOIS_API_KEY = "at_K2J2BnEiE6akdx0EJ7VhZAVD469iJ"

@asset_bp.route('/', methods=['GET'])
def asset_page():
    return render_template('asset.html')

@asset_bp.route('/collect', methods=['POST'])
def collect():
    data = request.get_json()
    targets = data.get('targets', [])
    subdomain_level = int(data.get('subdomain_level', 100))

    if not isinstance(targets, list) or not targets:
        return jsonify({'status': 'error', 'message': '目标格式无效'}), 400

    task_id = str(uuid.uuid4())
    task_results[task_id] = []
    task_progress[task_id] = {"total": len(targets), "current": 0}

    # 选择字典路径：优先使用上传的
    user_dict = session.get('subdomain_dict')
    default_paths = {
        100: r"D:\Desktop\wvs\tools\subdamain_list\subdomains-100.txt",
        500: r"D:\Desktop\wvs\tools\subdamain_list\subdomains-500.txt",
        1000: r"D:\Desktop\wvs\tools\subdamain_list\subdomains-1000.txt"
    }
    dict_path = user_dict if user_dict and os.path.isfile(user_dict) else default_paths.get(subdomain_level, default_paths[100])

    def background_collect():
        for domain in targets:
            domain = domain.strip()
            if not domain:
                task_progress[task_id]["current"] += 1
                continue

            if not re.match(r'^[\w.-]+\.[a-z]{2,}$', domain) and not re.match(r'^\d+\.\d+\.\d+\.\d+$', domain):
                task_progress[task_id]["current"] += 1
                continue

            asset = collect_single_asset(domain, dict_path)
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
        writer.writerow(['域名', 'IP', '组织', '邮箱', '注册时间', 'ASN', 'IP组织', '国家', '开放端口', '子域名(IP)'])

        for r in assets:
            base_row = [
                r['domain'],
                r['ip'],
                r['whois'].get('org', ''),
                r['whois'].get('email', ''),
                r['whois'].get('creation_date', ''),
                r['ip_info'].get('asn', ''),
                r['ip_info'].get('org', ''),
                r['ip_info'].get('country', ''),
                r['ports'].replace('\n', ' ') if isinstance(r['ports'], str) else ''
            ]

            subdomains = r.get('subdomains', [])
            if subdomains:
                for sub in subdomains:
                    writer.writerow(base_row + [f"{sub['subdomain']} ({sub['ip']})"])
            else:
                writer.writerow(base_row + ['无子域名'])

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
    upload_type = request.args.get('type', 'dict')  # 默认为子域名字典

    if not file:
        return jsonify({'status': 'error', 'message': '未提供文件'}), 400

    try:
        content = file.read().decode('utf-8')
        filename = f"{uuid.uuid4().hex}.txt"
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(content)

        if upload_type == 'target':
            lines = content.splitlines()
            targets = [line.strip() for line in lines if line.strip()]
            return jsonify({'status': 'success', 'targets': targets})
        else:
            session['subdomain_dict'] = save_path
            return jsonify({'status': 'success', 'message': '字典上传成功'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'上传失败：{e}'}), 500

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
        ip_set = set()
        for a in assets:
            main_ip = a.get('ip')
            if main_ip:
                writer.writerow([main_ip])

            subdomains = a.get('subdomains', [])
            for sub in subdomains:
                sub_ip = sub.get('ip')
                if sub_ip:
                    writer.writerow([sub_ip])
        filename = 'ips_only.csv'

    else:
        writer.writerow(['域名', 'IP', 'WHOIS-组织', 'WHOIS-邮箱', 'WHOIS-注册时间', 'ASN', '组织', '国家', '开放端口', '子域名(IP)'])
        for r in assets:
            base_row = [
                r.get('domain', ''),
                r.get('ip', ''),
                r.get('whois', {}).get('org', ''),
                format_email(r.get('whois', {}).get('email')),
                r.get('whois', {}).get('creation_date', ''),
                r.get('ip_info', {}).get('asn', ''),
                r.get('ip_info', {}).get('org', ''),
                r.get('ip_info', {}).get('country', ''),
                r.get('ports', '').replace('\n', ' ')
            ]
            subdomains = r.get('subdomains', [])
            if subdomains:
                for sub in subdomains:
                    writer.writerow(base_row + [f"{sub['subdomain']} ({sub['ip']})"])
            else:
                writer.writerow(base_row + ['无子域名'])

        filename = 'full_asset_results.csv'

    mem = BytesIO()
    mem.write(output.getvalue().encode('utf-8-sig'))
    mem.seek(0)
    output.close()
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=filename)

# ============ 工具函数 ============

def collect_single_asset(domain, dict_path):
    ip = resolve_ip(domain)
    ports = scan_ports(ip) if ip else "无法解析IP"
    whois_info = get_whois_info(domain)
    ip_info = get_ip_info(ip) if ip else {}
    subdomains = scan_subdomains(domain, wordlist_path=dict_path)
    return {
        'domain': domain,
        'ip': ip,
        'ports': ports,
        'whois': whois_info,
        'ip_info': ip_info,
        'subdomains': subdomains
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
        return {"org": '', "email": '', "creation_date": ''}

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

def scan_subdomains(domain, wordlist_path):
    subdomains = []
    if not os.path.isfile(wordlist_path):
        print(f"子域名字典文件不存在：{wordlist_path}")
        return subdomains

    with open(wordlist_path, 'r') as f:
        for line in f:
            sub = line.strip()
            if not sub:
                continue
            full_domain = f"{sub}.{domain}"
            try:
                ip = socket.gethostbyname(full_domain)
                subdomains.append({"subdomain": full_domain, "ip": ip})
            except socket.gaierror:
                continue
    return subdomains

def format_email(email_field):
    if isinstance(email_field, list):
        return ', '.join(email_field)
    return email_field or ''
