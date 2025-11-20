# -*- coding: utf-8 -*-
import json
import os
import sys
import re

# === 关键：资源路径修正函数 (防止找不到 mappings.json) ===
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# === 关键：类名必须是 SportteryRuleEngine ===
class SportteryRuleEngine:
    def __init__(self):
        # 加载配置文件
        try:
            with open(resource_path('mappings.json'), 'r', encoding='utf-8') as f:
                self.rules = json.load(f)
        except Exception as e:
            print(f"Error loading mappings: {e}")
            self.rules = {} # 防崩兜底
        
        self.week_map = {'周一':'1', '周二':'2', '周三':'3', '周四':'4', '周五':'5', '周六':'6', '周日':'7'}

        # === OMR 布局定义 ===
        self.layouts = {
            "SPF":   [("3","胜"), ("1","平"), ("0","负")],
            "RQSPF": [("3","让胜"), ("1","让平"), ("0","让负")],
            "JQS":   [("0","0"),("1","1"),("2","2"),("3","3"),("4","4"),("5","5"),("6","6"),("7","7+")],
            "SF":    [("0","主负"), ("3","主胜")], 
            "RFSF":  [("0","让负"), ("3","让胜")],
            "DXF":   [("1","大分"), ("2","小分")],
            "SFC_GUEST": [("01","客1-5"),("02","客6-10"),("03","客11-15"),("04","客16-20"),("05","客21-25"),("06","客26+")],
            "SFC_HOME":  [("11","主1-5"),("12","主6-10"),("13","主11-15"),("14","主16-20"),("15","主21-25"),("16","主26+")],
            "NUM_0_9": [("0","0"),("1","1"),("2","2"),("3","3"),("4","4"),("5","5"),("6","6"),("7","7"),("8","8"),("9","9")]
        }

    def normalize_match_id(self, raw_text, category="football"):
        if category == "number": return raw_text
        for cn, num in self.week_map.items():
            if cn in raw_text:
                digits = re.findall(r'\d+', raw_text)
                if digits: return f"{num}{digits[0].zfill(3)}"
        return raw_text

    def get_code(self, category, play_type, choice):
        if category == "number": return choice
        mapping = self.rules.get(category, {}).get(play_type.upper(), {})
        # 尝试精确匹配
        if choice in mapping: return mapping[choice]
        return None

    def generate_omr_view(self, category, play_type, user_code, user_choice):
        structure = []
        
        # 1. 数字彩
        if play_type in ["P3", "P5"]:
            layout = self.layouts["NUM_0_9"]
            for code, label in layout:
                structure.append({"text": f" {label} ", "active": (code == user_code)})
            return structure

        # 2. 篮球胜分差
        if play_type == "SFC":
            if user_code and user_code.startswith("0"): layout = self.layouts["SFC_GUEST"]
            else: layout = self.layouts["SFC_HOME"]
            for code, label in layout:
                structure.append({"text": f" {label} ", "active": (code == user_code)})
            return structure

        # 3. 通用体育
        layout = self.layouts.get(play_type.upper())
        if layout:
            for code, label in layout:
                structure.append({"text": f" {label} ", "active": (code == user_code)})
        else:
            # 无布局玩法（如比分），直接显示选中项
            structure.append({"text": f" {user_choice} ", "active": True})
            
        return structure

    def generate_ticket_data(self, bets, pass_type, multiplier):
        valid_bets = []
        codes = []
        
        for b in bets:
            cat = "football"
            if b['type'] in ["SF","RFSF","SFC","DXF"]: cat = "basketball"
            if b['type'] in ["P3","P5","DLT"]: cat = "number"

            m_id = self.normalize_match_id(b['match'], cat)
            o_code = self.get_code(cat, b['type'], b['choice'])
            
            if not o_code: continue

            omr_struct = self.generate_omr_view(cat, b['type'], o_code, b['choice'])
            
            valid_bets.append({
                "match_show": b['match'],
                "type_show": b['type'],
                "choice_show": b['choice'],
                "omr_struct": omr_struct
            })
            codes.append(f"{m_id}-{o_code}")
            
        qr = ",".join(codes) + f"|{pass_type}|{multiplier}"
        return {"human_readable": valid_bets, "machine_qr": qr, "count": len(valid_bets)}
