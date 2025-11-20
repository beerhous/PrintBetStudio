# -*- coding: utf-8 -*-
import requests
import base64

class UmiOCRClient:
    # === 关键修复点在这里 ===
    # 必须在 __init__ 里加上 url 参数，并给一个默认值
    def __init__(self, url="http://127.0.0.1:1224/api/ocr"):
        self.url = url

    def update_url(self, new_url):
        """允许后续修改 URL"""
        self.url = new_url

    def check_connection(self):
        """检查连接状态"""
        try:
            # 尝试请求根路径或 API 路径来测试
            target = self.url.replace("/api/ocr", "")
            requests.get(target, timeout=1)
            return True
        except:
            return False

    def scan(self, img_bytes):
        """扫描图片"""
        try:
            b64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # 请求体
            payload = {
                "base64": b64,
                "options": {
                    "data.format": "json", 
                    "ocr.language": "ch"
                }
            }
            
            # 发送请求
            r = requests.post(self.url, json=payload, timeout=5)
            
            if r.status_code != 200: 
                return {"status":"error", "msg":f"HTTP {r.status_code}"}
            
            j = r.json()
            if j.get("code") == 100: 
                return {"status":"ok", "data": j.get("data", [])}
            
            return {"status":"error", "msg": str(j.get("data"))}
            
        except Exception as e:
            return {"status":"error", "msg": str(e)}
