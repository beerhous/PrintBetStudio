# -*- coding: utf-8 -*-
import re

class BatchParser:
    def __init__(self, logic_instance):
        self.logic = logic_instance

    def parse_text_content(self, raw_text, delimiter="-"):
        """
        解析批量文本 (中文提示版)
        """
        valid_tickets = []
        errors = []
        
        lines = raw_text.strip().split('\n')
        
        for line_idx, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith("#"): continue

            try:
                # 智能探测分隔符
                if delimiter not in line:
                    if ":" in line: delimiter = ":"
                    elif " " in line: delimiter = " "
                
                parts = line.split(delimiter)
                if len(parts) < 2:
                    raise ValueError("格式错误，缺少选项部分")

                match_raw = parts[0].strip()
                choices_raw = parts[1].strip()

                # 场次清洗
                match_id = self.logic.normalize_match_id(match_raw)
                
                # 选项解析
                sub_choices = re.split(r'[,/，]', choices_raw)
                
                bets = []
                for c in sub_choices:
                    c = c.strip()
                    if not c: continue
                    
                    # 简单的玩法推断
                    play_type = "SPF" 
                    if ":" in c: play_type = "CBF"
                    elif len(c) >= 2 and c in ["33","31","30","13","11","10","03","01","00"]: play_type = "BQC"

                    m_code = self.logic.get_machine_code('football', play_type, c)
                    bets.append({
                        "match": match_id,
                        "type": play_type,
                        "choice": c,
                        "machine_choice": m_code
                    })

                if not bets:
                    raise ValueError("未解析到有效选项")

                valid_tickets.append({
                    "id": line_idx + 1,
                    "raw": line,
                    "bets": bets,
                    "passType": "1x1"
                })

            except Exception as e:
                # 这里返回中文错误信息
                errors.append(f"第 {line_idx+1} 行: '{line}' -> 解析失败: {str(e)}")

        return {"tickets": valid_tickets, "errors": errors}
