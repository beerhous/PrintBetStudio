# -*- coding: utf-8 -*-
import os
import sys
import threading
import webbrowser
import requests
import webview
import base64
from io import BytesIO
from flask import Flask, render_template, request, jsonify

# === 导入核心模块 ===
from logic import SportteryRuleEngine, resource_path
from driver import EscPosDriver
from ocr_adapter import UmiOCRClient
from ocr_parser import SmartBetParser
from config_manager import ConfigManager
from omr_engine import OMREngine

# === 版本信息 ===
CURRENT_VERSION = "v5.2.0 (Final)"
GITHUB_REPO = "beerhous/PrintBetStudio"

# === Flask 初始化 ===
app = Flask(__name__, template_folder=resource_path('templates'))

try:
    # 1. 最先加载配置
    config_mgr = ConfigManager()
    print(f"[System] Config loaded from: {config_mgr._config_path}")
    
    # 2. 基于配置初始化其他模块
    logic_engine = SportteryRuleEngine()
    printer_driver = EscPosDriver()
    ocr_parser = SmartBetParser()
    omr_engine = OMREngine()
    
    # 3. 初始化 OCR (带容错)
    ocr_url = config_mgr.get('ocr_url')
    if not ocr_url: 
        ocr_url = "http://127.0.0.1:1224/api/ocr" # 终极兜底
    ocr_client = UmiOCRClient(url=ocr_url)
    
    print("[System] All modules initialized.")

except Exception as e:
    print(f"[CRITICAL ERROR] System Init Failed: {e}")
    # 即使报错也不要让程序闪退，至少让它能打开窗口显示错误
    config_mgr = ConfigManager() # 重新生成默认实例防止后续空指针

# ... (路由部分保持不变) ...

# === 修改 save_config 路由 ===
@app.route('/api/config/save', methods=['POST'])
def save_config():
    """保存配置并即时应用"""
    try:
        new_conf = request.json
        
        # 1. 保存到磁盘 (ConfigManager 会处理原子写入)
        success = config_mgr.save(new_conf)
        
        if success:
            # 2. 实时应用变更 (热重载)
            if 'ocr_url' in new_conf:
                ocr_client.update_url(new_conf['ocr_url'])
            
            return jsonify({"status": "ok"})
        else:
            return jsonify({"status": "error", "msg": "写入文件失败"})
            
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})
# ==========================================
# 辅助函数：数据清洗 (中文 -> 机器码)
# ==========================================
def preprocess_bets_for_omr(bets):
    """
    将前端的原始数据清洗为 OMR 引擎可识别的格式
    关键：填充 machine_choice 字段
    """
    processed = []
    if not bets: return []

    for b in bets:
        # 1. 自动判断彩种 (用于查表)
        cat = "football"
        if b['type'] in ["SF", "RFSF", "SFC", "DXF"]: cat = "basketball"
        elif b['type'] in ["P3", "P5", "DLT"]: cat = "number"

        # 2. 调用 Logic 层获取标准机器码
        # 例如: "主胜" -> "3", "大" -> "1", "235" -> "235"
        # 优先使用前端传来的 machine_choice (如果是OCR结果)，否则重新计算
        m_choice = b.get('machine_choice')
        if not m_choice:
            m_choice = logic_engine.get_code(cat, b['type'], b['choice'])
        
        # 如果查不到代码(比如手动输入的非法值)，尝试直接使用输入值
        if not m_choice: m_choice = b['choice']

        # 3. 构造新对象
        processed.append({
            "match": b['match'],
            "type": b['type'],
            "choice": b['choice'],
            "machine_choice": str(m_choice) # 必须转字符串 "3"
        })
    return processed

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
    """获取配置 (增强健壮性版)"""
    try:
        # 1. 获取打印机列表 (带容错)
        try:
            printers = printer_driver.get_printers()
        except:
            printers = ["XP-58 (未检测到驱动)"]

        # 2. 获取配置
        current_config = config_mgr.config

        return jsonify({
            "status": "ok",
            "config": current_config,
            "printers": printers,
            "app_version": CURRENT_VERSION
        })
    except Exception as e:
        print(f"Config Error: {e}")
        return jsonify({
            "status": "error",
            "config": {}, 
            "printers": [], 
            "msg": str(e)
        })

@app.route('/api/config/save', methods=['POST'])
def save_config():
    """保存配置并即时应用"""
    try:
        new_conf = request.json
        config_mgr.save_config(new_conf)
        
        # 实时更新 OCR 客户端地址
        ocr_client.update_url(new_conf.get('ocr_url'))
        
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

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
    """生成并发送打印指令 (OMR 仿真版)"""
    try:
        d = request.json
        prn = config_mgr.get('printer_name')
        
        # 1. 数据清洗与预处理
        clean_bets = preprocess_bets_for_omr(d.get('bets', []))
        if not clean_bets: return jsonify({"status":"error", "msg":"无有效数据"})
        
        pass_type = d.get('passType', '单关')
        multiplier = d.get('multiplier', 1)
        play_type = clean_bets[0]['type'] # 假设单张票玩法一致
        
        # 2. 调用 OMR 引擎生成图片 (PIL Image)
        print(f"[Print] Generating OMR for {len(clean_bets)} bets, type={play_type}")
        img = omr_engine.dispatch(clean_bets, pass_type, multiplier, play_type)
        
        # 3. 图片转打印指令 (Hex)
        raw_data = printer_driver.image_to_commands(img)
        
        # 4. 发送物理打印
        ok = printer_driver.send_raw(prn, raw_data)
        
        if ok:
            return jsonify({"status":"ok"})
        else:
            return jsonify({"status":"error", "msg": f"打印机 [{prn}] 无响应"})
            
    except Exception as e:
        print(f"[Print Error] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/api/preview_omr', methods=['POST'])
def api_preview():
    """前端调用此接口获取 Base64 图片进行展示"""
    try:
        d = request.json
        
        # 1. 数据清洗
        clean_bets = preprocess_bets_for_omr(d.get('bets', []))
        if not clean_bets: 
             return jsonify({"status":"ok", "img_base64": ""})

        pass_type = d.get('passType', '单关')
        multiplier = d.get('multiplier', 1)
        play_type = clean_bets[0]['type']

        # 2. 调用 OMR 绘图
        img = omr_engine.dispatch(clean_bets, pass_type, multiplier, play_type)
        
        # 3. 转 Base64
        output_buffer = BytesIO()
        img.save(output_buffer, format='PNG')
        byte_data = output_buffer.getvalue()
        base64_str = base64.b64encode(byte_data).decode('utf-8')
        
        return jsonify({"status":"ok", "img_base64": base64_str})
    except Exception as e:
        return jsonify({"status":"error", "msg":str(e)})

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
