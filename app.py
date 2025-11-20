# -*- coding: utf-8 -*-
import threading
import webview
from flask import Flask, render_template, request, jsonify
# 确保从正确的文件导入
from logic import SportteryRuleEngine, resource_path
from driver import EscPosDriver
from ocr_adapter import UmiOCRClient
from ocr_parser import SmartBetParser

PRINTER_NAME = "XP-58"

app = Flask(__name__, template_folder=resource_path('templates'))

# === 初始化模块 (单例模式) ===
engine = SportteryRuleEngine()
driver = EscPosDriver()         # 对应 driver.py 中的 Class
ocr_client = UmiOCRClient()
ocr_parser = SmartBetParser()

@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/api/ocr', methods=['POST'])
def api_ocr():
    if 'image' not in request.files: 
        return jsonify({"status": "error", "msg": "无图片"})
    
    if not ocr_client.check_connection():
        return jsonify({"status": "error", "msg": "Umi-OCR 未连接 (请开启HTTP服务)"})
    
    res = ocr_client.scan(request.files['image'].read())
    if res['status'] == 'error': return jsonify(res)
    
    bets = ocr_parser.parse(res['data'])
    if not bets: return jsonify({"status": "error", "msg": "未识别到有效彩票内容"})
    
    return jsonify({"status": "ok", "bets": bets})

@app.route('/api/print', methods=['POST'])
def api_print():
    d = request.json
    
    # 1. 逻辑层计算
    ticket = engine.generate_ticket_data(d['bets'], d['passType'], d['multiplier'])
    if ticket['count'] == 0: 
        return jsonify({"status":"error", "msg":"内容无效"})
    
    # 2. 驱动层生成指令 (调用 Class 方法)
    raw_data = driver.build_escpos(
        ticket['human_readable'], 
        ticket['machine_qr'], 
        d['passType'], 
        d['multiplier']
    )
    
    # 3. 发送打印
    ok = driver.send_raw(PRINTER_NAME, raw_data)
    
    return jsonify({"status": "ok" if ok else "error", "qr": ticket['machine_qr']})

def start(): 
    app.run(port=6677, use_reloader=False)

if __name__ == '__main__':
    t = threading.Thread(target=start)
    t.daemon = True
    t.start()
    webview.create_window('PrintBet Studio', 'http://127.0.0.1:6677', width=1200, height=850)
    webview.start()
