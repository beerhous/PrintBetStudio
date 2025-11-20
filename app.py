# -*- coding: utf-8 -*-
import os
import sys
import threading
import webbrowser
import requests
import webview
from flask import Flask, render_template, request, jsonify

# === 导入核心模块 ===
from logic import SportteryRuleEngine, resource_path
from driver import EscPosDriver
from ocr_adapter import UmiOCRClient
from ocr_parser import SmartBetParser
from config_manager import ConfigManager

# === 版本信息 ===
CURRENT_VERSION = "v4.0.0"
GITHUB_REPO = "beerhous/PrintBetStudio"  # 你的 GitHub 仓库地址

# === Flask 初始化 ===
# resource_path 确保在打包成 EXE 后能找到 templates 文件夹
app = Flask(__name__, template_folder=resource_path('templates'))

# === 服务模块初始化 (单例模式) ===
config_mgr = ConfigManager()
logic_engine = SportteryRuleEngine()
printer_driver = EscPosDriver()
ocr_parser = SmartBetParser()

# OCR 客户端需要动态 URL，初始时从配置读取
ocr_client = UmiOCRClient(url=config_mgr.get('ocr_url'))

# ==========================================
# 1. 页面路由
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

# ==========================================
# 2. 配置与系统 API
# ==========================================
@app.route('/api/config/get', methods=['GET'])
def get_config():
    """获取当前配置、打印机列表及版本信息"""
    return jsonify({
        "config": config_mgr.config,
        "printers": printer_driver.get_printers(), # 动态获取系统打印机
        "app_version": CURRENT_VERSION
    })


@app.route('/api/config/get', methods=['GET'])
def get_config():
    """获取配置 (增强健壮性版)"""
    try:
        # 1. 获取打印机列表 (带容错)
        try:
            printers = printer_driver.get_printers()
        except:
            printers = ["XP-58 (未检测到驱动)"]

        # 2. 获取版本
        version = CURRENT_VERSION
        
        # 3. 获取配置
        current_config = config_mgr.config

        return jsonify({
            "status": "ok",
            "config": current_config,
            "printers": printers,
            "app_version": version
        })
    except Exception as e:
        # 发生天大的错误也要返回 JSON，不能让前端卡死
        print(f"Config Error: {e}")
        return jsonify({
            "status": "error",
            "config": {}, 
            "printers": [], 
            "msg": str(e)
        })
@app.route('/api/system/check_update', methods=['GET'])
def check_update():
    """检查 GitHub Release 更新"""
    try:
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        resp = requests.get(api_url, timeout=3)
        
        if resp.status_code == 200:
            data = resp.json()
            latest_tag = data.get('tag_name', 'v0.0.0')
            download_url = data.get('html_url', '')
            
            return jsonify({
                "status": "ok",
                "has_update": latest_tag != CURRENT_VERSION,
                "latest_version": latest_tag,
                "current_version": CURRENT_VERSION,
                "download_url": download_url,
                "body": data.get('body', '暂无更新日志')
            })
        return jsonify({"status": "error", "msg": "无法连接 GitHub API"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/api/system/open_url', methods=['POST'])
def open_url():
    """调用系统默认浏览器打开链接"""
    url = request.json.get('url')
    if url:
        webbrowser.open(url)
    return jsonify({"status": "ok"})

# ==========================================
# 3. 硬件测试 API
# ==========================================
@app.route('/api/test/printer', methods=['POST'])
def test_printer():
    """测试打印机连接"""
    target_printer = request.json.get('printer')
    # 发送一段极简的测试指令
    test_data = b'\x1B\x40\x1B\x61\x01\n[PrintBet Connection OK]\n\n\n\n\x1D\x56\x00'
    success = printer_driver.send_raw(target_printer, test_data)
    return jsonify({"status": "ok" if success else "error"})

@app.route('/api/test/ocr', methods=['POST'])
def test_ocr():
    """测试 OCR 服务连接"""
    test_url = request.json.get('url')
    # 创建临时客户端测试连接
    temp_client = UmiOCRClient(url=test_url)
    if temp_client.check_connection():
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"})

# ==========================================
# 4. 核心业务 API (OCR & Print)
# ==========================================
@app.route('/api/ocr', methods=['POST'])
def api_ocr():
    """处理图片识别"""
    if 'image' not in request.files:
        return jsonify({"status": "error", "msg": "未上传图片"})
    
    # 1. 检查连接
    if not ocr_client.check_connection():
        return jsonify({
            "status": "error", 
            "msg": "无法连接 Umi-OCR，请检查是否已开启 HTTP 服务 (端口1224)"
        })
    
    try:
        file = request.files['image']
        img_bytes = file.read()
        
        # 2. 发送扫描
        scan_res = ocr_client.scan(img_bytes)
        if scan_res['status'] == 'error':
            return jsonify(scan_res)
        
        # 3. 智能解析 (聚类 + 正则)
        bets = ocr_parser.parse(scan_res['data'])
        
        if not bets:
            return jsonify({
                "status": "error", 
                "msg": "图片已识别，但未提取到有效投注内容。请确认截图清晰度。"
            })
            
        return jsonify({"status": "ok", "bets": bets})
        
    except Exception as e:
        return jsonify({"status": "error", "msg": f"识别处理异常: {str(e)}"})

@app.route('/api/print', methods=['POST'])
def api_print():
    """生成并发送打印指令"""
    try:
        d = request.json
        # 从配置中获取当前选定的打印机
        target_printer = config_mgr.get('printer_name')
        
        # 1. 逻辑层：规则计算与 OMR 布局生成
        ticket_data = logic_engine.generate_ticket_data(
            d['bets'], 
            d['passType'], 
            d['multiplier']
        )
        
        if ticket_data['count'] == 0:
            return jsonify({"status": "error", "msg": "没有有效的投注内容"})
        
        # 2. 驱动层：生成 ESC/POS 二进制流 (含反白黑块指令)
        raw_data = printer_driver.build_escpos(
            ticket_data, 
            ticket_data['machine_qr'], 
            d['passType'], 
            d['multiplier']
        )
        
        # 3. 物理层：发送至打印机
        success = printer_driver.send_raw(target_printer, raw_data)
        
        if success:
            return jsonify({"status": "ok", "qr": ticket_data['machine_qr']})
        else:
            return jsonify({"status": "error", "msg": f"打印机 [{target_printer}] 无响应"})
            
    except Exception as e:
        return jsonify({"status": "error", "msg": f"打印服务异常: {str(e)}"})

# ==========================================
# 5. 启动逻辑
# ==========================================
def start_server():
    # 禁用 reloader 防止在 GUI 模式下二次启动
    app.run(host='127.0.0.1', port=5566, use_reloader=False)

if __name__ == '__main__':
    # 启动 Flask 后台线程
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()
    
    # 启动原生 GUI 窗口
    webview.create_window(
        'PrintBet Studio (Enterprise Edition)', 
        'http://127.0.0.1:5566',
        width=1200, 
        height=850,
        resizable=True,
        min_size=(800, 600)
    )
    webview.start()
