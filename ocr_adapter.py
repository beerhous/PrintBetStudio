import requests
import base64

class UmiOCRClient:
    def __init__(self):
        self.url = "http://127.0.0.1:1224/api/ocr"

    def check_connection(self):
        try:
            requests.get(self.url, timeout=0.5)
            return True
        except: return False

    def scan(self, img_bytes):
        try:
            b64 = base64.b64encode(img_bytes).decode('utf-8')
            # 请求 JSON 格式以获取坐标
            pl = {"base64": b64, "options": {"data.format": "json", "ocr.language": "ch"}}
            r = requests.post(self.url, json=pl, timeout=5)
            if r.status_code != 200: return {"status":"error", "msg":f"HTTP {r.status_code}"}
            
            j = r.json()
            if j.get("code") == 100: return {"status":"ok", "data": j.get("data", [])}
            return {"status":"error", "msg": str(j.get("data"))}
        except Exception as e:
            return {"status":"error", "msg": str(e)}
