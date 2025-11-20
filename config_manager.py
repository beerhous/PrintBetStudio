# -*- coding: utf-8 -*-
import json
import os

CONFIG_FILE = "config.json"

# 默认配置增加用户偏好
DEFAULT_CONFIG = {
    "printer_name": "XP-58",
    "ocr_url": "http://127.0.0.1:1224/api/ocr",
    "default_pass_type": "2x1",
    "default_multiplier": 10,
    "paper_width": "58mm",  # 预留纸张设置
    "auto_cut": True        # 预留切纸设置
}

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return DEFAULT_CONFIG.copy()
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 合并默认配置，防止旧版配置文件缺少新字段
                merged = DEFAULT_CONFIG.copy()
                merged.update(data)
                return merged
        except:
            return DEFAULT_CONFIG.copy()

    def save_config(self, new_config):
        # 更新配置
        self.config.update(new_config)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def get(self, key):
        return self.config.get(key, DEFAULT_CONFIG.get(key))
