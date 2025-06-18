from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_file
import pandas as pd
import json
import os
import uuid
from io import StringIO, BytesIO
import csv
import folium
from folium.plugins import HeatMap, MarkerCluster, MiniMap
import numpy as np
import random
from werkzeug.utils import secure_filename

visualization_bp = Blueprint('visualization', __name__, url_prefix='/visualization')

# 上传文件目录 - 使用绝对路径
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads'))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"📁 上传目录设置为: {UPLOAD_FOLDER}")


class VulnerabilityHeatmapSystem:
    """漏洞热力图系统"""

    def __init__(self):
        # 漏洞等级配置
        self.vulnerability_levels = {
            'critical': {'color': '#FF0000', 'weight': 10, 'name': '严重', 'icon': '🔴'},
            'high': {'color': '#FF4500', 'weight': 7, 'name': '高危', 'icon': '🟠'},
            'medium': {'color': '#FFA500', 'weight': 5, 'name': '中危', 'icon': '🟡'},
            'low': {'color': '#FFFF00', 'weight': 3, 'name': '低危', 'icon': '🟢'},
            'info': {'color': '#00BFFF', 'weight': 1, 'name': '信息', 'icon': '🔵'}
        }

        # 全球省份/州名坐标映射
        self.global_locations = {
            # 中国省份
            '北京': (39.9042, 116.4074), '上海': (31.2304, 121.4737), '广东': (23.1291, 113.2644),
            '浙江': (30.2741, 120.1551), '江苏': (32.0617, 118.7778), '山东': (36.6512, 117.1201),
            '河北': (38.0428, 114.5149), '湖北': (30.5928, 114.3055), '湖南': (28.2282, 112.9388),
            '河南': (34.7466, 113.6254), '福建': (26.0745, 119.2965), '安徽': (31.8612, 117.2272),
            '四川': (30.5728, 104.0668), '陕西': (34.3416, 108.9398), '重庆': (29.5647, 106.5507),
            '辽宁': (41.8057, 123.4315), '黑龙江': (45.7732, 126.6611), '吉林': (43.8868, 125.3245),
            '云南': (25.0389, 102.7183), '贵州': (26.5783, 106.7135), '新疆': (43.7928, 87.6177),
            '西藏': (29.6444, 91.1174), '青海': (36.6171, 101.7782), '甘肃': (36.0611, 103.8343),
            '宁夏': (38.4681, 106.2731), '内蒙古': (40.8174, 111.7656), '广西': (22.8150, 108.3669),
            '海南': (20.0178, 110.3487), '台湾': (23.8, 121.0), '香港': (22.3964, 114.1095),
            '澳门': (22.1987, 113.5439), '江西': (28.6740, 115.9093), '山西': (37.8706, 112.5489),
            '天津': (39.1042, 117.2000),

            # 美国州
            'California': (36.7783, -119.4179), 'Texas': (31.9686, -99.9018), 'Florida': (27.7663, -82.6404),
            'New York': (42.1657, -74.9481), 'Pennsylvania': (41.2033, -77.1945), 'Illinois': (40.3363, -89.0022),
            'Ohio': (40.3888, -82.7649), 'Georgia': (33.76, -84.39), 'North Carolina': (35.771, -78.638),
            'Michigan': (42.354558, -84.955255), 'Washington': (47.751074, -120.740139), 'Virginia': (37.768, -78.2057),

            # 欧洲国家/地区
            'London': (51.5074, -0.1278), 'Paris': (48.8566, 2.3522), 'Berlin': (52.5200, 13.4050),
            'Madrid': (40.4168, -3.7038), 'Rome': (41.9028, 12.4964), 'Amsterdam': (52.3676, 4.9041),
            'Stockholm': (59.3293, 18.0686), 'Copenhagen': (55.6761, 12.5683), 'Oslo': (59.9139, 10.7522),
            'Helsinki': (60.1699, 24.9384), 'Vienna': (48.2082, 16.3738), 'Prague': (50.0755, 14.4378),
            'Warsaw': (52.2297, 21.0122), 'Budapest': (47.4979, 19.0402), 'Zurich': (47.3769, 8.5417),
            'Brussels': (50.8503, 4.3517), 'Dublin': (53.3498, -6.2603), 'Lisbon': (38.7223, -9.1393),
            'Athens': (37.9838, 23.7275), 'Moscow': (55.7558, 37.6176), 'Kiev': (50.4501, 30.5234),

            # 亚洲国家/地区
            'Tokyo': (35.6762, 139.6503), 'Seoul': (37.5665, 126.9780), 'Mumbai': (19.0760, 72.8777),
            'Delhi': (28.7041, 77.1025), 'Bangkok': (13.7563, 100.5018), 'Singapore': (1.3521, 103.8198),
            'Kuala Lumpur': (3.1390, 101.6869), 'Jakarta': (6.2088, 106.8456), 'Manila': (14.5995, 120.9842),
            'Ho Chi Minh City': (10.8231, 106.6297), 'Hanoi': (21.0285, 105.8542), 'Yangon': (16.8661, 96.1951),
            'Dhaka': (23.8103, 90.4125), 'Karachi': (24.8607, 67.0011), 'Islamabad': (33.6844, 73.0479),
            'Tehran': (35.6892, 51.3890), 'Dubai': (25.2048, 55.2708), 'Riyadh': (24.7136, 46.6753),
            'Tel Aviv': (32.0853, 34.7818), 'Istanbul': (41.0082, 28.9784),

            # 大洋洲
            'Sydney': (-33.8688, 151.2093), 'Melbourne': (-37.8136, 144.9631), 'Perth': (-31.9505, 115.8605),
            'Brisbane': (-27.4698, 153.0251), 'Auckland': (-36.8485, 174.7633), 'Wellington': (-41.2865, 174.7762),

            # 非洲
            'Cairo': (30.0444, 31.2357), 'Lagos': (6.5244, 3.3792), 'Johannesburg': (-26.2041, 28.0473),
            'Cape Town': (-33.9249, 18.4241), 'Nairobi': (-1.2921, 36.8219), 'Casablanca': (33.5731, -7.5898),
            'Tunis': (36.8065, 10.1815), 'Algiers': (36.7538, 3.0588), 'Addis Ababa': (9.1450, 38.7451),

            # 南美洲
            'São Paulo': (-23.5505, -46.6333), 'Rio de Janeiro': (-22.9068, -43.1729),
            'Buenos Aires': (-34.6118, -58.3960),
            'Santiago': (-33.4489, -70.6693), 'Lima': (-12.0464, -77.0428), 'Bogotá': (4.7110, -74.0721),
            'Caracas': (10.4806, -66.9036), 'Quito': (-0.1807, -78.4678), 'La Paz': (-16.2902, -63.5887),

            # 加拿大省份
            'Ontario': (51.2538, -85.3232), 'Quebec': (53.9110, -68.1420), 'British Columbia': (53.7267, -127.6476),
            'Alberta': (53.9333, -116.5765), 'Manitoba': (53.7609, -98.8139), 'Saskatchewan': (52.9399, -106.4509)
        }

    def load_csv_data(self, csv_file_path):
        """加载CSV数据并处理地理坐标 - 支持逗号和空格分隔格式"""
        try:
            print(f"🔍 正在加载CSV文件: {csv_file_path}")
            print(f"📁 文件是否存在: {os.path.exists(csv_file_path)}")

            # 尝试更多的编码格式，包括常见的中文编码
            encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030', 'cp936', 'latin1', 'iso-8859-1']
            df = None
            used_encoding = None
            used_separator = None

            # 首先尝试检测文件内容和分隔符
            for encoding in encodings:
                try:
                    print(f"🧪 尝试编码: {encoding}")

                    # 读取前几行来检测分隔符
                    with open(csv_file_path, 'r', encoding=encoding) as f:
                        first_line = f.readline().strip()
                        second_line = f.readline().strip()

                    print(f"📄 第一行内容: {repr(first_line)}")
                    print(f"📄 第二行内容: {repr(second_line)}")

                    # 检测分隔符
                    separators = [',', '\t', ' ', ';', '|']
                    best_separator = None
                    max_columns = 0

                    for sep in separators:
                        if sep == ' ':
                            # 对于空格分隔，使用正则表达式处理多个空格
                            import re
                            columns = len(re.split(r'\s+', first_line.strip()))
                        else:
                            columns = len(first_line.split(sep))

                        print(f"   分隔符 '{sep}': {columns} 列")
                        if columns > max_columns and columns >= 6:  # 至少需要6列
                            max_columns = columns
                            best_separator = sep

                    if best_separator:
                        print(f"✅ 检测到最佳分隔符: '{best_separator}' ({max_columns} 列)")
                        used_separator = best_separator
                        used_encoding = encoding
                        break
                    else:
                        print(f"⚠️ 未能检测到合适的分隔符")

                except (UnicodeDecodeError, UnicodeError) as e:
                    print(f"⚠️ 使用 {encoding} 编码失败: {str(e)[:100]}...")
                    continue
                except Exception as e:
                    print(f"❌ 使用 {encoding} 编码时发生其他错误: {str(e)[:100]}...")
                    continue

            if not used_encoding or not used_separator:
                print("❌ 无法检测到合适的编码和分隔符")
                return pd.DataFrame()

            # 根据检测到的分隔符读取CSV
            try:
                if used_separator == ' ':
                    # 对于空格分隔，使用特殊处理
                    print("🔧 使用空格分隔处理...")
                    df = pd.read_csv(csv_file_path, encoding=used_encoding, sep=r'\s+', engine='python')
                else:
                    print(f"🔧 使用分隔符 '{used_separator}' 处理...")
                    df = pd.read_csv(csv_file_path, encoding=used_encoding, sep=used_separator)

                print(f"✅ 成功加载CSV文件: {len(df)} 行，使用编码: {used_encoding}，分隔符: '{used_separator}'")

            except Exception as e:
                print(f"❌ 使用检测到的参数读取失败: {e}")
                return pd.DataFrame()

            print(f"📋 CSV原始列名: {list(df.columns)}")

            # 清理列名（去除空格、BOM和特殊字符）
            original_columns = df.columns.tolist()
            df.columns = df.columns.str.strip().str.replace('\ufeff', '').str.replace('\u200b', '')
            cleaned_columns = df.columns.tolist()

            if original_columns != cleaned_columns:
                print(f"🧹 列名清理:")
                for orig, clean in zip(original_columns, cleaned_columns):
                    if orig != clean:
                        print(f"  '{orig}' -> '{clean}'")

            print(f"🧹 清理后的列名: {list(df.columns)}")

            # 固定表头格式检查和重命名
            expected_columns = ['ip', '省份', '漏洞个数', '高危个数', '中危个数', '低危个数']

            # 检查是否有所需的列
            if '省份' in df.columns:
                df = df.rename(columns={'省份': '省份/州名'})
                print(f"✅ 将 '省份' 列重命名为 '省份/州名'")

            # 验证必需列是否存在
            required_columns = ['ip', '省份/州名', '漏洞个数', '高危个数', '中危个数', '低危个数']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                print(f"❌ 缺少必需的列: {missing_columns}")
                print(f"📋 当前列名: {list(df.columns)}")
                print(f"📋 期望的列名格式: {expected_columns}")

                # 显示列名对比
                print(f"🔍 列名详细对比:")
                for i, col in enumerate(df.columns):
                    expected = expected_columns[i] if i < len(expected_columns) else "无对应"
                    print(f"  第{i + 1}列: '{col}' (期望: '{expected}')")

                # 返回空DataFrame，但包含所需的列结构
                return pd.DataFrame(columns=required_columns + ['latitude', 'longitude'])

            print(f"✅ 列名验证通过，包含所有必需列")

            # 数据类型转换和清理
            numeric_columns = ['漏洞个数', '高危个数', '中危个数', '低危个数']
            for col in numeric_columns:
                if col in df.columns:
                    # 先尝试转换，如果失败则显示详细错误信息
                    try:
                        original_data = df[col].copy()
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

                        # 检查是否有转换失败的数据
                        failed_conversions = original_data[pd.to_numeric(original_data, errors='coerce').isna()]
                        if not failed_conversions.empty:
                            print(f"⚠️ 列 '{col}' 中有无法转换为数字的数据: {failed_conversions.tolist()}")

                    except Exception as e:
                        print(f"❌ 转换列 '{col}' 时出错: {e}")
                        df[col] = 0

            # 显示数据样本
            print(f"📋 数据前3行预览:")
            for i, (_, row) in enumerate(df.head(3).iterrows()):
                print(f"  行{i + 1}: IP={row['ip']}, 地区={row['省份/州名']}, 漏洞={row['漏洞个数']}, 高危={row['高危个数']}")

            # 添加地理坐标
            coords = []
            for _, row in df.iterrows():
                location = str(row['省份/州名']).strip()
                if location in self.global_locations:
                    lat, lon = self.global_locations[location]
                    coords.append({'latitude': lat, 'longitude': lon})
                    print(f"✅ 找到坐标: {location} -> ({lat:.4f}, {lon:.4f})")
                else:
                    # 如果找不到坐标，使用随机坐标（在合理范围内）
                    lat = random.uniform(20, 50)  # 主要在中国范围内
                    lon = random.uniform(80, 130)
                    coords.append({'latitude': lat, 'longitude': lon})
                    print(f"⚠️ 未找到 '{location}' 的坐标，使用随机坐标: ({lat:.4f}, {lon:.4f})")

            coords_df = pd.DataFrame(coords)
            df = pd.concat([df, coords_df], axis=1)

            print(f"🎯 最终数据处理完成:")
            print(f"   📊 记录数: {len(df)}")
            print(f"   📋 列名: {list(df.columns)}")
            print(
                f"   📈 数据统计: 总漏洞 {df['漏洞个数'].sum()}，高危 {df['高危个数'].sum()}，中危 {df['中危个数'].sum()}，低危 {df['低危个数'].sum()}")
            return df

        except Exception as e:
            print(f"❌ 加载CSV文件失败: {e}")
            import traceback
            print(f"📋 详细错误信息:")
            print(traceback.format_exc())
            return pd.DataFrame(columns=['ip', '省份/州名', '漏洞个数', '高危个数', '中危个数', '低危个数', 'latitude', 'longitude'])

    def create_global_heatmap(self, csv_file_path=None):
        """创建全球漏洞热力图"""
        print(f"🗺️ 开始创建热力图...")
        print(f"📁 输入文件路径: {csv_file_path}")

        # 强制检查文件路径和存在性
        use_uploaded_file = False
        if csv_file_path:
            print(f"🔍 检查文件: {csv_file_path}")
            print(f"📂 文件存在性: {os.path.exists(csv_file_path)}")
            if os.path.exists(csv_file_path):
                use_uploaded_file = True
                print(f"✅ 使用上传的CSV文件: {csv_file_path}")
            else:
                print(f"❌ 文件不存在: {csv_file_path}")

        if use_uploaded_file:
            df = self.load_csv_data(csv_file_path)
            data_source = f"上传文件: {os.path.basename(csv_file_path)}"
        else:
            print("📝 使用示例数据")
            df = self.create_sample_data()
            data_source = "示例数据"

        if df.empty:
            print("⚠️ 数据为空，创建默认地图")
            # 创建默认全球地图
            m = folium.Map(location=[20.0, 0.0], zoom_start=2)
            self.add_global_map_layers(m)
            return m

        print(f"📊 处理数据: {len(df)} 条记录，数据源: {data_source}")
        print(f"📋 数据列: {list(df.columns)}")

        # 计算全球地图中心点
        center_lat = df['latitude'].mean()
        center_lon = df['longitude'].mean()
        print(f"🎯 地图中心: ({center_lat:.4f}, {center_lon:.4f})")

        # 创建全球地图
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=2,
            prefer_canvas=True
        )

        # 添加多种全球地图图层
        self.add_global_map_layers(m)

        # 添加小地图
        try:
            minimap = MiniMap(position='bottomright', width=150, height=100, toggle_display=True)
            m.add_child(minimap)
            print("✅ 小地图创建成功")
        except Exception as e:
            print(f"⚠️ 小地图创建失败: {e}")

        # 准备热图数据
        heat_data = []

        # 按漏洞数量分组处理
        for idx, row in df.iterrows():
            lat, lon = row['latitude'], row['longitude']
            total_vulns = row['漏洞个数']
            high_vulns = row['高危个数']
            medium_vulns = row['中危个数']
            low_vulns = row['低危个数']

            # 计算权重（确保权重足够大以显示热力图）
            weight = max(1.0, high_vulns * 5 + medium_vulns * 3 + low_vulns * 1)
            # 如果权重太小，使用总漏洞数作为最小权重
            if weight < total_vulns:
                weight = total_vulns

            heat_data.append([lat, lon, weight])

            print(f"🔍 处理数据点: {row['省份/州名']} - 坐标({lat:.4f}, {lon:.4f}) - 漏洞({total_vulns}) - 权重({weight})")

            # 确定严重程度等级
            if high_vulns >= 5:
                severity = 'critical'
                icon_color = 'red'
            elif high_vulns >= 3:
                severity = 'high'
                icon_color = 'orange'
            elif medium_vulns >= 5:
                severity = 'medium'
                icon_color = 'orange'
            else:
                severity = 'low'
                icon_color = 'green'

            # 创建弹窗信息
            popup_html = f"""
            <div style="font-family: 'Microsoft YaHei', Arial, sans-serif; width: 300px;">
                <div style="background: {self.vulnerability_levels[severity]['color']}; color: white; padding: 12px; margin: -10px -10px 12px -10px; border-radius: 8px 8px 0 0;">
                    <h3 style="margin: 0;">{self.vulnerability_levels[severity]['icon']} 漏洞统计</h3>
                </div>
                <div style="padding: 8px;">
                    <p><strong>🌐 IP地址:</strong> <code>{row['ip']}</code></p>
                    <p><strong>📍 位置:</strong> {row['省份/州名']}</p>
                    <p><strong>📊 漏洞总数:</strong> <span style="font-size: 18px; font-weight: bold; color: {self.vulnerability_levels[severity]['color']};">{total_vulns}</span></p>
                    <hr style="margin: 10px 0;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                        <div style="text-align: center; padding: 8px; background: rgba(255,0,0,0.1); border-radius: 5px;">
                            <div style="font-weight: bold; color: #FF0000;">🔴 高危</div>
                            <div style="font-size: 16px; font-weight: bold;">{high_vulns}</div>
                        </div>
                        <div style="text-align: center; padding: 8px; background: rgba(255,165,0,0.1); border-radius: 5px;">
                            <div style="font-weight: bold; color: #FFA500;">🟡 中危</div>
                            <div style="font-size: 16px; font-weight: bold;">{medium_vulns}</div>
                        </div>
                        <div style="text-align: center; padding: 8px; background: rgba(255,255,0,0.1); border-radius: 5px; grid-column: span 2;">
                            <div style="font-weight: bold; color: #FFFF00;">🟢 低危</div>
                            <div style="font-size: 16px; font-weight: bold;">{low_vulns}</div>
                        </div>
                    </div>
                    <p style="margin-top: 10px; font-size: 12px; color: #666;">
                        坐标: ({lat:.4f}, {lon:.4f})
                    </p>
                </div>
            </div>
            """

            # 创建标记
            marker = folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"{row['省份/州名']} | 总漏洞: {total_vulns} | 高危: {high_vulns}",
                icon=folium.Icon(
                    color=icon_color,
                    icon='exclamation-triangle',
                    prefix='fa'
                )
            )
            marker.add_to(m)

        # 添加全球热力图层
        if heat_data:
            try:
                print(f"🔥 创建热力图，数据点数: {len(heat_data)}")
                print(f"📍 热力图数据示例: {heat_data[:3]}")  # 显示前3个数据点

                # 检查数据权重是否合理
                weights = [point[2] for point in heat_data]
                print(f"⚖️ 权重范围: {min(weights)} - {max(weights)}")

                heat_map = HeatMap(
                    heat_data,
                    name='全球漏洞热力图',
                    radius=50,  # 增加半径
                    blur=35,  # 增加模糊度
                    max_zoom=18,  # 修改最大缩放
                    min_opacity=0.4,  # 添加最小透明度
                    gradient={
                        0.0: '#0000FF',  # 蓝色
                        0.2: '#00FFFF',  # 青色
                        0.4: '#00FF00',  # 绿色
                        0.6: '#FFFF00',  # 黄色
                        0.8: '#FF8000',  # 橙色
                        1.0: '#FF0000'  # 红色
                    }
                )
                m.add_child(heat_map)
                print("✅ 全球热力图创建成功")

            except Exception as e:
                print(f"⚠️ 热力图创建失败: {e}")
                import traceback
                print(f"📋 详细错误: {traceback.format_exc()}")
        else:
            print("⚠️ 热力图数据为空")

        # 添加图层控制
        try:
            folium.LayerControl(position='topright').add_to(m)
        except:
            pass

        # 添加全球图例
        self.add_global_legend(m, df, data_source)

        return m

    def add_global_map_layers(self, m):
        """添加全球地图图层"""
        # 添加Esri世界地形图
        try:
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
                attr='&copy; <a href="https://www.esri.com/">Esri</a>',
                name='Esri世界地形图 ⭐',
                overlay=False,
                control=True
            ).add_to(m)
            print(f"✅ 成功加载: Esri世界地形图")
        except Exception as e:
            print(f"⚠️ Esri世界地形图加载失败: {e}")

        # 添加Esri世界影像图
        try:
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='&copy; <a href="https://www.esri.com/">Esri</a>',
                name='Esri世界影像图',
                overlay=False,
                control=True
            ).add_to(m)
            print(f"✅ 成功加载: Esri世界影像图")
        except Exception as e:
            print(f"⚠️ Esri世界影像图加载失败: {e}")

        # 添加OpenStreetMap
        try:
            folium.TileLayer(
                tiles='OpenStreetMap',
                name='OpenStreetMap',
                overlay=False,
                control=True
            ).add_to(m)
            print(f"✅ 成功加载: OpenStreetMap")
        except Exception as e:
            print(f"⚠️ OpenStreetMap加载失败: {e}")

        # 添加CartoDB深色地图
        try:
            folium.TileLayer(
                tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                attr='&copy; <a href="https://carto.com/attributions">CARTO</a>',
                name='CartoDB深色地图',
                overlay=False,
                control=True,
                subdomains=['a', 'b', 'c', 'd']
            ).add_to(m)
            print(f"✅ 成功加载: CartoDB深色地图")
        except Exception as e:
            print(f"⚠️ CartoDB深色地图加载失败: {e}")

        # 添加CartoDB浅色地图
        try:
            folium.TileLayer(
                tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
                attr='&copy; <a href="https://carto.com/attributions">CARTO</a>',
                name='CartoDB浅色地图',
                overlay=False,
                control=True,
                subdomains=['a', 'b', 'c', 'd']
            ).add_to(m)
            print(f"✅ 成功加载: CartoDB浅色地图")
        except Exception as e:
            print(f"⚠️ CartoDB浅色地图加载失败: {e}")

    def add_global_legend(self, m, df, data_source):
        """添加全球图例"""
        total_locations = len(df)
        total_vulns = df['漏洞个数'].sum()
        total_high = df['高危个数'].sum()
        total_medium = df['中危个数'].sum()
        total_low = df['低危个数'].sum()

        legend_html = f'''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 250px; 
                    background: rgba(255,255,255,0.95); 
                    backdrop-filter: blur(10px);
                    border: 2px solid #007ACC;
                    border-radius: 15px;
                    box-shadow: 0 8px 32px rgba(0,123,204,0.2);
                    z-index: 9999; 
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    font-size: 13px; 
                    padding: 15px">

            <h4 style="margin: 0 0 12px 0; color: #007ACC; font-size: 16px; text-align: center; border-bottom: 1px solid #eee; padding-bottom: 8px;">
                🌍 全球漏洞统计
            </h4>

            <div style="display: grid; gap: 8px;">
                <div style="display: flex; justify-content: space-between; padding: 6px; background: rgba(0,123,204,0.1); border-radius: 5px;">
                    <span><strong>📍 监控地区:</strong></span>
                    <span style="font-weight: bold;">{total_locations}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 6px; background: rgba(0,123,204,0.1); border-radius: 5px;">
                    <span><strong>📊 漏洞总数:</strong></span>
                    <span style="font-weight: bold; color: #007ACC;">{total_vulns}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 6px; background: rgba(255,0,0,0.1); border-radius: 5px;">
                    <span><strong>🔴 高危:</strong></span>
                    <span style="font-weight: bold; color: #FF0000;">{total_high}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 6px; background: rgba(255,165,0,0.1); border-radius: 5px;">
                    <span><strong>🟡 中危:</strong></span>
                    <span style="font-weight: bold; color: #FFA500;">{total_medium}</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 6px; background: rgba(255,255,0,0.1); border-radius: 5px;">
                    <span><strong>🟢 低危:</strong></span>
                    <span style="font-weight: bold; color: #FFAA00;">{total_low}</span>
                </div>
            </div>

            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; text-align: center; color: #666; font-size: 11px;">
                🔄 数据源: {data_source}
            </div>
        </div>
        '''

        try:
            m.get_root().html.add_child(folium.Element(legend_html))
        except:
            pass

    def create_sample_data(self):
        """创建示例数据 - 固定表头格式"""
        sample_data = [
            ['192.168.1.100', '北京', 15, 3, 7, 5],
            ['10.0.0.50', '上海', 12, 2, 5, 5],
            ['172.16.0.10', '广东', 20, 5, 8, 7],
            ['203.0.113.10', 'California', 18, 4, 9, 5],
            ['198.51.100.5', 'New York', 14, 3, 6, 5],
            ['10.10.10.100', 'Texas', 16, 2, 8, 6],
            ['192.168.50.100', 'London', 22, 6, 10, 6],
            ['172.20.0.100', 'Paris', 13, 2, 7, 4],
            ['10.30.40.50', 'Berlin', 17, 4, 8, 5],
            ['192.168.100.200', 'Tokyo', 19, 5, 9, 5],
            ['203.0.113.50', 'Seoul', 11, 1, 5, 5],
            ['10.40.50.60', 'Singapore', 21, 6, 9, 6],
            ['172.30.0.100', 'Sydney', 14, 3, 6, 5],
            ['192.168.200.100', 'São Paulo', 16, 4, 7, 5],
            ['10.50.60.70', 'Mumbai', 18, 5, 8, 5],
            ['203.0.113.100', '浙江', 13, 2, 6, 5],
            ['198.51.100.200', '四川', 15, 3, 7, 5],
            ['10.60.70.80', 'Ontario', 12, 2, 5, 5],
            ['172.40.0.100', 'Moscow', 20, 6, 8, 6],
            ['192.168.300.100', 'Dubai', 14, 3, 6, 5]
        ]

        # 使用固定的列名格式
        df = pd.DataFrame(sample_data, columns=['ip', '省份', '漏洞个数', '高危个数', '中危个数', '低危个数'])

        # 重命名省份列以保持一致性
        df = df.rename(columns={'省份': '省份/州名'})

        # 添加地理坐标
        coords = []
        for _, row in df.iterrows():
            location = row['省份/州名']
            if location in self.global_locations:
                lat, lon = self.global_locations[location]
                coords.append({'latitude': lat, 'longitude': lon})
            else:
                # 如果找不到坐标，使用随机坐标
                lat = random.uniform(-60, 70)
                lon = random.uniform(-180, 180)
                coords.append({'latitude': lat, 'longitude': lon})

        coords_df = pd.DataFrame(coords)
        df = pd.concat([df, coords_df], axis=1)
        return df

    def load_csv_data_from_dataframe(self, df):
        """从DataFrame加载数据并处理地理坐标"""
        # 检查列名并统一格式
        if '省份' in df.columns:
            df = df.rename(columns={'省份': '省份/州名'})
            print("✅ 将 '省份' 列重命名为 '省份/州名'")

        # 添加地理坐标
        coords = []
        for _, row in df.iterrows():
            location = row['省份/州名']
            if location in self.global_locations:
                lat, lon = self.global_locations[location]
                coords.append({'latitude': lat, 'longitude': lon})
            else:
                # 如果找不到坐标，使用随机坐标
                lat = random.uniform(-60, 70)
                lon = random.uniform(-180, 180)
                coords.append({'latitude': lat, 'longitude': lon})

        coords_df = pd.DataFrame(coords)
        df = pd.concat([df, coords_df], axis=1)
        return df


# 创建系统实例
heatmap_system = VulnerabilityHeatmapSystem()


@visualization_bp.route('/')
def index():
    """热力图主页"""
    # 获取文件参数
    filename = request.args.get('file')
    print(f"🌐 热力图主页访问，文件参数: {filename}")
    return render_template('heatmap.html', uploaded_file=filename)


@visualization_bp.route('/upload', methods=['GET', 'POST'])
def upload_csv():
    """CSV文件上传页面"""
    if request.method == 'POST':
        print("📤 收到文件上传请求")

        if 'file' not in request.files:
            flash('没有选择文件', 'error')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('没有选择文件', 'error')
            return redirect(request.url)

        if file and file.filename.endswith('.csv'):
            filename = secure_filename(file.filename)
            filepath = os.path.abspath(os.path.join(UPLOAD_FOLDER, filename))
            file.save(filepath)

            print(f"✅ 文件上传成功:")
            print(f"  📄 文件名: {filename}")
            print(f"  📁 保存路径: {filepath}")
            print(f"  📂 文件大小: {os.path.getsize(filepath)} bytes")
            print(f"  ✅ 文件存在验证: {os.path.exists(filepath)}")

            flash(f'文件 {filename} 上传成功！', 'success')
            # 重定向到热力图页面并传递文件参数
            return redirect(url_for('visualization.index', file=filename))
        else:
            flash('请上传CSV文件', 'error')

    return render_template('upload_csv.html')


@visualization_bp.route('/api/heatmap')
def api_heatmap():
    """热力图API"""
    filename = request.args.get('file')
    print(f"🔌 热力图API调用，文件参数: {filename}")

    if filename:
        csv_file_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, filename))
        print(f"📁 构建文件路径: {csv_file_path}")
        print(f"✅ 文件存在检查: {os.path.exists(csv_file_path)}")
    else:
        csv_file_path = None
        print("📝 未指定文件，将使用示例数据")

    heatmap = heatmap_system.create_global_heatmap(csv_file_path)
    return heatmap._repr_html_()


@visualization_bp.route('/api/test_heatmap')
def test_heatmap():
    """测试热力图功能"""
    try:
        print("🧪 开始测试热力图功能")
        # 创建简单的测试地图
        m = folium.Map(location=[39.9, 116.4], zoom_start=4)

        # 测试数据
        test_data = [
            [39.9042, 116.4074, 10],  # 北京
            [31.2304, 121.4737, 15],  # 上海
            [23.1291, 113.2644, 20],  # 广东
            [30.2741, 120.1551, 8],  # 浙江
            [30.5728, 104.0668, 12],  # 四川
        ]

        print(f"🧪 测试热力图数据: {test_data}")

        # 添加热力图
        heat_map = HeatMap(
            test_data,
            radius=50,
            blur=35,
            min_opacity=0.4,
            gradient={0.4: 'blue', 0.6: 'cyan', 0.7: 'lime', 0.8: 'yellow', 1.0: 'red'}
        )
        m.add_child(heat_map)

        # 添加标记点以便比较
        for point in test_data:
            folium.CircleMarker(
                location=[point[0], point[1]],
                radius=point[2],
                color='red',
                fill=True,
                popup=f"权重: {point[2]}"
            ).add_to(m)

        return m._repr_html_()

    except Exception as e:
        print(f"❌ 测试热力图失败: {e}")
        import traceback
        return f"<h1>测试失败</h1><pre>{traceback.format_exc()}</pre>"


@visualization_bp.route('/api/debug_csv')
def debug_csv():
    """调试CSV处理"""
    filename = request.args.get('file')
    if not filename:
        return "<h1>请提供文件参数</h1><p>例如: /api/debug_csv?file=your_file.csv</p>"

    csv_file_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, filename))
    print(f"🔍 调试CSV文件: {csv_file_path}")

    if not os.path.exists(csv_file_path):
        # 显示调试信息
        files_in_upload = []
        if os.path.exists(UPLOAD_FOLDER):
            files_in_upload = os.listdir(UPLOAD_FOLDER)

        return f"""
        <h1>文件不存在</h1>
        <p><strong>请求的文件:</strong> {filename}</p>
        <p><strong>完整路径:</strong> {csv_file_path}</p>
        <p><strong>uploads目录:</strong> {UPLOAD_FOLDER}</p>
        <p><strong>uploads目录存在:</strong> {os.path.exists(UPLOAD_FOLDER)}</p>
        <p><strong>uploads目录中的文件:</strong> {files_in_upload}</p>

        <h2>解决方案:</h2>
        <ol>
            <li>确认文件已正确上传到uploads目录</li>
            <li>检查文件名是否正确（包括扩展名.csv）</li>
            <li>如果是中文文件名，检查是否有编码问题</li>
        </ol>
        """

    try:
        # 读取并处理CSV
        df = heatmap_system.load_csv_data(csv_file_path)

        html = f"""
        <h1>CSV调试信息</h1>
        <h2>文件路径: {csv_file_path}</h2>
        <h2>数据行数: {len(df)}</h2>
        <h2>列名: {list(df.columns)}</h2>
        <h2>前5行数据:</h2>
        <table border="1" style="border-collapse: collapse;">
        <tr>
        """

        # 表头
        for col in df.columns:
            html += f"<th>{col}</th>"
        html += "</tr>"

        # 数据行（显示前5行）
        for _, row in df.head().iterrows():
            html += "<tr>"
            for col in df.columns:
                html += f"<td>{row[col]}</td>"
            html += "</tr>"

        html += "</table>"

        # 检查地理坐标
        html += "<h2>地理坐标检查:</h2><ul>"
        for _, row in df.iterrows():
            location = row['省份/州名']
            lat, lon = row['latitude'], row['longitude']
            html += f"<li>{location}: ({lat:.4f}, {lon:.4f})</li>"
        html += "</ul>"

        return html

    except Exception as e:
        import traceback
        return f"<h1>处理失败</h1><pre>{traceback.format_exc()}</pre>"


@visualization_bp.route('/api/upload_info')
def api_upload_info():
    """获取上传文件信息API"""
    filename = request.args.get('file')
    if not filename:
        return jsonify({'error': '未指定文件名'})

    # 使用绝对路径
    csv_file_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, filename))

    # 输出调试信息
    print(f"🔍 调试信息:")
    print(f"  📁 UPLOAD_FOLDER: {UPLOAD_FOLDER}")
    print(f"  📄 filename: {filename}")
    print(f"  🎯 csv_file_path: {csv_file_path}")
    print(f"  ✅ 文件存在: {os.path.exists(csv_file_path)}")

    # 列出uploads目录中的所有文件
    if os.path.exists(UPLOAD_FOLDER):
        files_in_upload = os.listdir(UPLOAD_FOLDER)
        print(f"  📂 uploads目录中的文件: {files_in_upload}")
    else:
        print(f"  ❌ uploads目录不存在: {UPLOAD_FOLDER}")

    if not os.path.exists(csv_file_path):
        return jsonify({
            'error': '文件不存在',
            'file_path': csv_file_path,
            'upload_folder': UPLOAD_FOLDER,
            'files_in_upload': files_in_upload if os.path.exists(UPLOAD_FOLDER) else [],
            'expected_format': 'CSV文件应包含以下列：ip,省份,漏洞个数,高危个数,中危个数,低危个数'
        })

    try:
        # 简单读取文件信息
        file_size = os.path.getsize(csv_file_path)

        # 尝试读取前几行，多种编码
        first_line = None
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']

        for encoding in encodings:
            try:
                with open(csv_file_path, 'r', encoding=encoding) as f:
                    first_line = f.readline().strip()
                    print(f"  ✅ 使用 {encoding} 编码成功读取首行")
                    break
            except UnicodeDecodeError:
                print(f"  ⚠️ 使用 {encoding} 编码失败")
                continue

        if first_line is None:
            first_line = "无法读取文件内容（编码问题）"

        return jsonify({
            'success': True,
            'filename': filename,
            'file_path': csv_file_path,
            'upload_folder': UPLOAD_FOLDER,
            'file_size': file_size,
            'first_line': first_line,
            'expected_format': '表头应为：ip,省份,漏洞个数,高危个数,中危个数,低危个数'
        })

    except Exception as e:
        return jsonify({
            'error': f'读取文件信息失败: {str(e)}',
            'file_path': csv_file_path,
            'upload_folder': UPLOAD_FOLDER
        })
    """统计信息API"""
    filename = request.args.get('file')
    print(f"📈 统计API调用，文件参数: {filename}")

    if filename:
        csv_file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(csv_file_path):
            df = heatmap_system.load_csv_data(csv_file_path)
            print(f"✅ 使用上传文件统计数据")
        else:
            df = heatmap_system.create_sample_data()
            print(f"⚠️ 文件不存在，使用示例数据")
    else:
        df = heatmap_system.create_sample_data()
        print(f"📝 使用示例数据")

    if df.empty:
        return jsonify({
            'total_locations': 0,
            'total_vulns': 0,
            'total_high': 0,
            'total_medium': 0,
            'total_low': 0,
            'top_locations': [],
            'regional_stats': []
        })

    # 基础统计
    stats = {
        'total_locations': len(df),
        'total_vulns': int(df['漏洞个数'].sum()),
        'total_high': int(df['高危个数'].sum()),
        'total_medium': int(df['中危个数'].sum()),
        'total_low': int(df['低危个数'].sum())
    }

    # 按漏洞数量排序的前10个地区
    top_locations = df.nlargest(10, '漏洞个数')[['省份/州名', '漏洞个数', '高危个数']].to_dict('records')
    stats['top_locations'] = top_locations

    # 地区统计
    china_locations = ['北京', '上海', '广东', '浙江', '江苏', '山东', '河北', '湖北', '湖南', '河南', '福建', '安徽', '四川', '陕西', '重庆']
    df['region'] = df['省份/州名'].apply(lambda x: '中国' if x in china_locations else '海外')
    regional_stats = df.groupby('region').agg({
        '漏洞个数': 'sum',
        '高危个数': 'sum',
        '中危个数': 'sum',
        '低危个数': 'sum'
    }).reset_index().to_dict('records')
    stats['regional_stats'] = regional_stats

    return jsonify(stats)