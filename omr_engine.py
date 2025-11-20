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
        # 预加载三个核心文件
        for name in ['bb_sf_3', 'bb_sf_6', 'bb_rfsf_3']:
            try:
                with open(resource_path(f'omr_maps/{name}.json'), 'r', encoding='utf-8') as f:
                    self.maps[name] = json.load(f)
            except: pass

    def _draw_block(self, draw, x, y, w, h, filled=True):
        if filled: draw.rectangle([x, y, x+w, y+h], fill=0)
        else: draw.rectangle([x, y, x+w, y+h], outline=0, fill=1)

    # === 1. 胜负3关渲染 ===
    def generate_bb_sf_3(self, bets, pass_type, multiplier):
        cfg = self.maps['basketball_sf_3']
        return self._render_standard_3(cfg, bets, pass_type, multiplier)

    # === 2. 胜负6关渲染 ===
    def generate_bb_sf_6(self, bets, pass_type, multiplier):
        cfg = self.maps['basketball_sf_6']
        return self._render_standard_6(cfg, bets, pass_type, multiplier)

    # === 3. 让分胜负3关渲染 (加法制) ===
    def generate_bb_rfsf_3(self, bets, pass_type, multiplier):
        cfg = self.maps['basketball_rfsf_3']
        return self._render_additive_3(cfg, bets, pass_type, multiplier)

    # --- 核心渲染逻辑 ---
    def _render_standard_3(self, cfg, bets, pass_type, multiplier):
        img = Image.new('1', (cfg['meta']['width'], cfg['meta']['height']), 1)
        draw = ImageDraw.Draw(img)
        # 省略辅助线绘制...
        for idx, bet in enumerate(bets):
            if idx >= 3: break
            bx = cfg['layout']['columns'][idx]['x_offset']
            self._draw_match_header(draw, bx, cfg['layout']['rows'], bet['match'])
            # 选项
            opt_cfg = cfg['layout']['rows']['options']
            code = str(bet['machine_choice'])
            if code in opt_cfg:
                self._draw_block(draw, bx + opt_cfg[code]['x_rel'], opt_cfg['label_y'], 25, 14)
        self._draw_footer(draw, cfg, pass_type, multiplier)
        return img

    def _render_standard_6(self, cfg, bets, pass_type, multiplier):
        img = Image.new('1', (cfg['meta']['width'], cfg['meta']['height']), 1)
        draw = ImageDraw.Draw(img)
        for idx, bet in enumerate(bets):
            if idx >= 6: break
            is_top = idx < 3
            base_y = cfg['layout']['blocks']['top']['base_y'] if is_top else cfg['layout']['blocks']['bottom']['base_y']
            bx = cfg['layout']['columns'][idx % 3]['x_offset']
            
            # 使用相对坐标绘制
            self._draw_match_header_relative(draw, bx, base_y, cfg['layout']['rows_relative'], bet['match'])
            
            opt_cfg = cfg['layout']['rows_relative']['options']
            code = str(bet['machine_choice'])
            if code in opt_cfg:
                 self._draw_block(draw, bx + opt_cfg[code]['x_rel'], base_y + opt_cfg['label_y'], 25, 14)
        
        self._draw_footer(draw, cfg, pass_type, multiplier)
        return img

    def _render_additive_3(self, cfg, bets, pass_type, multiplier):
        img = Image.new('1', (cfg['meta']['width'], cfg['meta']['height']), 1)
        draw = ImageDraw.Draw(img)
        for idx, bet in enumerate(bets):
            if idx >= 3: break
            bx = cfg['layout']['columns'][idx]['x_offset']
            
            # 绘制周几
            week = bet['match'][:2]
            if week in cfg['layout']['rows']['week']['map']:
                wi = cfg['layout']['rows']['week']['map'].index(week)
                wx = bx + (wi % 4) * 35
                wy = cfg['layout']['rows']['week']['start_y'] + (30 if wi >=4 else 0)
                self._draw_block(draw, wx, wy, 25, 14)
            
            # 绘制加法制数字
            num_str = ''.join(filter(str.isdigit, bet['match']))[-3:]
            num_cfg = cfg['layout']['rows']['match_num_additive']
            for i, key in enumerate(['hundreds', 'tens', 'units']):
                val = int(num_str[i])
                comps = self._get_additive_components(val)
                for vi, vv in enumerate(num_cfg[key]['vals']):
                    if vv in comps:
                        self._draw_block(draw, bx + vi*35, num_cfg[key]['y'], 25, 14)

            # 选项
            code = str(bet['machine_choice'])
            opt_cfg = cfg['layout']['rows']['options']
            if code in opt_cfg:
                self._draw_block(draw, bx + opt_cfg[code]['x_rel'], opt_cfg['label_y'], 25, 14)

        self._draw_footer(draw, cfg, pass_type, multiplier)
        return img

    # 辅助：数字拆分 3 -> [1, 2]
    def _get_additive_components(self, val):
        res = []
        for v in [5, 4, 2, 1]:
            if val >= v:
                res.append(v)
                val -= v
        return res

    def _draw_footer(self, draw, cfg, pt, mu):
        # 过关
        if pt in cfg['layout']['footer']['pass']:
            p = cfg['layout']['footer']['pass'][pt]
            self._draw_block(draw, p['x'], p['y'], 25, 14)
        # 倍数 (拆分逻辑)
        m_val = int(mu)
        all_vals = []
        for r in cfg['layout']['footer']['multi']['rows']: all_vals.extend(r['vals'])
        # 简单拆分逻辑... (需自行实现贪心算法匹配all_vals中的字符串)

    def _draw_match_header(self, draw, bx, rows_cfg, match_str):
        # 标准数字绘制... (胜负3关用)
        pass

    def _draw_match_header_relative(self, draw, bx, by, rows_cfg, match_str):
        # 相对坐标绘制... (胜负6关用)
        pass

    # === 路由分发 ===
    def dispatch(self, bets, pass_type, multiplier, play_type="SF"):
        is_6 = len(bets) > 3 or "4x" in pass_type or "5x" in pass_type or "6x" in pass_type
        
        if play_type == "SF":
            return self.generate_bb_sf_6(bets, pass_type, multiplier) if is_6 else self.generate_bb_sf_3(bets, pass_type, multiplier)
        elif play_type == "RFSF":
            # 6关暂未配置，回退到3关逻辑
            return self.generate_bb_rfsf_3(bets, pass_type, multiplier)
            
        return Image.new('1', (576, 100), 1)
