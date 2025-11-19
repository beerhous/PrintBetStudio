import json
import os
import sys

# 资源路径辅助函数
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class BetLogic:
    def __init__(self):
        self.mappings = self.load_config()

    def load_config(self):
        # 优先读取同目录下的外部文件（方便店主修改）
        external_path = os.path.join(os.getcwd(), 'mappings.json')
        if os.path.exists(external_path):
            print(f"Loading external mappings from {external_path}")
            with open(external_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        # 否则读取打包在 EXE 内部的默认配置
        print("Loading internal default mappings")
        with open(resource_path('mappings.json'), 'r', encoding='utf-8') as f:
            return json.load(f)

    def normalize_match_id(self, raw_id):
        week_map = {'周一':'1', '周二':'2', '周三':'3', '周四':'4', '周五':'5', '周六':'6', '周日':'7'}
        for k, v in week_map.items():
            if k in raw_id:
                num = ''.join(filter(str.isdigit, raw_id.replace(k, '')))
                return v + num.zfill(3)
        return raw_id

    def get_machine_code(self, sport, play_type, choice):
        # 容错：防止字典为空
        sport_map = self.mappings.get(sport, {})
        play_map = sport_map.get(play_type, {})
        return play_map.get(choice, choice)

    def process_ticket(self, data):
        segments = []
        lines = []
        for b in data['bets']:
            mid = self.normalize_match_id(b['match'])
            oc = self.get_machine_code('football', b['type'], b['choice'])
            segments.append(f"{mid}-{oc}")
            lines.append(f"{b['match']} > {b['type']} = {b['choice']}")
        
        qr = ",".join(segments) + f"|{data['passType']}|{data['multiplier']}"
        return {"human_lines": lines, "qr_content": qr}
