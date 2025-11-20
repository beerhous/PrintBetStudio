# -*- coding: utf-8 -*-
import json
import os
import sys
import shutil
from datetime import datetime

# === 默认配置清单 ===
# 这是软件的“出厂设置”，当配置文件缺失或损坏时使用
DEFAULT_CONFIG = {
    "app_name": "PrintBet Studio",
    "version": "5.0.0",
    
    # 硬件连接
    "printer_name": "",  # 留空代表自动选择系统默认或列表第一个
    "ocr_url": "http://127.0.0.1:1224/api/ocr",
    
    # 业务偏好
    "default_pass_type": "2x1",
    "default_multiplier": 10,
    
    # 高级设置
    "paper_width": 576,  # 80mm 热敏纸的标准像素宽
    "debug_mode": False,
    "log_level": "INFO"
}

class ConfigManager:
    def __init__(self, filename="config.json"):
        self._config_path = self._get_config_path(filename)
        self.config = self.load_config()

    def _get_config_path(self, filename):
        """
        获取配置文件的绝对路径。
        兼容 IDE 开发环境和 PyInstaller 打包后的 EXE 环境。
        """
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 EXE，配置文件放在 EXE 同级目录
            base_dir = os.path.dirname(sys.executable)
        else:
            # 如果是脚本运行，放在当前脚本同级目录
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(base_dir, filename)

    def load_config(self):
        """
        加载配置，包含容错和合并逻辑。
        """
        # 1. 如果文件不存在，直接返回默认值
        if not os.path.exists(self._config_path):
            # 第一次运行时，自动创建一个默认配置文件
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                
            # 2. 合并逻辑 (Schema Migration)
            # 确保即使读取了旧版配置文件，新版增加的字段也能有默认值
            # 使用 DEFAULT_CONFIG 作为底版，用 saved_config 覆盖它
            merged_config = DEFAULT_CONFIG.copy()
            merged_config.update(saved_config)
            
            return merged_config

        except json.JSONDecodeError:
            print(f"[Config Error] 配置文件 {self._config_path} 格式损坏。")
            # 备份损坏的文件
            self._backup_corrupt_file()
            return DEFAULT_CONFIG.copy()
            
        except Exception as e:
            print(f"[Config Error] 读取失败: {e}")
            return DEFAULT_CONFIG.copy()

    def save_config(self, new_config):
        """
        保存配置到磁盘。
        """
        try:
            # 更新内存中的配置
            self.config.update(new_config)
            
            # 写入磁盘
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Config Error] 保存失败: {e}")
            return False

    def get(self, key, default=None):
        """
        安全的获取配置项，如果 key 不存在则返回默认值。
        """
        # 优先从当前配置取，没有则从默认配置取，再没有则返回传入的 default
        val = self.config.get(key)
        if val is None:
            val = DEFAULT_CONFIG.get(key, default)
        return val

    def _backup_corrupt_file(self):
        """
        备份损坏的配置文件，方便排查问题
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self._config_path}.{timestamp}.bak"
            shutil.copy(self._config_path, backup_path)
            print(f"[Config] 已备份损坏的配置文件至: {backup_path}")
        except Exception as e:
            print(f"[Config] 备份失败: {e}")

# 单例测试
if __name__ == "__main__":
    mgr = ConfigManager()
    print("Current Config:", mgr.config)
    mgr.save_config({"test_key": "test_value"})
