# 在 app.py 顶部引入
from ocr_service import OCRService

# 初始化服务 (注意：此时不会加载模型，只有第一次请求才会加载)
ocr_service = OCRService()

# 修改 /api/ocr 接口
@app.route('/api/ocr', methods=['POST'])
def api_ocr():
    try:
        # 接收上传的文件
        if 'image' not in request.files:
            return jsonify({"status": "error", "msg": "无图片数据"})
            
        file = request.files['image']
        img_bytes = file.read()
        
        # 调用真实识别
        # 注意：第一次调用会卡顿 3-5 秒加载模型，这是正常的
        result = ocr_service.parse_image(img_bytes)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "msg": f"识别服务异常: {str(e)}"})
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
