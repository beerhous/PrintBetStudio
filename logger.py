# -*- coding: utf-8 -*-
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# === 配置 ===
LOG_DIR = "logs"
LOG_FILE_NAME = "printbet.log"
MAX_BYTES = 5 * 1024 * 1024  # 5MB
BACKUP_COUNT = 10            # 保留最近10个文件

def setup_logger(name="PrintBet"):
    """
    初始化日志系统
    """
    # 1. 确定日志路径 (兼容 EXE 和 开发环境)
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    log_dir_path = os.path.join(base_dir, LOG_DIR)
    
    # 创建 logs 文件夹
    if not os.path.exists(log_dir_path):
        try:
            os.makedirs(log_dir_path)
        except Exception as e:
            print(f"[FATAL] 无法创建日志目录: {e}")
            return logging.getLogger(name)

    log_file_path = os.path.join(log_dir_path, LOG_FILE_NAME)

    # 2. 获取 Logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG) # 捕获所有级别，由 Handler 决定输出什么

    # 防止重复添加 Handler
    if logger.handlers:
        return logger

    # 3. 格式化器
    # 格式: [时间] [级别] [文件名:行号] - 消息
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )

    # 4. 文件处理器 (File Handler) - 详细记录
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=MAX_BYTES, 
        backupCount=BACKUP_COUNT, 
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # 5. 控制台处理器 (Console Handler) - 简略记录
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # 6. 添加到 Logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("=== 日志系统初始化完成 ===")
    logger.info(f"日志文件路径: {log_file_path}")

    return logger

# 全局单例
log = setup_logger()
