# -*- coding: utf-8 -*-
import cv2
import numpy as np
import logging
import threading

# 只有在真正调用时才加载 Paddle，避免启动卡死
# 这是一种 "Lazy Loading" 设计模式
PADDLE_INSTANCE = None
LOCK = threading.Lock()

class OCRService:
    def __init__(self):
        self.ready = False

    def _get_paddle(self):
        """单例模式懒加载 PaddleOCR"""
        global PADDLE_INSTANCE
        with LOCK:
            if PADDLE_INSTANCE is None:
                print("[OCR] Initializing Engine (Lazy Load)...")
                from paddleocr import PaddleOCR
                # use_angle_cls=True 矫正手机拍照角度
                # lang='ch' 支持中文
                # show_log=False 禁止控制台刷屏
                PADDLE_INSTANCE = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
                print("[OCR] Engine Ready.")
            return PADDLE_INSTANCE

    def detect_red_selections(self, image_bytes):
        """
        计算机视觉核心：寻找图片中的红色选中块
        """
        # 1. 字节流转 CV2 图像
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: raise ValueError("Invalid Image")

        # 2. 转换到 HSV 空间提取红色
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # 红色的两个 HSV 区间
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = mask1 + mask2

        # 3. 寻找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        red_boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # 过滤太小的噪点
            if w > 20 and h > 15:
                red_boxes.append((x, y, w, h))
        
        # 按 Y 轴排序（从上到下）
        red_boxes.sort(key=lambda b: b[1])
        return img, red_boxes

    def parse_image(self, image_bytes):
        """主入口"""
        try:
            ocr = self._get_paddle()
            img_cv, red_boxes = self.detect_red_selections(image_bytes)
            
            # 全图 OCR 识别文本
            # result 结构: [[[[x1,y1],...], ("text", conf)], ...]
            result = ocr.ocr(img_cv, cls=True)
            if not result or not result[0]:
                return {"error": "未识别到文字"}

            text_blocks = result[0]
            parsed_bets = []

            # === 核心算法：空间关联 (Spatial Mapping) ===
            # 我们有了红框的位置，也有了文字的位置
            # 如果文字位于红框内部，或者位于红框左侧且是"周x"，则提取
            
            for box in red_boxes:
                bx, by, bw, bh = box
                b_cy = by + bh/2 # 红框中心Y
                
                # 1. 找这个红框里的文字 (选项)
                choice = None
                for line in text_blocks:
                    coords = line[0]
                    text = line[1][0]
                    
                    tx_min = min(p[0] for p in coords)
                    ty_min = min(p[1] for p in coords)
                    tx_max = max(p[0] for p in coords)
                    ty_max = max(p[1] for p in coords)
                    
                    # 简单的包含判断：文字中心在红框内
                    t_cx = (tx_min + tx_max)/2
                    t_cy = (ty_min + ty_max)/2
                    
                    if bx < t_cx < bx+bw and by < t_cy < by+bh:
                        choice = text
                        break
                
                if not choice: continue # 空红框可能是噪点

                # 2. 找同一行的场次 (周x)
                match_id = None
                for line in text_blocks:
                    text = line[1][0]
                    coords = line[0]
                    t_cy = (coords[0][1] + coords[2][1]) / 2
                    
                    # Y轴接近，且在红框左边，且包含"周"字
                    if abs(t_cy - b_cy) < 50 and coords[0][0] < bx and "周" in text:
                        match_id = text
                        break
                
                if match_id and choice:
                    parsed_bets.append({
                        "match": match_id,
                        "type": "SPF" if len(choice)==1 else "SCORE", # 简单推断，逻辑层会二次清洗
                        "choice": choice
                    })

            return {"status": "ok", "bets": parsed_bets}

        except Exception as e:
            print(f"OCR Error: {e}")
            return {"status": "error", "msg": str(e)}
