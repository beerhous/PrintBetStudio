# -*- coding: utf-8 -*-
import json
import os
import sys
import shutil
import tempfile
from datetime import datetime

# === 1. 默认配置 (软件出厂设置) ===
# 这是唯一的真理来源。任何时候读取配置，都以此为蓝本。
DEFAULT_CONFIG = {
    "version": "5.0.0",
    "last_updated": "",
    
    # --- 硬件连接 ---
    "printer_name": "",           # 留空则自动查找默认打印机
    "ocr_url": "http://127.0.0.1:1224/api/ocr",
    
    # --- 业务偏好 ---
    "default_pass_type": "2x1",   # 默认过关方式
    "default_multiplier": 10,     # 默认倍数
    "auto_cut": True,             # 打印后是否切纸
    
    # --- 界面设置 ---
    "theme": "light",
    "window_width": 1200,
    "window_height": 850
}

CONFIG_FILENAME = "config.json"

class ConfigManager:
    def __init__(self):
        self._config_path = self._get_config_path()
        self.config = self._load_robust()

    def _get_config_path(self):
        """
        获取配置文件路径。
        兼容 PyInstaller 打包后的环境，确保配置保存在 EXE 同级目录。
        """
        if getattr(sys, 'frozen', False):
            # EXE 运行模式：路径为 EXE 所在文件夹
            base_dir = os.path.dirname(sys.executable)
        else:
            # 脚本运行模式：路径为脚本所在文件夹
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(base_dir, CONFIG_FILENAME)

    def _load_robust(self):
        """
        健壮的加载逻辑：读取 -> 校验 -> 合并 -> 返回
        """
        # 1. 文件不存在：初始化默认值
        if not os.path.exists(self._config_path):
            print(f"[Config] 初始化新配置文件: {self._config_path}")
            self._save_atomic(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

        try:
            # 2. 尝试读取
            with open(self._config_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            
            # 3. 模式合并 (Schema Merge)
            # 使用默认配置作为底版，用保存的数据覆盖它
            # 这样可以确保新版本增加的字段（如 'theme'）会自动补全
            merged_config = DEFAULT_CONFIG.copy()
            merged_config.update(saved_data)
            
            # 如果合并后有变化（说明旧配置缺字段），自动保存一次
            if saved_data.keys() != merged_config.keys():
                print("[Config] 检测到版本升级，自动修补配置文件...")
                self._save_atomic(merged_config)
                
            return merged_config

        except json.JSONDecodeError:
            # 4. 文件损坏处理：备份 -> 重置
            print(f"[Config Error] JSON 格式错误！正在重置...")
            self._backup_corrupt_file()
            return DEFAULT_CONFIG.copy()
            
        except Exception as e:
            print(f"[Config Critical] 读取失败: {e}")
            return DEFAULT_CONFIG.copy()

    def save(self, new_data):
        """
        公开的保存接口
        """
        try:
            # 更新内存
            self.config.update(new_data)
            self.config['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 写入磁盘
            self._save_atomic(self.config)
            return True
        except Exception as e:
            print(f"[Config Error] 保存失败: {e}")
            return False

    def get(self, key, default=None):
        """安全获取配置"""
        return self.config.get(key, default)

    def _save_atomic(self, data):
        """
        原子性写入：先写临时文件，再重命名。
        防止写入一半断电导致文件变成空白。
        """
        dir_name = os.path.dirname(self._config_path)
        # 创建临时文件
        fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
        
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            # 原子替换
            os.replace(temp_path, self._config_path)
        except Exception as e:
            os.remove(temp_path)
            raise e

    def _backup_corrupt_file(self):
        """备份损坏的文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self._config_path}.{timestamp}.bak"
            shutil.copy(self._config_path, backup_path)
            print(f"[Config] 已备份坏文件至: {backup_path}")
            # 重置
            self._save_atomic(DEFAULT_CONFIG)
        except:
            pass
