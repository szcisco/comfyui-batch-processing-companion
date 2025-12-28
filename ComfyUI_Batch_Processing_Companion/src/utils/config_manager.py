#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
import os

class ConfigManager:
    def __init__(self, config_file="setting.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        # 读取配置文件
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding="utf-8")
        
        # 确保所有配置组存在
        self._ensure_sections()
        
        # 加载配置
        self._load_config()
    
    def _ensure_sections(self):
        """确保所有必要的配置节存在"""
        required_sections = ["API", "Application", "UI", "ComfyUI", "System", "Ollama", "TencentTranslate"]
        for section in required_sections:
            if section not in self.config:
                self.config[section] = {}
    
    def _get_value(self, section, key, fallback=None):
        """获取配置值并去除注释"""
        value = self.config.get(section, key, fallback=fallback)
        if isinstance(value, str):
            value = value.split(';')[0].strip()
        return value
    
    def _load_config(self):
        """加载配置项"""
        # API相关配置
        self.COMFYUI_URL = self._get_value("API", "base_url", "http://127.0.0.1:8188")
        self.TIMEOUT = int(self._get_value("API", "timeout", "2700"))
        self.retry_count = int(self._get_value("API", "retry_count", "3"))
        
        # ComfyUI相关配置
        # 优先读取[comfyui_gen]章节的workflow_path配置（用户期望使用的版本）
        self.WORKFLOW_PATH = self._get_value("comfyui_gen", "workflow_path", "")
        # 如果[comfyui_gen]章节没有配置或配置为空，回退到[ComfyUI]章节的配置
        if not self.WORKFLOW_PATH:
            self.WORKFLOW_PATH = self._get_value("ComfyUI", "workflow_path", r"config\API\test_wan2.2-14B状态+生图_接口.json")
        
        # Application相关配置
        self.IMAGE_SAVE_DIR = self._get_value("Application", "default_save_path", "image")
        self.log_level = self._get_value("Application", "log_level", "INFO")
        self.temp_cleanup = self._get_value("Application", "temp_cleanup", "on_exit")
        
        # System相关配置
        self.content_rows = int(self._get_value("System", "content_rows", "30"))
        self.project_dir = self._get_value("System", "project_dir", "project")
        
        # UI相关配置
        self.ui_width = int(self._get_value("UI", "width", "1100"))
        self.ui_height = int(self._get_value("UI", "height", "1000"))
        self.ui_position_x = int(self._get_value("UI", "position_x", "0"))
        self.ui_position_y = int(self._get_value("UI", "position_y", "0"))
        
        # 主题配置处理
        custom_theme = self._get_value("UI", "custom_theme", "")
        old_theme = self._get_value("UI", "theme", "")
        
        if custom_theme:
            self.ui_theme = custom_theme
        elif old_theme:
            self.ui_theme = old_theme
        else:
            self.ui_theme = "cyborg"
            self.config["UI"]["custom_theme"] = self.ui_theme
            self.save_config()
        
        self.config["UI"]["theme"] = self.ui_theme
        self.ui_font_size = int(self._get_value("UI", "font_size", "10"))
        
        # 批量生成图片数范围
        self.BATCH_RANGE = list(range(1, 6))
        
        # TencentTranslate相关配置
        self.tencent_appid = self._get_value("TencentTranslate", "appid", "")
        self.tencent_secret_id = self._get_value("TencentTranslate", "secret_id", "")
        self.tencent_secret_key = self._get_value("TencentTranslate", "secret_key", "")
        self.tencent_api_host = self._get_value("TencentTranslate", "host", "tmt.tencentcloudapi.com")
        self.tencent_api_action = self._get_value("TencentTranslate", "action", "TextTranslate")
        self.tencent_api_version = self._get_value("TencentTranslate", "version", "2018-03-21")
        self.tencent_api_region = self._get_value("TencentTranslate", "region", "ap-guangzhou")
    
    def save_config(self):
        """保存配置文件"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)
    
    def get(self, section, key, fallback=None):
        """获取配置项"""
        return self._get_value(section, key, fallback)
    
    def set(self, section, key, value):
        """设置配置项"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save_config()