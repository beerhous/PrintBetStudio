# -*- coding: utf-8 -*-
import requests
import base64
import json
from io import BytesIO
from PIL import Image, ImageEnhance, ImageFilter

class UmiOCRClient:
    def __init__(self, url="http://127.0.0.1:1224/api/ocr"):
        self.url = url

    def update_url(self, new_url):
        self.url = new_url

    def check_connection(self):
        try:
            target = self.url.replace("/api/ocr", "")
            requests.get(target, timeout=0.5)
            return True
        except: return False

    # === 新增：图像增强流水线 ===
    def _preprocess_image(self, img_bytes):
        """
        图像增强算法：去噪 -> 锐化 -> 高对比度
        让 OCR 引擎更容易识别点阵字或模糊字
        """
        try:
            img = Image.open(BytesIO(img_bytes))
            
            # 1. 转灰度 (消除彩色噪点)
            img = img.convert('L')
            
            # 2. 增强对比度 (让字更黑，纸更白)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0) # 提高2倍对比度
            
            # 3. 增强锐度 (边缘清晰化)
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.5)
            
            # 4. 转回 Bytes
            output_buffer = BytesIO()
            img.save(output_buffer, format='JPEG', quality=90)
            return output_buffer.getvalue()
        except Exception as e:
            print(f"[OCR Preprocess Fail] {e}")
            return img_bytes # 失败则返回原图

    def scan(self, img_bytes):
        try:
            # 1. 执行预处理
            enhanced_bytes = self._preprocess_image(img_bytes)
            
            # 2. 转 Base64
            b64 = base64.b64encode(enhanced_bytes).decode('utf-8')
            
            payload = {
                "base64": b64,
                "options": {
                    "data.format": "json",
                    "ocr.cls": True # 方向矫正
                }
            }
            
            r = requests.post(self.url, json=payload, timeout=8)
            if r.status_code != 200: 
                return {"status":"error", "msg":f"HTTP {r.status_code}"}
            
            j = r.json()
            if j.get("code") in [100, 101]:
                # === 新增：计算平均置信度 ===
                raw_data = j.get("data", [])
                avg_score = 0
                if raw_data:
                    total_score = sum([item.get('score', 0) for item in raw_data])
                    avg_score = total_score / len(raw_data)
                
                return {
                    "status": "ok", 
                    "data": raw_data,
                    "confidence": avg_score # 返回置信度 0.0~1.0
                }
            
            return {"status":"error", "msg": f"引擎错误: {j.get('data')}"}
            
        except Exception as e:
            return {"status":"error", "msg": str(e)}
