import threading
import webview
from flask import Flask, render_template, request, jsonify
from logic import BetLogic, resource_path
from driver import EscPosDriver

PRINTER_NAME = "XP-58"
app = Flask(__name__, template_folder=resource_path('templates'))
logic = BetLogic()
driver = EscPosDriver()

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/ocr', methods=['POST'])
def ocr():
    # Mock OCR (对接 PaddleOCR 位置)
    return jsonify({"status":"ok", "bets":[{"match":"周三002","type":"CBF","choice":"2:1"}]})

@app.route('/api/print', methods=['POST'])
def prt():
    d = request.json
    res = logic.process_ticket(d)
    raw = driver.generate_stream(res['human_lines'], res['qr_content'], d['passType'], d['multiplier'])
    ok = driver.send_raw(PRINTER_NAME, raw)
    return jsonify({"status": "ok" if ok else "error", "machine_code": res['qr_content']})

if __name__ == '__main__':
    t = threading.Thread(target=lambda: app.run(port=28888, use_reloader=False))
    t.daemon = True
    t.start()
    webview.create_window('PrintBet Studio', 'http://127.0.0.1:28888', width=1024, height=768)
    webview.start()
