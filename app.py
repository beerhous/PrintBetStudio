# -*- coding: utf-8 -*-
import threading
import webview
import webbrowser
import requests
from flask import Flask, render_template, request, jsonify
from logic import SportteryRuleEngine, resource_path
from driver import EscPosDriver
from ocr_adapter import UmiOCRClient
from ocr_parser import SmartBetParser
from config_manager import ConfigManager

CURRENT_VERSION = "v4.0.0"
GITHUB_REPO = "beerhous/PrintBetStudio" 

app = Flask(__name__, template_folder=resource_path('templates'))

# 初始化
config_mgr = ConfigManager()
engine = SportteryRuleEngine()
driver = EscPosDriver()
ocr_client = UmiOCRClient(url=config_mgr.get('ocr_url'))
ocr_parser = SmartBetParser()

@app.route('/')
def index(): return render_template('index.html')

# === Config API ===
@app.route('/api/config/get', methods=['GET'])
def get_config():
    return jsonify({"config": config_mgr.config, "printers": driver.get_printers(), "app_version": CURRENT_VERSION})

@app.route('/api/config/save', methods=['POST'])
def save_config():
    new_conf = request.json
    config_mgr.save_config(new_conf)
    ocr_client.update_url(new_conf.get('ocr_url'))
    return jsonify({"status": "ok"})

@app.route('/api/system/check_update', methods=['GET'])
def check_update():
    try:
        resp = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest", timeout=3)
        if resp.status_code == 200:
            d = resp.json()
            return jsonify({"status":"ok", "has_update": d.get('tag_name') != CURRENT_VERSION, "latest_version": d.get('tag_name'), "download_url": d.get('html_url'), "body": d.get('body')})
        return jsonify({"status":"error", "msg":"无法获取"})
    except Exception as e: return jsonify({"status":"error", "msg":str(e)})

@app.route('/api/system/open_url', methods=['POST'])
def open_url():
    webbrowser.open(request.json.get('url'))
    return jsonify({"status":"ok"})

# === Test API ===
@app.route('/api/test/printer', methods=['POST'])
def test_printer():
    ok = driver.send_raw(request.json.get('printer'), b'\x1B\x40\x1B\x61\x01\n[OK]\n\n\n\x1D\x56\x00')
    return jsonify({"status":"ok" if ok else "error"})

@app.route('/api/test/ocr', methods=['POST'])
def test_ocr():
    cli = UmiOCRClient(url=request.json.get('url'))
    return jsonify({"status":"ok" if cli.check_connection() else "error"})

# === Core API ===
@app.route('/api/ocr', methods=['POST'])
def api_ocr():
    if 'image' not in request.files: return jsonify({"status":"error"})
    if not ocr_client.check_connection(): return jsonify({"status":"error", "msg":"OCR连接失败"})
    
    res = ocr_client.scan(request.files['image'].read())
    if res['status']=='error': return jsonify(res)
    
    bets = ocr_parser.parse(res['data'])
    if not bets: return jsonify({"status":"error", "msg":"未识别到内容"})
    return jsonify({"status":"ok", "bets":bets})

@app.route('/api/print', methods=['POST'])
def api_print():
    d = request.json
    prn = config_mgr.get('printer_name')
    
    # Logic 计算
    ticket = engine.generate_ticket_data(d['bets'], d['passType'], d['multiplier'])
    if ticket['count']==0: return jsonify({"status":"error", "msg":"内容无效"})
    
    # Driver 生成
    raw = driver.build_escpos(ticket, ticket['machine_qr'], d['passType'], d['multiplier'])
    
    # 发送
    ok = driver.send_raw(prn, raw)
    return jsonify({"status":"ok" if ok else "error", "qr": ticket['machine_qr']})

def start(): app.run(port=5566, use_reloader=False)

if __name__ == '__main__':
    t = threading.Thread(target=start); t.daemon = True; t.start()
    webview.create_window('PrintBet Studio', 'http://127.0.0.1:5566', width=1200, height=850)
    webview.start()
