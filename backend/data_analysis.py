# backend/analysis.py
from flask import Blueprint, render_template, request
import csv
from io import TextIOWrapper

analysis_bp = Blueprint('analysis', __name__, url_prefix='/analysis')

@analysis_bp.route('/', methods=['GET', 'POST'])
def analyze():
    stats = {}
    if request.method == 'POST':
        file = request.files.get('data_file')
        if file and file.filename.endswith('.csv'):
            stream = TextIOWrapper(file.stream, encoding='utf-8-sig')
            reader = csv.DictReader(stream)
            for row in reader:
                ip = row.get("ip") or row.get("目标")
                if not ip:
                    continue
                if ip not in stats:
                    stats[ip] = {
                        'province': row.get("省份", "未知"),
                        'high': 0,
                        'medium': 0,
                        'low': 0
                    }
                stats[ip]['high'] += int(row.get("高危个数", 0))
                stats[ip]['medium'] += int(row.get("中危个数", 0))
                stats[ip]['low'] += int(row.get("低危个数", 0))
    return render_template('data_analysis.html', stats=stats)
