import re

class SmartBetParser:
    def _cluster_rows(self, data, threshold=25):
        # 按 Y 轴聚类算法
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
        for row in rows:
            # 简单拼合一行
            line = " ".join([b['text'] for b in row])
            
            # 提取周几 (match)
            m = re.search(r'(周[一二三四五六日]\d{3})', line)
            if not m:
                # 尝试提取纯数字 3001
                m_num = re.search(r'\b([1-7]\d{3})\b', line)
                if m_num: match_id = "周x" + m_num.group(1)[1:]
                else: continue
            else:
                match_id = m.group(1)

            # 提取玩法 (type) & 选项 (choice)
            # 简单关键词匹配
            ptype, choice = "SPF", ""
            if ":" in line and re.search(r'\d:\d', line): 
                ptype = "CBF"
                choice = re.search(r'(\d+:\d+|胜其他|平其他|负其他)', line).group(1)
            elif "让" in line:
                ptype = "RQSPF"
                if "胜" in line: choice = "让胜"
                elif "平" in line: choice = "让平"
                elif "负" in line: choice = "让负"
            else:
                ptype = "SPF"
                if "胜" in line: choice = "胜"
                elif "平" in line: choice = "平"
                elif "负" in line: choice = "负"

            if choice:
                bets.append({"match": match_id, "type": ptype, "choice": choice})
        return bets
