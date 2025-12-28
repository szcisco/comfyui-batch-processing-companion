#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
from logging.handlers import RotatingFileHandler

class Logger:
    def __init__(self, name=__name__, log_level=logging.DEBUG):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        
        # 创建logs目录
        log_dir = os.path.join("config", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建文件处理器
        log_file = os.path.join(log_dir, "app.log")
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器到 logger
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def get_logger(self):
        """获取logger实例"""
        return self.logger
    
    def debug(self, message, exc_info=False):
        """记录debug级别日志"""
        self.logger.debug(message, exc_info=exc_info)
    
    def info(self, message, exc_info=False):
        """记录info级别日志"""
        self.logger.info(message, exc_info=exc_info)
    
    def warning(self, message, exc_info=False):
        """记录warning级别日志"""
        self.logger.warning(message, exc_info=exc_info)
    
    def error(self, message, exc_info=False):
        """记录error级别日志"""
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message, exc_info=False):
        """记录critical级别日志"""
        self.logger.critical(message, exc_info=exc_info)