# -*- coding: utf-8 -*-
import os
import sys
import json
import datetime
import threading
import webview
from flask import Flask, render_template, request, jsonify

# === 配置: 目标打印机名称 ===
# 用户需在 Windows 控制面板确认此名称
PRINTER_NAME = "XP-58"

def resource_path(relative_path):
    """资源路径修正：兼容开发环境与打包后的 exe 环境"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

app = Flask(__name__, template_folder=resource_path('templates'))

# === 核心业务逻辑 ===
RULES = {
    "SPF": {"胜":"3", "主胜":"3", "平":"1", "1":"1", "负":"0", "0":"0"},
    "SCORE": {
        "1:0":"10", "2:0":"20", "2:1":"21", "3:0":"30", "3:1":"31", "3:2":"32",
        "4:0":"40", "4:1":"41", "4:2":"42", "5:0":"50", "5:1":"51", "5:2":"52", "胜其他":"90",
        "0:0":"00", "1:1":"11", "2:2":"22", "3:3":"33", "平其他":"99",
        "0:1":"01", "0:2":"02", "1:2":"12", "0:3":"03", "1:3":"13", "2:3":"23",
        "0:4":"04", "1:4":"14", "2:4":"24", "0:5":"05", "1:5":"15", "2:5":"25", "负其他":"09"
    }
}

def normalize_match(raw_id):
    week_map = {'周一':'1', '周二':'2', '周三':'3', '周四':'4', '周五':'5', '周六':'6', '周日':'7'}
    for k, v in week_map.items():
        if k in raw_id:
            return v + raw_id.replace(k, '').strip()
    return raw_id

def send_raw_printer(printer_name, data_bytes):
    try:
        import win32print
        p = win32print.OpenPrinter(printer_name)
        try:
            job = win32print.StartDocPrinter(p, 1, ("PrintBet Job", None, "RAW"))
            win32print.StartPagePrinter(p)
            win32print.WritePrinter(p, data_bytes)
            win32print.EndPagePrinter(p)
            win32print.EndDocPrinter(p)
            return True
        finally:
            win32print.ClosePrinter(p)
    except Exception as e:
        return False

def build_escpos(bets, pass_type, multi, qr_str):
    cmds = []
    # Init, Center, Title
    cmds.append(b'\x1B\x40\x1B\x61\x01') 
    cmds.append(b'\x1D\x21\x11' + "PrintBet Studio\n".encode('gbk') + b'\x1D\x21\x00')
    cmds.append(f"TIME: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n".encode('gbk'))
    cmds.append(b'--------------------------------\n\x1B\x61\x00')
    
    for b in bets:
        cmds.append(f"{b['match']} > {b['type']} : {b['choice']}\n".encode('gbk'))
        
    cmds.append(b'--------------------------------\n')
    cmds.append(f"PASS: {pass_type}  MULTI: {multi}\n".encode('gbk'))
    
    # QR Code Logic
    cmds.append(b'\n\x1B\x61\x01Scan to Terminal:\n'.encode('gbk'))
    q_bytes = qr_str.encode('utf-8')
    l = len(q_bytes) + 3
    pl, ph = l % 256, l // 256
    cmds.append(b'\x1D\x28\x6B\x03\x00\x31\x43\x08') # QR Size
    cmds.append(b'\x1D\x28\x6B' + bytes([pl, ph]) + b'\x31\x50\x30' + q_bytes)
    cmds.append(b'\x1D\x28\x6B\x03\x00\x31\x51\x30')
    
    cmds.append(b'\n\n\n\x1D\x56\x00') # Cut
    return b''.join(cmds)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/print', methods=['POST'])
def handle_print():
    d = request.json
    codes = []
    for b in d['bets']:
        m = normalize_match(b['match'])
        pmap = RULES.get(b['type'], RULES['SPF'])
        o = pmap.get(b['choice'], b['choice'])
        codes.append(f"{m}-{o}")
    
    qr = ",".join(codes) + f"|{d['passType']}|{d['multiplier']}"
    data = build_escpos(d['bets'], d['passType'], d['multiplier'], qr)
    
    if send_raw_printer(PRINTER_NAME, data):
        return jsonify({"status": "ok", "qr": qr})
    return jsonify({"status": "error", "msg": f"Printer '{PRINTER_NAME}' not found or offline."})

def start_server():
    app.run(host='127.0.0.1', port=18888, use_reloader=False)

if __name__ == '__main__':
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()
    webview.create_window('PrintBet Studio', 'http://127.0.0.1:18888', width=1024, height=768)
    webview.start()