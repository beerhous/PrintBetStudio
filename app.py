# -*- coding: utf-8 -*-
import threading
import webview
from flask import Flask, render_template, request, jsonify
from logic import SportteryRuleEngine, resource_path
from driver import EscPosDriver
from ocr_adapter import UmiOCRClient
from ocr_parser import SmartBetParser

# 配置
PRINTER_NAME = "XP-58"

app = Flask(__name__, template_folder=resource_path('templates'))

# 初始化各服务模块 (微服务架构思想)
logic_engine = SportteryRuleEngine()
printer_driver = EscPosDriver()
ocr_client = UmiOCRClient()
ocr_parser = SmartBetParser()

@app.route('/')
def index(): 
    return render_template('index.html')

# === OCR 接口 ===
@app.route('/api/ocr', methods=['POST'])
def api_ocr():
    if 'image' not in request.files:
        return jsonify({"status": "error", "msg": "未上传图片"})
    
    # 1. 检查 Umi 服务状态
    if not ocr_client.check_connection():
        return jsonify({"status": "error", "msg": "连接 Umi-OCR 失败！请确保已开启 HTTP 服务 (端口1224)"})
    
    # 2. 发送扫描
    scan_res = ocr_client.scan(request.files['image'].read())
    if scan_res['status'] == 'error':
        return jsonify(scan_res)
    
    # 3. 智能解析 (空间聚类)
    bets = ocr_parser.parse(scan_res['data'])
    
    if not bets:
        return jsonify({"status": "error", "msg": "图片已识别，但未找到有效彩票内容"})
        
    return jsonify({"status": "ok", "bets": bets})

# === 打印接口 ===
@app.route('/api/print', methods=['POST'])
def api_print():
    d = request.json
    
    # 1. 规则计算 (生成 OMR 结构)
    ticket = logic_engine.generate_ticket_data(d['bets'], d['passType'], d['multiplier'])
    
    if ticket['count'] == 0:
        return jsonify({"status":"error", "msg":"没有有效内容"})
        
    # 2. 生成指令 (生成 ESC/POS 二进制)
    raw_data = printer_driver.generate(
        ticket['human_readable'], 
        ticket['machine_qr'], 
        d['passType'], 
        d['multiplier']
    )
    
    # 3. 发送打印机
    ok = printer_driver.send(PRINTER_NAME, raw_data)
    
    return jsonify({"status": "ok" if ok else "error", "qr": ticket['machine_qr']})

def run_server(): 
    app.run(port=5566, use_reloader=False)

if __name__ == '__main__':
    t = threading.Thread(target=run_server)
    t.daemon = True
    t.start()
    webview.create_window('PrintBet Studio (Enterprise)', 'http://127.0.0.1:5566', width=1100, height=850)
    webview.start()
