# -*- coding: utf-8 -*-
import json
import os
import sys
import re

# === 资源路径修正 (PyInstaller 兼容性核心) ===
def resource_path(relative_path):
    """获取资源的绝对路径，兼容开发环境和 PyInstaller 打包环境"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class SportteryRuleEngine:
    def __init__(self):
        # 加载官方映射表
        try:
            with open(resource_path('mappings.json'), 'r', encoding='utf-8') as f:
                self.rules = json.load(f)
        except Exception as e:
            print(f"[Logic Error] Failed to load mappings.json: {e}")
            self.rules = {}
        
        # 星期映射表 (用于场次归一化)
        self.week_map = {
            '周一': '1', '周二': '2', '周三': '3', '周四': '4', 
            '周五': '5', '周六': '6', '周日': '7'
        }

        # === OMR 答题卡物理布局定义 ===
        # 定义打印纸上选项的排列顺序 (机器码, 显示文本)
        self.layouts = {
            # --- 竞彩足球 ---
            "SPF":   [("3","胜"), ("1","平"), ("0","负")],
            "RQSPF": [("3","让胜"), ("1","让平"), ("0","让负")],
            "JQS":   [("0","0球"), ("1","1球"), ("2","2球"), ("3","3球"), ("4","4球"), ("5","5球"), ("6","6球"), ("7","7+")],
            "BQC":   [("33","胜胜"),("31","胜平"),("30","胜负"),("13","平胜"),("11","平平"),("10","平负"),("03","负胜"),("01","负平"),("00","负负")],
            
            # --- 竞彩篮球 ---
            # 篮球胜负/让分：通常左边是负(客胜)，右边是胜(主胜)，或者根据具体省份有所不同。
            # 这里采用标准通用布局：0(负/小) 在左，3(胜)/1(大) 在右
            "SF":    [("0","主负"), ("3","主胜")],
            "RFSF":  [("0","让负"), ("3","让胜")],
            "DXF":   [("2","小分"), ("1","大分")],
            
            # 篮球胜分差 (SFC)：分为两行 (客胜行/主胜行)
            "SFC_GUEST": [("01","客1-5"), ("02","客6-10"), ("03","客11-15"), ("04","客16-20"), ("05","客21-25"), ("06","客26+")],
            "SFC_HOME":  [("11","主1-5"), ("12","主6-10"), ("13","主11-15"), ("14","主16-20"), ("15","主21-25"), ("16","主26+")],
            
            # --- 数字彩 ---
            # 排列3/5：0-9 全排列
            "NUM_0_9": [("0","0"),("1","1"),("2","2"),("3","3"),("4","4"),("5","5"),("6","6"),("7","7"),("8","8"),("9","9")]
        }

    def normalize_match_id(self, raw_text, category="football"):
        """
        场次清洗引擎
        Input: "周三305", "第23125期"
        Output: "3305", "23125"
        """
        if category == "number": 
            # 数字彩提取纯数字期号
            digits = re.findall(r'\d+', raw_text)
            return digits[0] if digits else raw_text
            
        # 竞彩提取 (周x + 数字)
        for cn, num in self.week_map.items():
            if cn in raw_text:
                digits = re.findall(r'\d+', raw_text)
                if digits: 
                    # 补齐3位，例如 周三1 -> 3001
                    return f"{num}{digits[0].zfill(3)}"
        
        # 兜底：如果输入已经是纯数字 (3005)
        if re.match(r'^\d{4}$', raw_text):
            return raw_text
            
        return raw_text

    def get_code(self, category, play_type, choice):
        """
        从 mappings.json 获取官方机器码
        """
        if category == "number":
            return choice # 数字彩选项即代码
            
        play_map = self.rules.get(category, {}).get(play_type.upper(), {})
        
        # 1. 精确匹配
        if choice in play_map: 
            return play_map[choice]
            
        # 2. 模糊匹配 (如 "主胜[1.5]" -> 匹配 "主胜")
        for key, val in play_map.items():
            if key in choice:
                return val
                
        return None

    def generate_title(self, category, play_type, pass_type):
        """
        根据过关方式生成标准票头
        规则：< 4关显示"3关投注单"，>= 4关显示"6关投注单"
        """
        sport_name = {
            "football": "竞彩足球",
            "basketball": "竞彩篮球",
            "number": "数字彩票"
        }.get(category, "彩票")

        play_name = {
            "SPF": "胜平负", "RQSPF": "让球胜平负", "CBF": "比分", "JQS": "总进球", "BQC": "半全场",
            "SF": "胜负", "RFSF": "让分胜负", "SFC": "胜分差", "DXF": "大小分",
            "P3": "排列三", "P5": "排列五", "DLT": "大乐透"
        }.get(play_type, "游戏")

        # 判断关数后缀 (仅针对竞彩)
        suffix = ""
        if category in ["football", "basketball"]:
            # 检查 pass_type 是否包含 4x, 5x, 6x, 7x, 8x
            if any(x in pass_type for x in ['4x','5x','6x','7x','8x','4串','5串','6串','7串','8串']):
                suffix = "6关投注单"
            else:
                suffix = "3关投注单" # 单关、2串、3串 统称3关单

        return f"{sport_name}{play_name}{suffix}"

    def generate_omr_view(self, play_type, user_code, user_choice):
        """
        生成 OMR 视觉结构数据 (二维数组，支持多行)
        """
        # 1. 数字彩处理
        if play_type in ["P3", "P5"]:
            layout = self.layouts["NUM_0_9"]
            row = []
            # 数字彩支持复式 (如 "1,2,3")
            selected_codes = user_code.split(',') if ',' in str(user_code) else [str(user_code)]
            
            for code, label in layout:
                is_active = code in selected_codes
                row.append({"text": f" {label} ", "active": is_active})
            return [row]

        # 2. 篮球胜分差 (特殊双行处理)
        if play_type == "SFC":
            # 客胜行
            row_guest = []
            for code, label in self.layouts["SFC_GUEST"]:
                row_guest.append({"text": f" {label} ", "active": (code == user_code)})
            # 主胜行
            row_home = []
            for code, label in self.layouts["SFC_HOME"]:
                row_home.append({"text": f" {label} ", "active": (code == user_code)})
            return [row_guest, row_home]

        # 3. 通用单行处理
        layout = self.layouts.get(play_type.upper())
        if layout:
            row = []
            for code, label in layout:
                row.append({"text": f" {label} ", "active": (code == user_code)})
            return [row]
        
        # 4. 无布局处理 (如比分，直接显示黑块)
        # 视觉修正：如果没布局，就显示 [[ 2:1 ]] 这种强提示
        return [[{"text": f"[{user_choice}]", "active": True}]]

    def generate_ticket_data(self, bets, pass_type, multiplier):
        """
        主入口：接收前端数据，返回打印机可读数据对象
        """
        valid_bets = []
        machine_codes = []
        
        # 获取第一场比赛的信息用于生成标题
        first_cat = "football"
        first_type = "SPF"
        if bets:
            if bets[0]['type'] in ["SF","RFSF","SFC","DXF"]: first_cat = "basketball"
            if bets[0]['type'] in ["P3","P5","DLT"]: first_cat = "number"
            first_type = bets[0]['type']
            
        title = self.generate_title(first_cat, first_type, pass_type)

        for b in bets:
            # 1. 判定类别
            cat = "football"
            if b['type'] in ["SF","RFSF","SFC","DXF"]: cat = "basketball"
            if b['type'] in ["P3","P5","DLT"]: cat = "number"

            # 2. 归一化数据
            m_id = self.normalize_match_id(b['match'], cat)
            o_code = self.get_code(cat, b['type'], b['choice'])
            
            if not o_code and cat != "number": 
                continue # 无法识别的选项跳过

            # 3. 生成 OMR 结构
            omr_rows = self.generate_omr_view(b['type'], o_code, b['choice'])
            
            valid_bets.append({
                "match": b['match'],
                "type": b['type'],
                "omr_rows": omr_rows
            })
            
            # 4. 机器码拼接 (用于二维码)
            machine_codes.append(f"{m_id}-{o_code}")
            
        qr_str = ",".join(machine_codes) + f"|{pass_type}|{multiplier}"
        
        return {
            "title": title,
            "human_readable": valid_bets,
            "machine_qr": qr_str,
            "count": len(valid_bets)
        }
