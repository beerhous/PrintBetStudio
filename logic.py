# -*- coding: utf-8 -*-
import json
import os
import sys
import re
import math

# === 资源路径修正 (PyInstaller 兼容性核心) ===
def resource_path(relative_path):
    """获取资源的绝对路径，兼容开发环境和 PyInstaller 打包环境"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class SportteryRuleEngine:
    def __init__(self):
        # 1. 加载官方映射表
        self.rules = {}
        try:
            config_path = resource_path('mappings.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.rules = json.load(f)
            else:
                print(f"[Logic Warning] mappings.json not found at {config_path}")
        except Exception as e:
            print(f"[Logic Error] Failed to load mappings: {e}")
        
        # 2. 星期映射表 (Rule 2956 核心: 1=周一 ... 7=周日)
        self.week_map = {
            '周一': '1', '周二': '2', '周三': '3', '周四': '4', 
            '周五': '5', '周六': '6', '周日': '7'
        }

    def normalize_match_id(self, raw_text, category="football"):
        """
        场次清洗引擎: 将人类可读场次转换为机器码
        Input: "周三305" -> Output: "3305"
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
                    # 补齐3位，例如: 周三1 -> 3001, 周三305 -> 3305
                    return f"{num}{digits[0].zfill(3)}"
        
        # 兜底：如果输入已经是纯数字 (3305)
        if re.match(r'^\d{4,5}$', raw_text):
            return raw_text
            
        return raw_text

    def get_code(self, category, play_type, choice):
        """
        从 mappings.json 获取官方机器码 (Option Code)
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
                
        # 3. 容错: 如果没找到映射但看起来像合法代码(如胜分差的"01","11")
        # 则直接返回，交给后续 OMR 引擎去处理
        return choice

    def determine_capacity(self, bets, pass_type):
        """
        【智能拆单核心】决定一张票打 3 关还是 6 关
        """
        # 1. 强制 3 关的情况:
        #    - 选择了低关方式 (单关, 2x1, 3x1)
        #    - 或者总比赛数量 <= 3
        is_low_pass = any(x in pass_type for x in ['单', '1x', '2x', '3x', '2串', '3串'])
        
        if is_low_pass:
            return 3
            
        # 2. 强制 6 关的情况:
        #    - 选择了高关方式 (4x1 ... 8x1)
        #    - 且比赛数量 > 3
        is_high_pass = any(x in pass_type for x in ['4x','5x','6x','7x','8x','4串','5串','6串'])
        
        if is_high_pass:
            return 6
            
        # 默认兜底
        return 3

    def generate_title(self, category, play_type, capacity):
        """
        生成符合规范的票面标题
        Example: 竞彩篮球让分胜负游戏3关投注单
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

        suffix = f"{capacity}关投注单" if category != "number" else "投注单"
        
        # 特殊处理：数字彩没有关数
        if category == "number":
            return f"{sport_name}{play_name}{suffix}"
            
        return f"{sport_name}{play_name}游戏{suffix}"

    def generate_ticket_data(self, bets, pass_type, multiplier):
        """
        主处理流程：接收前端数据 -> 拆单 -> 生成打印数据列表
        """
        if not bets: return {"tickets": [], "count": 0}

        # 1. 识别彩种 (假设同一批次彩种一致)
        first_bet = bets[0]
        cat = "football"
        if first_bet['type'] in ["SF","RFSF","SFC","DXF"]: cat = "basketball"
        if first_bet['type'] in ["P3","P5","DLT"]: cat = "number"

        # 2. 决定单张票容量 (3场 or 6场)
        if cat == "number":
            limit = 5 # 数字彩假设一张打5注
        else:
            limit = self.determine_capacity(bets, pass_type)

        # 3. 执行拆单 (Chunking)
        # 将 bets 列表切分为 [[bet1, bet2, bet3], [bet4...]]
        ticket_chunks = [bets[i:i + limit] for i in range(0, len(bets), limit)]
        
        final_tickets = []
        
        for chunk in ticket_chunks:
            human_readable = []
            machine_codes = []
            
            # 处理单张票内的每一行
            for b in chunk:
                # 数据归一化
                m_id = self.normalize_match_id(b['match'], cat)
                o_code = self.get_code(cat, b['type'], b['choice'])
                
                if not o_code and cat != "number": continue
                
                # 构建人类可读数据 (传给 driver/engine 绘图用)
                human_readable.append({
                    "match_raw": b['match'],      # 原始: "周三305"
                    "match_code": m_id,           # 机器: "3305"
                    "type": b['type'],            # "RFSF"
                    "choice": b['choice'],        # "主胜"
                    "machine_choice": o_code      # "3"
                })
                
                # 机器码 (用于生成二维码)
                machine_codes.append(f"{m_id}-{o_code}")

            if not human_readable: continue

            # 生成该张票的标题
            title = self.generate_title(cat, chunk[0]['type'], limit)
            
            # 生成该张票的二维码字符串
            qr_str = ",".join(machine_codes) + f"|{pass_type}|{multiplier}"

            final_tickets.append({
                "title": title,
                "human_readable": human_readable,
                "machine_qr": qr_str,
                "meta": {
                    "category": cat,
                    "play_type": chunk[0]['type'],
                    "capacity": limit # 告诉 OMR 引擎用哪个模板 (3或6)
                }
            })

        return {
            "tickets": final_tickets,
            "count": len(final_tickets)
        }
