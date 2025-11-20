# -*- coding: utf-8 -*-
import re

class SmartBetParser:
    def __init__(self):
        # === 字符混淆纠错字典 ===
        self.OCR_FIXES = {
            'O': '0', 'o': '0', 'D': '0', 'Q': '0',
            'l': '1', 'I': '1', '|': '1', 'i': '1', ']': '1', '[': '1',
            'Z': '2', 'z': '2',
            'S': '5', 's': '5',
            'b': '6', 'G': '6',
            'q': '9', 'g': '9',
            '：': ':', ';': ':' # 标点纠错
        }

    def _sanitize_text(self, text):
        """
        文本清洗：替换混淆字符
        """
        # 1. 全角转半角
        text = text.replace('：', ':').replace('（', '(').replace('）', ')')
        # 2. 移除干扰符号
        text = text.replace(' ', '').replace('.', '')
        return text

    def _smart_replace_digits(self, text):
        """
        针对数字区域的智能纠错
        例如: "周三3O5" -> "周三305"
        """
        chars = list(text)
        for i, c in enumerate(chars):
            if c in self.OCR_FIXES:
                chars[i] = self.OCR_FIXES[c]
        return "".join(chars)

    def _cluster_rows(self, data, threshold=25):
        # (保留之前的聚类算法，此处省略以节省篇幅，请复用之前的代码)
        # ...
        # 这里的代码与上一版一致
        data.sort(key=lambda x: x['box'][0][1])
        rows = []
        if not data: return rows
        curr = [data[0]]
        for i in range(1, len(data)):
            y1 = curr[-1]['box'][0][1]
            y2 = data[i]['box'][0][1]
            if abs(y2 - y1) < threshold: curr.append(data[i])
            else:
                rows.append(curr)
                curr = [data[i]]
        rows.append(curr)
        return rows

    def parse(self, ocr_data):
        rows = self._cluster_rows(ocr_data)
        bets = []
        warnings = [] # 收集潜在错误
        
        for row in rows:
            # 原始行文本
            raw_line = " ".join([b['text'] for b in row])
            
            # 1. 场次提取 (支持模糊容错)
            # 匹配 "周x" + "3位杂乱字符"
            m_match = re.search(r'(周[一二三四五六日])\s*([A-Za-z0-9]{3})', raw_line)
            
            if not m_match:
                # 尝试匹配纯数字 3001 模式
                m_num = re.search(r'\b([1-7][0-9A-Za-z]{3})\b', raw_line)
                if m_num:
                    raw_id = self._smart_replace_digits(m_num.group(1)) # 纠错 3O1 -> 301
                    match_id = "周x" + raw_id[1:]
                else:
                    continue
            else:
                # 纠错编号部分: 周三3O5 -> 周三305
                fixed_num = self._smart_replace_digits(m_match.group(2))
                match_id = m_match.group(1) + fixed_num

            # 2. 玩法与选项提取
            ptype, choice = "SPF", ""
            
            # A. 比分 (CBF) - 强特征 ":"
            if ":" in raw_line:
                ptype = "CBF"
                # 提取 x:y，同时修复 l:0 -> 1:0
                clean_line = self._sanitize_text(raw_line)
                # 查找形如 1:0, 2:1, 胜其他 的模式
                m_score = re.search(r'(\d{1,2}:\d{1,2}|胜其他|平其他|负其他)', clean_line)
                if m_score:
                    choice = m_score.group(1)
                else:
                    # 尝试修复: 比如识别成 2:O (字母O)
                    fixed_line = self._smart_replace_digits(clean_line)
                    m_score_fix = re.search(r'(\d{1,2}:\d{1,2})', fixed_line)
                    if m_score_fix: choice = m_score_fix.group(1)

            # B. 胜平负 / 让球
            elif "让" in raw_line:
                ptype = "RQSPF"
                if "胜" in raw_line: choice = "让胜"
                elif "平" in raw_line: choice = "让平"
                elif "负" in raw_line: choice = "让负"
            else:
                ptype = "SPF"
                # 排除 "胜分差" 这种干扰词
                if "分" not in raw_line: 
                    if "胜" in raw_line: choice = "胜"
                    elif "平" in raw_line: choice = "平"
                    elif "负" in raw_line: choice = "负"
            
            # 3. 结果校验
            if choice:
                bets.append({"match": match_id, "type": ptype, "choice": choice})
            else:
                # 发现了场次但没发现选项 -> 记录警告
                warnings.append(f"场次 {match_id} 识别不完整 (缺少选项)")

        return bets, warnings
