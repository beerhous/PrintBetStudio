# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw
import json
import os
import sys

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class OMREngine:
    def __init__(self):
        self.maps = {}
        # 预加载所有配置文件
        map_list = [
            'bb_sf_3', 'bb_sf_6', 
            'bb_rfsf_3', 'bb_rfsf_6', 
            'bb_dxf_3', 'bb_dxf_6', 
            'bb_sfc_3'
        ]
        for name in map_list:
            try:
                with open(resource_path(f'omr_maps/{name}.json'), 'r', encoding='utf-8') as f:
                    self.maps[name] = json.load(f)
            except: pass

    def _draw_block(self, draw, x, y, w, h, filled=True):
        if filled: draw.rectangle([x, y, x+w, y+h], fill=0)
        else: draw.rectangle([x, y, x+w, y+h], outline=0, fill=1)

    # === 辅助算法：加法制拆分 (3 -> [1,2]) ===
    def _get_additive_components(self, val):
        res = []
        temp = int(val)
        for v in [5, 4, 2, 1]:
            if temp >= v:
                res.append(v)
                temp -= v
        return res

    # === 辅助算法：绘制通用倍数 ===
    def _draw_multiplier_grid(self, draw, multi, cfg):
        m_val = int(multi)
        targets = []
        # 假设 cfg['rows'] 里的 vals 是字符，需转换
        all_vals = []
        for r in cfg['rows']: 
            for v in r['vals']: all_vals.append(int(v))
        all_vals.sort(reverse=True)
        
        temp = m_val
        for v in all_vals:
            if temp >= v:
                targets.append(str(v))
                temp -= v
        
        start_x = cfg['start_x']
        gap_x = cfg['gap_x']
        for row in cfg['rows']:
            for i, val_str in enumerate(row['vals']):
                if val_str in targets:
                    self._draw_block(draw, start_x + i*gap_x, row['y'], 25, 14)

    # === 核心生成器：单层加法制 (RFSF3, DXF3) ===
    def _generate_additive_3(self, bets, pass_type, multiplier, map_name):
        cfg = self.maps.get(map_name)
        if not cfg: return Image.new('1', (576, 100), 1)
        
        width, height = cfg['meta']['width'], cfg['meta']['height']
        img = Image.new('1', (width, height), 1)
        draw = ImageDraw.Draw(img)
        
        # 绘制锚点和线
        draw.line([10, 120, 566, 120], fill=0, width=2)
        draw.line([10, 450, 566, 450], fill=0, width=2)
        for i in range(0, height, 30): draw.rectangle([0, i, 15, i+15], fill=0)

        for idx, bet in enumerate(bets):
            if idx >= 3: break
            base_x = cfg['layout']['columns'][idx]['x_offset']
            
            # 解析周数和数字
            week_str = bet['match'][:2]
            num_str = ''.join(filter(str.isdigit, bet['match']))[-3:]
            h, t, u = int(num_str[0]), int(num_str[1]), int(num_str[2])
            
            # 1. 涂周
            if week_str in cfg['layout']['rows']['week']['map']:
                wi = cfg['layout']['rows']['week']['map'].index(week_str)
                row_add = 30 if wi >= 4 else 0
                wx = base_x + (wi % 4) * cfg['layout']['rows']['week']['gap_x']
                self._draw_block(draw, wx, cfg['layout']['rows']['week']['start_y'] + row_add, 25, 14)

            # 2. 涂编号 (加法)
            num_cfg = cfg['layout']['rows']['match_num_additive']
            for digit, key in zip([u, t, h], ['units', 'tens', 'hundreds']):
                comps = self._get_additive_components(digit)
                for i, val in enumerate(num_cfg[key]['vals']):
                    if val in comps:
                        self._draw_block(draw, base_x + i*35, num_cfg[key]['y'], 25, 14)

            # 3. 涂选项
            code = str(bet['machine_choice'])
            opt_cfg = cfg['layout']['rows']['options']
            if code in opt_cfg:
                self._draw_block(draw, base_x + opt_cfg[code]['x_rel'], opt_cfg['label_y'], 25, 14)

        # 4. 底部
        if pass_type in cfg['layout']['footer']['pass']:
            p = cfg['layout']['footer']['pass'][pass_type]
            self._draw_block(draw, p['x'], p['y'], 25, 14)
            
        self._draw_multiplier_grid(draw, multiplier, cfg['layout']['footer']['multi'])
        return img

    # === 核心生成器：双层加法制 (RFSF6, DXF6) ===
    def _generate_additive_6(self, bets, pass_type, multiplier, map_name):
        cfg = self.maps.get(map_name)
        if not cfg: return Image.new('1', (576, 100), 1)
        
        width, height = cfg['meta']['width'], cfg['meta']['height']
        img = Image.new('1', (width, height), 1)
        draw = ImageDraw.Draw(img)
        
        draw.line([10, 130, 566, 130], fill=0, width=2)
        draw.line([10, 560, 566, 560], fill=0, width=2)
        draw.line([10, 930, 566, 930], fill=0, width=2)
        for i in range(0, height, 30): draw.rectangle([0, i, 15, i+15], fill=0)

        for idx, bet in enumerate(bets):
            if idx >= 6: break
            is_top = idx < 3
            base_y = cfg['layout']['blocks']['top']['base_y'] if is_top else cfg['layout']['blocks']['bottom']['base_y']
            col_idx = idx if is_top else idx - 3
            base_x = cfg['layout']['columns'][col_idx]['x_offset']
            rows_rel = cfg['layout']['rows_relative']
            
            # 解析
            week_str = bet['match'][:2]
            num_str = ''.join(filter(str.isdigit, bet['match']))[-3:]
            h, t, u = int(num_str[0]), int(num_str[1]), int(num_str[2])
            
            # 1. 涂周
            if week_str in rows_rel['week']['map']:
                wi = rows_rel['week']['map'].index(week_str)
                row_add = 30 if wi >= 4 else 0
                wx = base_x + (wi % 4) * rows_rel['week']['gap_x']
                self._draw_block(draw, wx, base_y + rows_rel['week']['start_y'] + row_add, 25, 14)
                
            # 2. 涂编号
            num_cfg = rows_rel['match_num_additive']
            for digit, key in zip([u, t, h], ['units', 'tens', 'hundreds']):
                comps = self._get_additive_components(digit)
                for i, val in enumerate(num_cfg[key]['vals']):
                    if val in comps:
                        self._draw_block(draw, base_x + i*35, base_y + num_cfg[key]['y'], 25, 14)
                        
            # 3. 涂选项
            code = str(bet['machine_choice'])
            if code in rows_rel['options']:
                self._draw_block(draw, base_x + rows_rel['options'][code]['x_rel'], base_y + rows_rel['options']['label_y'], 25, 14)

        # 4. 底部
        if pass_type in cfg['layout']['footer']['pass']:
            p = cfg['layout']['footer']['pass'][pass_type]
            self._draw_block(draw, p['x'], p['y'], 25, 14)
        self._draw_multiplier_grid(draw, multiplier, cfg['layout']['footer']['multi'])
        return img

    # === 路由分发 ===
    def dispatch(self, bets, pass_type, multiplier, play_type="SF"):
        is_6 = len(bets) > 3 or any(x in pass_type for x in ["4x","5x","6x"])
        
        if play_type == "SF":
            # 需保留之前的 SF 逻辑代码 (generate_bb_sf_3/6)，此处略去以聚焦新需求
            pass 
            
        # === 核心：RFSF 和 DXF 的路由 ===
        elif play_type == "RFSF":
            if is_6: return self._generate_additive_6(bets, pass_type, multiplier, 'basketball_rfsf_6')
            else:    return self._generate_additive_3(bets, pass_type, multiplier, 'basketball_rfsf_3')
            
        elif play_type == "DXF":
            if is_6: return self._generate_additive_6(bets, pass_type, multiplier, 'basketball_dxf_6')
            else:    return self._generate_additive_3(bets, pass_type, multiplier, 'basketball_dxf_3')
            
        return Image.new('1', (576, 100), 1)
