# -*- coding: utf-8 -*-
import requests
import base64

class UmiOCRClient:
    def __init__(self, url="http://127.0.0.1:1224/api/ocr"):
        self.url = url

    def update_url(self, new_url):
        self.url = new_url

    def check_connection(self):
        try:
            # 尝试请求根路径
            target = self.url.replace("/api/ocr", "")
            requests.get(target, timeout=1)
            return True
        except:
            return False

    def scan(self, img_bytes):
        try:
            b64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # === 修复点：移除 'ocr.language' ===
            # 让 Umi-OCR 使用其 GUI 上设置的默认语言
            payload = {
                "base64": b64,
                "options": {
                    "data.format": "json",
                    "ocr.cls": True  # 保留方向矫正
                }
            }
            
            r = requests.post(self.url, json=payload, timeout=10)
            
            if r.status_code != 200: 
                return {"status":"error", "msg":f"HTTP {r.status_code}"}
            
            j = r.json()
            
            # Umi-OCR 成功码通常是 100 (有些版本是 101)
            if j.get("code") in [100, 101]: 
                return {"status":"ok", "data": j.get("data", [])}
            
            # 返回具体的错误信息以便调试
            return {"status":"error", "msg": f"引擎错误: {j.get('data')}"}
            
        except Exception as e:
            return {"status":"error", "msg": f"连接异常: {str(e)}"}
