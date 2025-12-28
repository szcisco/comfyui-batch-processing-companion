#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
ComfyUI 批量处理伴侣 (ComfyUI Batch Processing Companion)
================================================================================

项目名称: ComfyUI批量处理伴侣 / ComfyUI_Batch_Processing_Companion
版本: v1.0
作者: victor (szcisco@gmail.com)
创建日期: 2025-12-29
开源协议: GNU General Public License v3.0 (GPLv3)

GitHub: https://github.com/szcisco/ComfyUI_Batch_Processing_Companion
联系方式:
    - Email: szcisco@gmail.com
    - QQ群: https://qm.qq.com/q/eBWAzdjzmE
    - WeChat: lilian_wang1206

描述:
    专为 ComfyUI 用户打造的桌面端批量图像生成工具。
    通过可视化界面简化 ComfyUI API 的调用流程，
    让用户无需编写代码即可实现批量图生图、文生图等 AI 绘图任务。

Copyright (C) 2025 victor (szcisco@gmail.com)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
================================================================================
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import configparser
import json
import time
import shutil
import uuid
import subprocess
import threading

# Coze SDK 导入
from cozepy import COZE_CN_BASE_URL
from cozepy import Coze, TokenAuth, Stream, WorkflowEvent, WorkflowEventType

# 导入日志模块
from src.utils.logger import Logger

# 导入多语言支持模块
from src.utils.language import tr, LanguageManager, get_language_display_name, get_language_code

# 支持重复section的ConfigParser子类
class MultiConfigParser(configparser.ConfigParser):
    # 英文到中文的索引名映射（类变量，从setting.ini加载）
    _eng_to_chs_mapping = None
    
    @classmethod
    def load_eng_to_chs_mapping(cls, setting_ini_path="setting.ini"):
        """从setting.ini加载英文到中文的索引名映射"""
        if cls._eng_to_chs_mapping is not None:
            return cls._eng_to_chs_mapping
        
        cls._eng_to_chs_mapping = {}
        try:
            config = configparser.ConfigParser()
            config.read(setting_ini_path, encoding='utf-8')
            if config.has_section('VariableBindings_EngToChs'):
                for key, value in config.items('VariableBindings_EngToChs'):
                    # ConfigParser会将key转为小写，需要保留原始大小写
                    cls._eng_to_chs_mapping[key] = value
        except Exception as e:
            print(f"加载英文到中文映射失败: {e}")
        
        # 手动添加大小写敏感的映射（因为ConfigParser会转小写）
        cls._eng_to_chs_mapping.update({
            'None': '无',
            'Image Load': '图片载入',
            'Positive Prompt': '正向提示词',
            'Negative Prompt': '负面提示词',
            'K Sampler Steps': 'K采样步值',
            'Image Width': '图片尺寸宽度',
            'Image Height': '图片尺寸高度',
            'Image Output': '图片输出',
            'Wideo Width': '视频尺寸宽度',
            'Video Height': '视频尺寸高度',
            'Video Output': '视频输出',
        })
        return cls._eng_to_chs_mapping
    
    def translate_section_name(self, section_name):
        """将英文section名称转换为中文"""
        if self._eng_to_chs_mapping is None:
            self.load_eng_to_chs_mapping()
        
        # 检查是否有带后缀的section名（如 "Image Load_2"）
        base_name = section_name
        suffix = ""
        if '_' in section_name:
            parts = section_name.rsplit('_', 1)
            if parts[1].isdigit():
                base_name = parts[0]
                suffix = '_' + parts[1]
        
        # 查找映射
        if base_name in self._eng_to_chs_mapping:
            return self._eng_to_chs_mapping[base_name] + suffix
        
        return section_name
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sections = []
        self._section_data = []
    
    def read(self, filenames, encoding=None):
        """读取INI文件，支持重复section，自动将英文索引名转换为中文"""
        if isinstance(filenames, str):
            filenames = [filenames]
        
        for filename in filenames:
            with open(filename, 'r', encoding=encoding) as f:
                current_section = None
                current_data = {}
                
                for line in f:
                    # 移除行首可能存在的UTF-8 BOM字节
                    line = line.lstrip('\ufeff')
                    # 去除行首尾的空白字符
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # 匹配section行：[section_name]
                    if line.startswith('[') and line.endswith(']'):
                        # 保存当前section
                        if current_section is not None:
                            self._sections.append(current_section)
                            self._section_data.append(current_data.copy())
                        # 开始新section，并进行英文到中文的转换
                        raw_section = line[1:-1]
                        current_section = self.translate_section_name(raw_section)
                        current_data = {}
                    # 匹配键值对：key = value
                    if '=' in line and current_section is not None:
                        key, value = line.split('=', 1)
                        current_data[key.strip()] = value.strip()
                
                # 保存最后一个section
                if current_section is not None:
                    self._sections.append(current_section)
                    self._section_data.append(current_data.copy())
    
    def sections(self):
        """返回所有section名称列表"""
        return self._sections
    
    def __getitem__(self, section):
        """获取指定section的数据"""
        # 这个方法在直接访问config[section]时调用，但我们不需要它
        # 我们会使用自定义的方式访问section数据
        return self._section_data[0]

class CreativeArea:
    def check_api_status(self):
        """测试当前ComfyUI API状态"""
        try:
            # 获取ComfyUI API URL
            comfyui_url = self.config.get("ComfyUI", "api_url", fallback=self.COMFYUI_URL)
            
            # 更新状态为测试中
            def update_status_testing():
                if hasattr(self, 'api_status_var'):
                    self.api_status_var.set(tr("状态: 测试中..."))
                    self.api_status_label.configure(foreground="#ff9900")
            
            # 显示结果
            def show_result(status, response=None):
                if status:
                    result_text = tr("状态: 正常")
                    color = "green"
                else:
                    result_text = tr("状态: 异常")
                    color = "red"
                
                # 更新界面状态
                if hasattr(self, 'api_status_var'):
                    self.api_status_var.set(result_text)
                    self.api_status_label.configure(foreground=color)
            
            # 测试API
            def api_test_thread():
                import requests
                status = False
                try:
                    response = requests.get(comfyui_url, timeout=5)
                    status = response.status_code == 200
                    print(f"API测试结果: {'正常' if status else '异常'}, 状态码: {response.status_code if status else '无响应'}")
                except Exception as e:
                    print(f"API测试失败: {str(e)}")
                    status = False
                
                # 在主线程更新UI
                self.root.after(0, lambda: show_result(status))
            
            # 在主线程更新UI为测试中
            self.root.after(0, update_status_testing)
            
            # 启动测试线程
            import threading
            threading.Thread(target=api_test_thread, daemon=True).start()
        except Exception as e:
            print(f"API测试失败: {str(e)}")
            if hasattr(self, 'api_status_var'):
                self.api_status_var.set(tr("状态: 错误"))
                self.api_status_label.configure(foreground="red")
    """创作区域类"""
    def __init__(self, root):
        """初始化"""
        # 初始化必要的属性
        self.row_height = 320
        self.content_rows = 30
        self.visible_rows = 15
        self.displayed_rows = {}
        self.content_offset = 0
        
        # 将工作目录切换到程序所在目录，确保相对路径正确
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        # 配置文件路径 - 使用相对路径
        self.config_file = "setting.ini"
        
        # 读取配置
        self.load_config()
        
        # 初始化UI
        self.root = root
        # 初始化窗口标题相关属性
        self.current_filename = "未保存"
        self.is_edited = False
        self.update_window_title()
        # 调整窗口高度，确保能看到所有按钮
        adjusted_height = max(self.ui_height, 1200)  # 将最小高度设置为1200像素
        
        # 计算屏幕中心位置
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - self.ui_width) // 2
        y = (screen_height - adjusted_height) // 2
        
        # 设置窗口位置为屏幕正中央
        self.root.geometry(f"{self.ui_width}x{adjusted_height}+{x}+{y}")
        self.root.resizable(True, True)
        
        
        
        # 初始化变量
        # 图片相关变量
        self.image_paths = []
        self.image_cache = []
        self.img_prompts = []
        self.img_labels = []
        self.img_frames = []
        
        # 提示词相关变量
        self.prompt_texts = []
        self.english_texts = []
        
        # 图片相关变量
        self.k_sampler_steps_list = []
        self.image_height_list = []
        self.image_width_list = []
        self.image_orientation_list = []
        self.generated_images = []
        # 绑定名称到节点ID的映射，用于动态获取SaveImage节点
        self.binding_node_map = {}
        # 批量生成相关变量
        self.batch_generate_count_list = []
        
        # UI相关变量
        # 提示窗口 - 用于显示K采样器步数提示
        self.tooltip = None
        self.select_all_var = None
        self.global_k_sampler_steps = None
        self.global_image_height = None
        self.global_image_width = None
        self.global_orientation = None
        
        # 新增：提示词配置标志位
        self.has_positive_prompt = True
        self.has_negative_prompt = True
        self.has_image_load = True  # 新增：图片载入模块标志位
        self.prompt_frames = []
        self.negative_prompt_frames = []
        self.positive_buttons_frames = []
        self.negative_buttons_frames = []
        self.content_no_frames = []  # 新增：存储No.框体实例
        self.content_img_frames = []  # 确保content_img_frames已初始化
        
        # 计时器相关变量
        self.timer_var = None
        self.timer_running = False
        self.start_time = 0
        self.timer_id = None
        self.row_timers = []
        self.row_timer_vars = []
        self.row_timer_running = []
        self.row_timer_ids = []
        self.row_timer_labels = []
        
        # 其他变量
        self.current_image_index = None
        self.button_frame = None
        self.api_image_frames = []
        self.image_item_vars = []
        
        # 翻译相关变量
        self.stop_translating = False
        # 添加fps_entry属性，防止加载配置时出错
        self.fps_entry = None
        
        # 初始化日志器
        self.logger = Logger()
        
        # 顶部框体动态布局相关变量
        self.top_frames = []
        self.top_frames_visible = {}
        
        # 创建样式
        self.style = ttk.Style()
        
        # 创建自定义按钮样式，文字大小缩小30%
        # 移除了按钮字体缩放功能
        
        # 从配置中加载主题
        theme = self.config.get("UI", "theme", fallback="cosmo")
        self.style.theme_use(theme)
        
        # 1. 创建水平滚动条 - 固定在底部，作为第一个创建的控件
        self.hscroll_frame = ttk.Frame(self.root, height=30, relief=tk.SUNKEN)
        self.hscroll_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=False)
        self.hscroll_frame.pack_propagate(False)  # 防止框架随内容收缩
        # 创建水平滚动条，先不指定command，稍后与Canvas关联
        self.hscrollbar = ttk.Scrollbar(self.hscroll_frame, orient=tk.HORIZONTAL)
        self.hscrollbar.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # 2. 创建固定顶部框架
        self.fixed_frame = ttk.Frame(self.root, padding="10")
        self.fixed_frame.pack(side=tk.TOP, fill=tk.X, expand=False)
        # 兼容旧代码中使用的fixed_top_frame名称
        self.fixed_top_frame = self.fixed_frame
        
        # 配置列权重，确保五列宽度协调
        self.fixed_frame.grid_columnconfigure(0, weight=0, minsize=143)
        self.fixed_frame.grid_columnconfigure(1, weight=1, minsize=200)
        # 动作提示词框体所在列，宽度缩小1/3
        self.fixed_frame.grid_columnconfigure(2, weight=0, minsize=133)
        self.fixed_frame.grid_columnconfigure(3, weight=1, minsize=200)
        # 图片参数(全局)框体所在列，宽度缩小2/7
        self.fixed_frame.grid_columnconfigure(4, weight=0, minsize=143)
        
        # 创建滚动区域
        # 3. 创建中间框架，填充固定顶部框架和水平滚动条之间的空间
        scroll_content = ttk.Frame(self.root)
        scroll_content.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # 4. 创建Canvas作为滚动容器
        self.canvas = tk.Canvas(scroll_content, borderwidth=0, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 5. 创建垂直滚动条
        self.scrollbar = ttk.Scrollbar(scroll_content, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        


        # 4. 配置Canvas和滚动条的双向关联
        # 配置Canvas的滚动条命令
        self.canvas.configure(yscrollcommand=self.scrollbar.set, xscrollcommand=self.hscrollbar.set)
        # 配置滚动条的command属性
        self.scrollbar.configure(command=self.canvas.yview)
        self.hscrollbar.configure(command=self.canvas.xview)
        
        # 5. 创建主框架，将其放在Canvas中
        self.main_frame = ttk.Frame(self.canvas, padding="10")
        
        # 4. 将主框架添加到Canvas的窗口中
        self.canvas.create_window((0, 0), window=self.main_frame, anchor=tk.NW, tags="main_window")
        
        # 5. 绑定主框架大小变化事件，更新Canvas滚动区域
        def update_scrollregion(event):
            # 更新Canvas滚动区域，包含所有内容
            # 使用Canvas的bbox方法获取正确的滚动区域
            bbox = self.canvas.bbox("all")
            if bbox:
                # 如果有内容，使用实际内容尺寸
                self.canvas.configure(scrollregion=bbox)
            else:
                # 初始设置一个较大的滚动区域，确保滚动条可见
                self.canvas.configure(scrollregion=(0, 0, 2000, 1000))
        
        self.main_frame.bind("<Configure>", update_scrollregion)
        
        # 6. 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            """处理垂直鼠标滚轮事件 - 对应上下滑动控件"""
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")  # 垂直滚动
        
        def _on_mouse_hwheel(event):
            """处理水平鼠标滚轮事件 - 对应左右滑动控件"""
            # 水平滚轮的delta值直接对应滚动方向
            # 去掉负号，确保水平滚轮对应水平滚动
            self.canvas.xview_scroll(int(event.delta/120), "units")  # 横向滚动
        
        # 为Canvas绑定鼠标滚轮事件
        # 垂直滚轮事件
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 尝试绑定水平滚轮事件
        try:
            self.canvas.bind_all("<MouseHWheel>", _on_mouse_hwheel)
        except Exception as e:
            # 如果不支持水平滚轮事件，继续使用Shift+滚轮方式作为备选
            def _on_mousewheel_with_shift(event):
                # 检测是否按住了Shift键，实现横向滚动
                shift_pressed = (event.state == 8)  # Shift键被按下
                if shift_pressed:
                    # 水平滚动：去掉负号，确保方向正确
                    self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")  # 横向滚动
                else:
                    # 垂直滚动：保持原有逻辑
                    self.canvas.xview_scroll(int(event.delta/120), "units")  # 垂直滚动
            
            # 替换原有的鼠标滚轮事件处理
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel_with_shift)
        
        # 7. 配置网格权重
        self.configure_grid_weights()
        
        # 创建菜单栏
        self.create_menu()
        
        # 8. 创建网格布局
        self.create_grid_layout()
        
        # 添加关闭窗口确认对话框
        self.root.protocol("WM_DELETE_WINDOW", self.confirm_exit)
        
        # 初始化生成状态相关属性
        self.generation_status = "none"
        self.generated_count = 0
        self.total_count = 0
        
        # 根据配置的语言设置刷新所有UI文本
        # 这确保程序启动时使用正确的语言显示
        if self.current_language != "zh_CN":
            print(f"检测到非中文语言设置: {self.current_language}，将刷新UI文本")
            self.root.after(500, self.refresh_all_ui_texts)
        
        # 根据配置自动打开ComfyUI API配置窗体
        if hasattr(self, "auto_open_comfyui_api") and self.auto_open_comfyui_api:
            self.root.after(0, self.config_comfyui_api)
    
    def select_api_json(self):
        """选择API文件并自动关联对应的INI文件，同时读取初始值"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        if file_path:
            self.workflow_path = file_path
            file_name = os.path.basename(file_path)
            
            # 更新当前API标签
            if hasattr(self, 'api_json_label'):
                self.api_json_label.configure(text=file_name)
            
            # 自动选择对应的INI文件
            ini_path = os.path.splitext(file_path)[0] + ".ini"
            if os.path.exists(ini_path):
                self.ini_path = ini_path
                ini_file_name = os.path.basename(ini_path)
                # 更新当前脚本标签
                if hasattr(self, 'api_ini_label'):
                    self.api_ini_label.configure(text=ini_file_name)
                
                # 从INI文件中读取初始值，使用支持重复section的解析器
                config = MultiConfigParser()
                config.read(ini_path, encoding='utf-8')
                
                # 1. 处理K采样步值 - 计算平均数
                k_sampler_values = []
                for i, section in enumerate(config.sections()):
                    # 处理带有下划线和数字后缀的section名称，如"K采样步值_3"
                    if section.startswith("K采样步值"):
                        # 从配置文件获取默认值
                        default_k_sampler_steps = self.config.get("ImageToImage_K_Generation", "default_k_sampler_steps", fallback="4")
                        param_value = config._section_data[i].get("参数值", default_k_sampler_steps)
                        try:
                            k_sampler_values.append(int(param_value))
                        except ValueError:
                            pass
                
                if k_sampler_values:
                    # 计算平均数，去除小数点
                    avg_steps = int(sum(k_sampler_values) / len(k_sampler_values))
                    print(f"K采样步值基准值: {avg_steps}")
                    # 将K采样器步数设为计算得到的平均值
                    if hasattr(self, 'global_k_sampler_steps'):
                        self.global_k_sampler_steps.set(str(avg_steps))
                
                # 2. 处理图片尺寸宽度 - 读取实际参数值
                for i, section in enumerate(config.sections()):
                    if section.startswith("图片尺寸宽度"):
                        # 从配置文件获取默认值
                        default_image_width = self.config.get("ImageToImage_K_Generation", "default_image_width", fallback="480")
                        param_value = config._section_data[i].get("参数值", default_image_width)
                        if hasattr(self, 'global_image_width'):
                            self.global_image_width.set(param_value)
                        break
                
                # 3. 处理图片尺寸高度 - 读取实际参数值
                for i, section in enumerate(config.sections()):
                    if section.startswith("图片尺寸高度"):
                        # 从配置文件获取默认值
                        default_image_height = self.config.get("ImageToImage_K_Generation", "default_image_height", fallback="832")
                        param_value = config._section_data[i].get("参数值", default_image_height)
                        if hasattr(self, 'global_image_height'):
                            self.global_image_height.set(param_value)
                        break
            else:
                # 当对应的INI文件不存在时，更新INI标签为"未找到对应INI文件"
                if hasattr(self, 'api_ini_label'):
                    self.api_ini_label.configure(text="未找到对应INI文件")
    
    def generate_image_thread(self, row_index):
        """生成图片的线程方法"""
        try:
            # 加载工作流
            with open(self.workflow_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
            
            # 读取INI配置文件，使用支持重复section的解析器
            config = MultiConfigParser()
            config.read(self.ini_path, encoding='utf-8')
            
            # 处理工作流数据
            workflow_nodes = workflow
            
            print("\n=== 开始处理工作流节点 ===")
            print(f"原始工作流节点数量: {len(workflow_nodes)}")
            
            # 获取当前行的参数
            image_path = self.image_paths[row_index] if row_index < len(self.image_paths) else ""
            # 根据提示词框体的存在状态决定是否加载英文提示词
            english_prompt = ""
            if hasattr(self, 'has_positive_prompt') and self.has_positive_prompt and row_index < len(self.english_texts):
                english_prompt = self.english_texts[row_index].get("1.0", tk.END).strip()
            
            # 根据负面提示词框体的存在状态决定是否加载负面英文提示词
            negative_english_prompt = ""
            if hasattr(self, 'has_negative_prompt') and self.has_negative_prompt and hasattr(self, 'negative_english_texts') and row_index < len(self.negative_english_texts):
                negative_english_prompt = self.negative_english_texts[row_index].get("1.0", tk.END).strip()
            # 从配置文件获取默认值
            default_k_sampler_steps = self.config.get("ImageToImage_K_Generation", "default_k_sampler_steps", fallback="4")
            default_image_width = self.config.get("ImageToImage_K_Generation", "default_image_width", fallback="480")
            default_image_height = self.config.get("ImageToImage_K_Generation", "default_image_height", fallback="832")
            
            k_sampler_steps = self.k_sampler_steps_list[row_index].get() if row_index < len(self.k_sampler_steps_list) else default_k_sampler_steps
            image_width = self.image_width_list[row_index].get() if row_index < len(self.image_width_list) else default_image_width
            image_height = self.image_height_list[row_index].get() if row_index < len(self.image_height_list) else default_image_height
            
            # 1. 处理图片载入
            print("\n1. 处理图片载入")
            # 查找所有[图片载入]相关的section
            for i, section in enumerate(config.sections()):
                if section.startswith("图片载入"):
                    print(f"   处理section: {section}")
                    # 解析数据节点路径，获取节点ID和参数键名
                    data_path = config._section_data[i].get("数据节点路径", "")
                    param_key = config._section_data[i].get("参数键名", "image")
                    print(f"   数据节点路径: {data_path}")
                    print(f"   参数键名: {param_key}")
                    
                    # 从data_path中提取节点ID，格式：data["97"]["inputs"]["image"]
                    if data_path.startswith('data["'):
                        # 提取节点ID，如"97"
                        node_id = data_path.split('"')[1]
                        print(f"   提取到节点ID: {node_id}")
                        if node_id in workflow_nodes:
                            print(f"   节点 {node_id} 存在于工作流中")
                            print(f"   修改前的值: {workflow_nodes[node_id]["inputs"][param_key]}")
                            workflow_nodes[node_id]["inputs"][param_key] = image_path
                            print(f"   修改后的值: {workflow_nodes[node_id]["inputs"][param_key]}")
                        else:
                            print(f"   警告: 节点 {node_id} 不存在于工作流中")
            
            # 2. 处理正向提示词
            print("\n2. 处理正向提示词")
            for i, section in enumerate(config.sections()):
                if section.startswith("正向提示词"):
                    print(f"   处理section: {section}")
                    data_path = config._section_data[i].get("数据节点路径", "")
                    param_key = config._section_data[i].get("参数键名", "text")
                    print(f"   数据节点路径: {data_path}")
                    print(f"   参数键名: {param_key}")
                    
                    if data_path.startswith('data["'):
                        # 提取节点ID，如"97"
                        node_id = data_path.split('"')[1]
                        print(f"   提取到节点ID: {node_id}")
                        if node_id in workflow_nodes:
                            print(f"   节点 {node_id} 存在于工作流中")
                            print(f"   修改前的值: {workflow_nodes[node_id]["inputs"][param_key]}")
                            workflow_nodes[node_id]["inputs"][param_key] = english_prompt
                            print(f"   修改后的值: {workflow_nodes[node_id]["inputs"][param_key]}")
                        else:
                            print(f"   警告: 节点 {node_id} 不存在于工作流中")
            
            # 3. 处理负面提示词
            print("\n3. 处理负面提示词")
            for i, section in enumerate(config.sections()):
                if section.startswith("负面提示词"):
                    print(f"   处理section: {section}")
                    data_path = config._section_data[i].get("数据节点路径", "")
                    param_key = config._section_data[i].get("参数键名", "text")
                    print(f"   数据节点路径: {data_path}")
                    print(f"   参数键名: {param_key}")
                    
                    if data_path.startswith('data["'):
                        # 提取节点ID，如"97"
                        node_id = data_path.split('"')[1]
                        print(f"   提取到节点ID: {node_id}")
                        if node_id in workflow_nodes:
                            print(f"   节点 {node_id} 存在于工作流中")
                            print(f"   修改前的值: {workflow_nodes[node_id]["inputs"][param_key]}")
                            if negative_english_prompt:
                                workflow_nodes[node_id]["inputs"][param_key] = negative_english_prompt
                                print(f"   修改后的值: {workflow_nodes[node_id]["inputs"][param_key]}")
                            else:
                                print(f"   跳过修改: 负面提示词为空")
                        else:
                            print(f"   警告: 节点 {node_id} 不存在于工作流中")
            
            # 4. 处理图片尺寸高度
            print("\n4. 处理图片尺寸高度")
            for i, section in enumerate(config.sections()):
                if section.startswith("图片尺寸高度"):
                    print(f"   处理section: {section}")
                    data_path = config._section_data[i].get("数据节点路径", "")
                    param_key = config._section_data[i].get("参数键名", "height")
                    print(f"   数据节点路径: {data_path}")
                    print(f"   参数键名: {param_key}")
                    
                    if data_path.startswith('data["'):
                        # 提取节点ID，如"97"
                        node_id = data_path.split('"')[1]
                        print(f"   提取到节点ID: {node_id}")
                        if node_id in workflow_nodes:
                            print(f"   节点 {node_id} 存在于工作流中")
                            print(f"   修改前的值: {workflow_nodes[node_id]["inputs"][param_key]}")
                            # 直接使用UI中的值
                            workflow_nodes[node_id]["inputs"][param_key] = int(image_height)
                            print(f"   修改后的值: {workflow_nodes[node_id]["inputs"][param_key]}")
                        else:
                            print(f"   警告: 节点 {node_id} 不存在于工作流中")
            
            # 5. 处理图片尺寸宽度
            print("\n5. 处理图片尺寸宽度")
            for i, section in enumerate(config.sections()):
                if section.startswith("图片尺寸宽度"):
                    print(f"   处理section: {section}")
                    data_path = config._section_data[i].get("数据节点路径", "")
                    param_key = config._section_data[i].get("参数键名", "width")
                    print(f"   数据节点路径: {data_path}")
                    print(f"   参数键名: {param_key}")
                    
                    if data_path.startswith('data["'):
                        # 提取节点ID，如"97"
                        node_id = data_path.split('"')[1]
                        print(f"   提取到节点ID: {node_id}")
                        if node_id in workflow_nodes:
                            print(f"   节点 {node_id} 存在于工作流中")
                            print(f"   修改前的值: {workflow_nodes[node_id]["inputs"][param_key]}")
                            # 直接使用UI中的值
                            workflow_nodes[node_id]["inputs"][param_key] = int(image_width)
                            print(f"   修改后的值: {workflow_nodes[node_id]["inputs"][param_key]}")
                        else:
                            print(f"   警告: 节点 {node_id} 不存在于工作流中")
            
            # 6. 处理K采样步值（支持多个section）
            print("\n6. 处理K采样步值")
            k_sampler_indices = [i for i, section in enumerate(config.sections()) if section.startswith("K采样步值")]
            print(f"   找到 {len(k_sampler_indices)} 个K采样步值section")
            
            # 直接使用UI中的值
            steps = int(k_sampler_steps)
            print(f"   使用K采样器步数: {steps}")
            
            for i in k_sampler_indices:
                section = config.sections()[i]
                print(f"   处理section: {section}")
                data_path = config._section_data[i].get("数据节点路径", "")
                param_key = config._section_data[i].get("参数键名", "steps")
                print(f"   数据节点路径: {data_path}")
                print(f"   参数键名: {param_key}")
                
                if data_path.startswith('data["'):
                    # 提取节点ID，如"97"
                    node_id = data_path.split('"')[1]
                    print(f"   提取到节点ID: {node_id}")
                    if node_id in workflow_nodes:
                        print(f"   节点 {node_id} 存在于工作流中")
                        # 只修改steps值，不更改start_at_step和end_at_step
                        original_steps = workflow_nodes[node_id]["inputs"].get("steps", 4)
                        print(f"   原始值 - steps: {original_steps}")
                        
                        # 只更新steps值，保留原有的start_at_step和end_at_step
                        workflow_nodes[node_id]["inputs"]["steps"] = steps
                        print(f"   修改后 - steps: {steps}")
                    else:
                        print(f"   警告: 节点 {node_id} 不存在于工作流中")
            
            print("\n=== 工作流节点处理完成 ===")
            
            # 输出调试信息
            print("\n=== 开始生成图片 ===")
            print(f"图片路径: {image_path}")
            print(f"正向提示词: {english_prompt}")
            print(f"负面提示词: {negative_english_prompt}")
            print(f"K采样器步数: {k_sampler_steps}")
            print(f"图片尺寸 - 宽: {image_width}, 高: {image_height}")
            print(f"API URL: {self.COMFYUI_URL}")
            
            # 发送API请求
            url = f"{self.COMFYUI_URL}/prompt"
            payload = {"prompt": workflow_nodes}
            
            print(f"\n=== 发送API请求 ===")
            print(f"请求URL: {url}")
            print(f"请求类型: POST")
            print(f"超时时间: {self.TIMEOUT}秒")
            print(f"payload包含的节点数量: {len(payload['prompt'])}")
            
            # 输出关键节点的配置，用于调试
            print("\n关键节点配置:")
            for node_id in ["98", "85", "86", "97"]:
                if node_id in workflow_nodes:
                    print(f"节点 {node_id}:")
                    print(f"  类型: {workflow_nodes[node_id]['class_type']}")
                    print(f"  输入参数: {workflow_nodes[node_id]['inputs']}")
            
            import requests
            try:
                print(f"\n正在发送API请求...")
                response = requests.post(url, json=payload, timeout=self.TIMEOUT)
                
                print(f"API响应状态码: {response.status_code}")
                print(f"响应头: {dict(response.headers)}")
                
                response_text = response.text
                print(f"响应内容: {response_text}")
                
                response.raise_for_status()
                
                # 处理响应
                result = response.json()
                print(f"\n解析后的响应: {result}")
                
                if "prompt_id" in result:
                    prompt_id = result["prompt_id"]
                    print(f"获取到prompt_id: {prompt_id}")
                else:
                    print("错误: 响应中没有prompt_id")
                    raise Exception("Invalid response: no prompt_id")
                    
                # 轮询结果
                output_files = []
                start_time = time.time()
                
                print(f"\n开始轮询结果，prompt_id: {prompt_id}")
                print(f"轮询超时时间: {self.TIMEOUT}秒")
                print("轮询间隔: 5秒")
                
                while time.time() - start_time < self.TIMEOUT:
                    elapsed_time = time.time() - start_time
                    print(f"\n第{int(elapsed_time/5) + 1}次轮询，已耗时: {int(elapsed_time)}秒")
                    
                    time.sleep(5)
                    status_url = f"{self.COMFYUI_URL}/history/{prompt_id}"
                    print(f"正在请求状态: {status_url}")
                    
                    status_response = requests.get(status_url, timeout=30)
                    status_response.raise_for_status()
                    
                    print(f"状态请求响应码: {status_response.status_code}")
                    
                    status_result = status_response.json()
                    if prompt_id in status_result:
                        print(f"prompt_id {prompt_id} 存在于响应中")
                        
                        if "outputs" in status_result[prompt_id]:
                            print("检测到输出结果，开始解析")
                            outputs = status_result[prompt_id]["outputs"]
                            print(f"输出节点数量: {len(outputs)}")
                            
                            # 优先使用配置的SaveImage节点ID
                            if hasattr(self, 'image_output_node_id') and self.image_output_node_id in outputs:
                                print(f"优先处理配置的SaveImage节点: {self.image_output_node_id}")
                                node_output = outputs[self.image_output_node_id]
                                if "images" in node_output:
                                    print(f"节点 {self.image_output_node_id} 包含图片输出，图片数量: {len(node_output['images'])}")
                                    for image_info in node_output["images"]:
                                        if image_info["type"] == "output":
                                            output_files.append(image_info["filename"])
                                            print(f"从优先节点添加输出文件: {image_info['filename']}")
                            
                            # 如果没有从优先节点获取到图片，回退到遍历所有节点
                            if not output_files:
                                print("未从优先节点获取到图片，开始遍历所有节点")
                                for node_id, node_output in outputs.items():
                                    print(f"处理节点: {node_id}")
                                    if "images" in node_output:
                                        print(f"节点 {node_id} 包含图片输出，图片数量: {len(node_output['images'])}")
                                        for image_info in node_output["images"]:
                                            if image_info["type"] == "output":
                                                output_files.append(image_info["filename"])
                                                print(f"添加输出文件: {image_info['filename']}")
                            
                            if output_files:
                                print(f"\n成功获取到输出文件列表: {output_files}")
                                break
                        else:
                            print("暂未检测到输出结果，继续轮询")
                    else:
                        print(f"prompt_id {prompt_id} 不存在于响应中，继续轮询")
                
                if output_files:
                    # 下载图片文件
                    image_path = os.path.join("image", output_files[0])
                    download_url = f"{self.COMFYUI_URL}/view?filename={output_files[0]}&type=output"
                    
                    print(f"\n开始下载图片文件")
                    print(f"下载URL: {download_url}")
                    print(f"保存路径: {image_path}")
                    
                    response = requests.get(download_url, timeout=30)
                    response.raise_for_status()
                    
                    print(f"文件下载成功，大小: {len(response.content)}字节")
                    
                    os.makedirs("image", exist_ok=True)
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"文件已保存到: {image_path}")
                    
                    # 更新界面显示
                    self.root.after(0, lambda: self.update_image_display(row_index, image_path))
                else:
                    print(f"\n轮询超时，未获取到输出文件")
                    self.root.after(0, lambda: self.update_image_display(row_index, "error", "图片生成失败: 未获取到输出文件"))
            except Exception as e:
                print(f"\n=== 生成图片失败 ===")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误信息: {str(e)}")
                print(f"错误详情: {traceback.format_exc()}")
                
                # 更新界面显示
                self.root.after(0, lambda: self.update_image_display(row_index, "error", f"生成图片失败: {e}"))
                
        except Exception as e:
            self.root.after(0, lambda: self.update_image_display(row_index, "error", f"生成图片失败: {e}"))
    
    def confirm_exit(self):
        """确认关闭窗口对话框"""
        # 创建自定义确认对话框
        exit_window = tk.Toplevel(self.root)
        exit_window.title(tr("确认关闭"))
        exit_window.geometry("300x200")
        exit_window.resizable(False, False)
        exit_window.transient(self.root)
        exit_window.grab_set()
        
        # 计算并设置对话框居中位置
        exit_window.update_idletasks()  # 确保获取正确的尺寸
        # 获取主窗口的位置和尺寸
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        # 获取对话框的尺寸
        dialog_width = exit_window.winfo_width()
        dialog_height = exit_window.winfo_height()
        # 计算居中位置
        x = root_x + (root_width - dialog_width) // 2
        y = root_y + (root_height - dialog_height) // 2
        # 设置对话框位置
        exit_window.geometry(f"+{x}+{y}")
        
        # 使用ttkbootstrap组件和样式
        main_frame = ttk.Frame(exit_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 提示信息
        message = ttk.Label(main_frame, text=tr("确定要关闭创作区域吗？"), font=("宋体", 12))
        message.pack(pady=20)
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        # 确定关闭按钮
        def on_confirm():
            exit_window.destroy()
            self.root.destroy()
        
        confirm_btn = ttk.Button(btn_frame, text=tr("确定关闭"), command=on_confirm, style="danger.TButton", width=10)
        confirm_btn.pack(side=tk.LEFT, padx=10)
        
        # 取消按钮
        cancel_btn = ttk.Button(btn_frame, text=tr("取消"), command=exit_window.destroy, style="secondary.TButton", width=10)
        cancel_btn.pack(side=tk.LEFT, padx=10)
    
    def create_menu(self):
        """创建菜单栏"""
        # 创建菜单栏
        menubar = tk.Menu(self.root)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label=tr("exit"), command=lambda: self.root.destroy())
        menubar.add_cascade(label=tr("文件"), menu=file_menu)
        
        # API设置菜单
        api_menu = tk.Menu(menubar, tearoff=0)
        api_menu.add_command(label="Ollama API", command=lambda: self.config_ollama_api())
        api_menu.add_command(label=tr("腾讯翻译 API"), command=lambda: self.config_translate_api())
        api_menu.add_command(label="ComfyUI API", command=lambda: self.config_comfyui_api())
        menubar.add_cascade(label=tr("API设置"), menu=api_menu)
        
        # 系统设置菜单
        menubar.add_command(label=tr("系统设置"), command=lambda: self.show_system_settings())
        
        # 语言(Language)菜单
        menubar.add_command(label="语言(Language)", command=lambda: self.show_language_settings())
        
        # 联系作者菜单
        menubar.add_command(label=tr("联系作者"), command=lambda: self.show_contact_author())
        
        # 设置菜单栏
        self.root.config(menu=menubar)
    
    def show_language_settings(self):
        """显示语言选择对话框"""
        # 创建语言选择对话框
        lang_window = tk.Toplevel(self.root)
        lang_window.title("语言(Language)")
        lang_window.geometry("350x200")
        lang_window.resizable(False, False)
        lang_window.transient(self.root)
        lang_window.grab_set()
        
        # 居中显示
        lang_window.update_idletasks()
        x = (lang_window.winfo_screenwidth() - 350) // 2
        y = (lang_window.winfo_screenheight() - 200) // 2
        lang_window.geometry(f"350x250+{x}+{y}")
        
        # 主框架
        main_frame = ttk.Frame(lang_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="选择语言 / Select Language", font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 获取当前语言设置
        current_lang_code = self.config.get("UI", "language", fallback="zh_CN")
        
        # 语言选择变量
        lang_var = tk.StringVar(value="Chinese" if current_lang_code == "zh_CN" else "English")
        
        # 语言选项框架
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=10)
        
        # Chinese 选项
        chinese_radio = ttk.Radiobutton(options_frame, text="Chinese (中文简体)", variable=lang_var, value="Chinese")
        chinese_radio.pack(anchor=tk.W, pady=5)
        
        # English 选项
        english_radio = ttk.Radiobutton(options_frame, text="English", variable=lang_var, value="English")
        english_radio.pack(anchor=tk.W, pady=5)
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(20, 0))
        
        def save_language():
            """保存语言设置"""
            selected_lang = lang_var.get()
            new_lang_code = "zh_CN" if selected_lang == "Chinese" else "en_US"
            
            # 更新配置
            if "UI" not in self.config:
                self.config["UI"] = {}
            self.config["UI"]["language"] = new_lang_code
            
            # 保存到setting.ini
            self.save_config()
            
            # 更新语言管理器
            LanguageManager.set_language(new_lang_code)
            
            # 刷新UI
            self.refresh_all_ui_texts()
            
            # 关闭窗口
            lang_window.destroy()
        
        def cancel():
            """取消"""
            lang_window.destroy()
        
        # 确定按钮
        ok_btn = ttk.Button(btn_frame, text="OK / 确定", command=save_language, width=12)
        ok_btn.pack(side=tk.LEFT, padx=10, expand=True)
        
        # 取消按钮
        cancel_btn = ttk.Button(btn_frame, text="Cancel / 取消", command=cancel, width=12)
        cancel_btn.pack(side=tk.LEFT, padx=10, expand=True)
    
    def show_contact_author(self):
        """显示联系作者信息"""
        # 导入联系作者信息
        from src.help.contact_author import CONTACT_INFO
        
        # 创建弹窗
        contact_window = tk.Toplevel(self.root)
        contact_window.title(tr("联系作者"))
        contact_window.geometry("400x300")
        contact_window.resizable(False, False)
        
        # 居中显示
        contact_window.update_idletasks()
        width = contact_window.winfo_width()
        height = contact_window.winfo_height()
        x = (self.root.winfo_width() // 2) - (width // 2) + self.root.winfo_x()
        y = (self.root.winfo_height() // 2) - (height // 2) + self.root.winfo_y()
        contact_window.geometry(f"+{x}+{y}")
        
        # 创建文本框显示信息
        text_widget = tk.Text(contact_window, wrap=tk.WORD, font=(".\华文中宋", 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 添加联系信息
        text_widget.insert(tk.END, f"{tr('技术交流:')}\n")
        text_widget.insert(tk.END, f"{tr('QQ群:')} {CONTACT_INFO['技术交流']['QQ群']}\n")
        text_widget.insert(tk.END, f"{tr('微信ID:')} {CONTACT_INFO['技术交流']['微信ID']}\n\n")
        
        text_widget.insert(tk.END, f"{tr('开源项目地址:')}\n")
        text_widget.insert(tk.END, f"GitHub [{CONTACT_INFO['开源项目地址']['GitHub']}]\n\n")
        
        text_widget.insert(tk.END, f"{tr('商务合作:')}\n")
        text_widget.insert(tk.END, f"{CONTACT_INFO['商务合作']}\n")
        
        # 设置文本框为只读
        text_widget.config(state=tk.DISABLED)
        
        # 添加关闭按钮
        close_btn = ttk.Button(contact_window, text=tr("关闭"), command=contact_window.destroy, style="primary.TButton")
        close_btn.pack(pady=10)
    
    def load_config(self):
        """读取配置文件，支持配置项的读取和默认值设置"""
        self.config = configparser.ConfigParser()
        
        # 读取配置文件
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding="utf-8")
        
        # 确保所有配置组存在
        required_sections = ["API", "Application", "UI", "ComfyUI", "System", "Ollama", "TencentTranslate", "ComfyUI_API", "ImageToImage_K_Generation", "textToImage_K_Generation"]
        for section in required_sections:
            if section not in self.config:
                self.config[section] = {}
        
        # 从配置文件加载API相关配置
        self.COMFYUI_URL = self.config.get("API", "base_url", fallback="http://127.0.0.1:8188").split()[0]
        self.TIMEOUT = int(self.config.get("API", "timeout", fallback="2700").split()[0])
        self.retry_count = int(self.config.get("API", "retry_count", fallback="3").split()[0])
        
        # 从配置文件加载ComfyUI相关配置
        # 优先读取[comfyui_gen]章节的workflow_path配置（用户期望使用的版本）
        workflow_path = self.config.get("comfyui_gen", "workflow_path", fallback="")
        # 直接使用完整路径，不进行split()，因为文件名可能包含空格
        self.WORKFLOW_PATH = workflow_path.strip()
        # 如果[comfyui_gen]章节没有配置或配置为空，回退到[ComfyUI]章节的配置
        if not self.WORKFLOW_PATH:
            comfyui_path = self.config.get("ComfyUI", "workflow_path", fallback="config\\API\\test_wan2.2-14B状态+生图_接口.json")
            # 直接使用完整路径，不进行split()
            self.WORKFLOW_PATH = comfyui_path.strip()
            if not self.WORKFLOW_PATH:
                self.WORKFLOW_PATH = "config\\API\\test_wan2.2-14B状态+生图_接口.json"
        
        # 初始化workflow_path和对应的ini_path实例变量
        self.workflow_path = self.WORKFLOW_PATH
        # 根据workflow_path自动生成对应的ini_path
        self.ini_path = os.path.splitext(self.workflow_path)[0] + ".ini"
        
        # 从配置文件加载Application相关配置
        # 将ImageOutput目录改为相对路径指向上级目录下的ImageOutput文件夹
        self.IMAGE_SAVE_DIR = "..\ImageOutput"
        # 将图片输出目录写入配置文件
        self.config["Application"]["default_save_path"] = self.IMAGE_SAVE_DIR
        self.log_level = self.config.get("Application", "log_level", fallback="INFO").split()[0]
        self.temp_cleanup = self.config.get("Application", "temp_cleanup", fallback="on_exit").split()[0]
        
        # 从配置文件加载System相关配置
        self.content_rows = int(self.config.get("System", "content_rows", fallback="30").split()[0])
        # 从配置文件读取项目文件展示目录，使用相对路径作为默认值
        self.project_dir = self.config.get("System", "project_dir", fallback="..\\Comfyui_API_Map\\图生图").split()[0]
        # 将项目目录写入配置文件
        self.config["System"]["project_dir"] = self.project_dir
        # 新增：控制ComfyUI API配置窗体是否一启动就打开或关闭
        self.auto_open_comfyui_api = int(self.config.get("System", "auto_open_comfyui_api", fallback="1").split()[0])
        # 将配置写入文件
        self.config["System"]["auto_open_comfyui_api"] = str(self.auto_open_comfyui_api)
        self.save_config()
        
        # 从配置文件加载UI相关配置
        self.ui_width = int(self.config.get("UI", "width", fallback="1100").split()[0])
        self.ui_height = int(self.config.get("UI", "height", fallback="1000").split()[0])
        self.ui_position_x = int(self.config.get("UI", "position_x", fallback="0").split()[0])
        self.ui_position_y = int(self.config.get("UI", "position_y", fallback="0").split()[0])
        
        # 主题配置处理：
        # 1. 检查是否有用户自定义主题（二次选择）
        custom_theme = self.config.get("UI", "custom_theme", fallback="")
        
        # 2. 检查是否有旧版主题配置
        old_theme = self.config.get("UI", "theme", fallback="")
        
        # 3. 确定最终使用的主题
        if custom_theme:
            # 如果有用户自定义主题，使用它
            self.ui_theme = custom_theme
        elif old_theme:
            # 如果有旧版主题配置，使用它
            self.ui_theme = old_theme
        else:
            # 第一次使用，默认使用cyborg主题
            self.ui_theme = "cyborg"
            # 保存到配置文件
            self.config["UI"]["custom_theme"] = self.ui_theme
            self.save_config()
        
        # 4. 保存主题到旧版配置项，确保兼容性
        self.config["UI"]["theme"] = self.ui_theme
        
        # 5. 添加特殊主题到配置中，用于文本框颜色控制
        special_themes = "darkly,superhero,cyborg,vapor,solar"
        self.config["UI"]["special_themes"] = special_themes
        self.save_config()
        
        self.ui_font_size = int(self.config.get("UI", "font_size", fallback="10"))
        
        # 从配置文件加载ComfyUI API目录配置
        self.api_dir = self.config.get("ComfyUI_API", "api_dir", fallback=r"..\Comfyui_API_Map\图生图").split()[0]
        # 从配置文件加载ComfyUI输出路径配置
        self.output_path = self.config.get("ComfyUI_API", "output_path", fallback="").split()[0]
        
        # 从配置文件加载Ollama相关配置
        self.ollama_url = self.config.get("ollama", "url", fallback="http://localhost:11434").split()[0]
        self.ollama_model = self.config.get("ollama", "model", fallback="llama3.2-vision:latest").split()[0]
        self.ollama_timeout = int(self.config.get("ollama", "timeout", fallback="10"))
        
        # 从配置文件加载腾讯翻译API相关配置
        self.tencent_appid = self.config.get("tencent_translate", "appid", fallback="").split(';')[0].strip()
        self.tencent_secret_id = self.config.get("tencent_translate", "secret_id", fallback="").split(';')[0].strip()
        self.tencent_secret_key = self.config.get("tencent_translate", "secret_key", fallback="").split(';')[0].strip()
        self.tencent_api_host = self.config.get("tencent_translate", "host", fallback="tmt.tencentcloudapi.com").split(';')[0].strip()
        self.tencent_api_action = self.config.get("tencent_translate", "action", fallback="TextTranslate").split(';')[0].strip()
        self.tencent_api_version = self.config.get("tencent_translate", "version", fallback="2018-03-21").split(';')[0].strip()
        self.tencent_api_region = self.config.get("tencent_translate", "region", fallback="ap-guangzhou").split(';')[0].strip()
        
        # 批量生成图片数范围（1-5）
        self.BATCH_RANGE = list(range(1, 6))
        
        # 从配置文件加载允许的索引名列表
        self.allowed_index_names = self.config.get("ImageToImage_K_Generation", "allowed_index_names", fallback="[图片载入],[正向提示词],[负面提示词],[K采样步值],[图片尺寸高度],[图片尺寸宽度],[图片输出]")
        # 解析allowed_index_names为列表
        self.allowed_index_names = [name.strip() for name in self.allowed_index_names.split(",")]
        print(f"允许的索引名列表: {self.allowed_index_names}")
        
        # 从配置文件加载语言设置
        self.current_language = self.config.get("UI", "language", fallback="zh_CN")
        # 初始化语言管理器
        LanguageManager.set_language(self.current_language)
    
    def save_config(self):
        """保存配置文件"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.config.write(f)
    
    def play_image(self, row_index, image_path):
        """打开生成的图片
        
        Args:
            row_index: 图片行索引
            image_path: 图片文件路径
        """
        # 使用系统默认程序打开图片
        import os
        try:
            if os.path.exists(image_path):
                # 在Windows系统上使用默认程序打开图片
                os.startfile(image_path)
                print(f"正在打开图片: {image_path}")
            else:
                print(f"图片文件不存在: {image_path}")
                self.root.after(0, lambda: messagebox.showerror("错误", f"图片文件不存在: {image_path}"))
        except Exception as e:
            error_msg = f"打开图片失败: {e}"
            print(error_msg)
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
    
    def delete_image(self, row_index):
        """删除图片显示，清空API接口返回的新图片框体内的已生成图片绑定显示关系"""
        try:
            # 获取API返回图片显示区域的框架
            # 遍历main_frame的所有子组件，找到对应的API图片框
            for child in self.main_frame.winfo_children():
                # 检查是否为API接口返回的新图片标签框架
                if isinstance(child, ttk.Labelframe) and child.cget("text") == "API接口返回的新图片":
                    # 获取内部框架
                    for inner_child in child.winfo_children():
                        if isinstance(inner_child, ttk.Frame):
                            # 清空原有内容
                            for widget in inner_child.winfo_children():
                                widget.pack_forget()
                            
                            # 恢复初始状态，显示"API返回图片显示区域"提示文字
                            api_prompt = ttk.Label(inner_child, text="API返回图片显示区域", justify=tk.CENTER)
                            api_prompt.pack(expand=True)
                            
                            print(f"已清空第{row_index}行的图片显示")
                            break
                    break
        except Exception as e:
            error_msg = f"删除图片显示失败: {e}"
            print(error_msg)
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
    
    def delete_all_images(self, row_index):
        """删除所有图片显示，清空API接口返回的新图片框体内的已生成图片绑定显示关系"""
        # 弹出确认对话框
        confirm_msg = tr("确定要批量删除此行的所有图片显示关系吗?此操作会清除程序的已生成图片的绑定显示关系，但不会删除png图片原文件。")
        confirm_result = messagebox.askyesno(tr("确认删除"), confirm_msg, parent=self.root)
        
        if confirm_result:
            try:
                # 检查是否有生成的图片
                if hasattr(self, "generated_images") and row_index < len(self.generated_images):
                    # 获取当前行的图片数量
                    image_count = len(self.generated_images[row_index])
                    
                    # 从后往前逐个删除图片，避免索引错位
                    for idx in range(image_count-1, -1, -1):
                        # 调用每个删除图标的点击事件
                        self.remove_single_image(row_index, idx)
                    
                    print(f"已批量删除第{row_index}行的所有图片显示")
            except Exception as e:
                error_msg = f"删除所有图片显示失败: {e}"
                print(error_msg)
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
    
    def update_window_title(self):
        """更新窗口标题"""
        app_title = tr("ComfyUI批量处理伴侣")
        self.root.title(app_title)
    
    def toggle_prompt_widgets(self):
        """根据配置隐藏/显示提示词相关控件"""
        # 1. 隐藏/显示正向提示词相关控件
        if not self.has_positive_prompt:
            # 隐藏正向提示词框体和按钮
            for frame in self.prompt_frames:
                frame.grid_remove()
            for frame in self.positive_buttons_frames:
                frame.grid_remove()
        else:
            # 显示正向提示词框体和按钮
            for i, frame in enumerate(self.prompt_frames):
                base_row = 2 + i * 2
                frame.grid(row=base_row, column=1, padx=3, pady=3, sticky=tk.NSEW)
            for i, frame in enumerate(self.positive_buttons_frames):
                base_row = 2 + i * 2
                frame.grid(row=base_row+1, column=1, padx=10, pady=5, sticky=tk.W)
        
        # 2. 隐藏/显示负面提示词相关控件
        if not self.has_negative_prompt:
            # 隐藏负面提示词框体和按钮
            for frame in self.negative_prompt_frames:
                frame.grid_remove()
            for frame in self.negative_buttons_frames:
                frame.grid_remove()
        else:
            # 显示负面提示词框体和按钮
            for i, frame in enumerate(self.negative_prompt_frames):
                base_row = 2 + i * 2
                frame.grid(row=base_row, column=2, padx=3, pady=3, sticky=tk.NSEW)
            for i, frame in enumerate(self.negative_buttons_frames):
                base_row = 2 + i * 2
                frame.grid(row=base_row+1, column=2, padx=10, pady=5, sticky=tk.W)
        
        # 3. 如果同时没有正向和负面提示词，隐藏整个动作提示词框体
        if hasattr(self, "top_frames_visible"):
            if not self.has_positive_prompt and not self.has_negative_prompt:
                self.top_frames_visible[self.prompt_frame] = False
                self.add_ui_log(self.prompt_frame, "文/图生图动作提示词: 已隐藏")
            else:
                self.top_frames_visible[self.prompt_frame] = True
                self.add_ui_log(self.prompt_frame, "文/图生图动作提示词: 已显示")
            # 调用动态布局方法
            self.layout_top_frames()

    def log_frame_visibility(self):
        """记录所有框架的可见性配置到日志"""
        try:
            # 导入必要的模块
            import configparser
            import os
            
            # 创建一个新的配置解析器，用于读取工作流对应的INI文件
            ini_config = configparser.ConfigParser()
            
            # 读取当前工作流对应的INI文件（如果存在）
            if hasattr(self, "ini_path") and os.path.exists(self.ini_path):
                try:
                    # 使用utf-8-sig编码处理带有BOM的文件
                    with open(self.ini_path, 'r', encoding='utf-8-sig') as f:
                        ini_config.read_file(f)
                except Exception as e:
                    print(f"警告: 无法读取工作流INI文件 '{self.ini_path}': {str(e)}")
            
            # 同时读取主配置文件，作为备用
            try:
                with open("setting.ini", 'r', encoding='utf-8-sig') as f:
                    ini_config.read_file(f)
            except Exception as e:
                print(f"警告: 无法读取主配置文件 'setting.ini': {str(e)}")
            
            # 根据当前工作流类型确定配置节
            workflow_type = self.config.get("ComfyUI", "workflow_path", fallback="图生图")
            
            # 默认配置节
            section = "FrameVisibility_ImageToImage"
            
            # 从配置文件中读取所有可用模式
            if self.config.has_section("FrameVisibility_Modes"):
                # 遍历所有模式，查找匹配当前工作流类型的模式
                for mode_config in self.config.items("FrameVisibility_Modes"):
                    mode_name = mode_config[0]
                    mode_info = mode_config[1]
                    
                    # 解析模式配置：section_name, workflow_identifier
                    mode_parts = mode_info.split(",")
                    if len(mode_parts) >= 2:
                        mode_section = mode_parts[0].strip()
                        workflow_identifier = mode_parts[1].strip()
                        
                        # 检查当前工作流类型是否匹配
                        if workflow_identifier in workflow_type:
                            section = mode_section
                            break
            
            # 定义需要检查的所有框架名称
            frame_names = [
                "self.current_workflow_frame",
                "self.img_frame",
                "self.prompt_frame",
                "self.image_gen_frame",
                "self.global_image_frame",
                "no_frame",
                "img_frame",
                "prompt_frame",
                "negative_prompt_frame",
                "api_frame",
                "image_params_right_frame",
                "positive_buttons_frame",
                "negative_buttons_frame",
                "gen_btn_frame"
            ]
            
            # 输出框架可见性日志
            print("\n=== 框架可见性配置日志 ===")
            print(f"当前工作流: {workflow_type}")
            print(f"配置节: {section}")
            print(f"工作流INI文件: {self.ini_path if hasattr(self, 'ini_path') else '未设置'}")
            
            for frame_name in frame_names:
                # 获取框架可见性
                visibility = ini_config.get(section, frame_name, fallback="Y")
                is_visible = visibility.upper() == "Y"
                print(f"{frame_name} = {visibility} → {'显示' if is_visible else '隐藏'}")
            
            print("====================\n")
            
        except Exception as e:
            print(f"记录框架可见性日志时出错: {str(e)}")
            import traceback
            traceback.print_exc()

    def save_project(self, selected_project=None, project_file=None, parent_window=None):
        """保存项目"""
        if not selected_project or not project_file:
            # 如果没有提供项目信息，打开项目选择窗口
            project_dir = self.config.get("System", "project_dir").split()[0]
            
            # 列出所有项目文件
            project_files = []
            if os.path.exists(project_dir):
                project_files = [f for f in os.listdir(project_dir) if f.endswith('.json')]
            
            if not project_files:
                self.custom_messagebox(self.root, "警告", "没有找到任何项目文件", msg_type="warning")
                return
            
            # 创建项目选择对话框
            from tkinter import simpledialog
            selected_project = simpledialog.askstring("选择项目", "请输入要保存的项目名称：", parent=self.root)
            
            if not selected_project:
                return
            
            if not selected_project.endswith('.json'):
                selected_project += '.json'
            
            if selected_project not in project_files:
                self.custom_messagebox(self.root, "错误", f"项目 '{selected_project}' 不存在", msg_type="error")
                return
            
            project_file = os.path.join(project_dir, selected_project)
            parent_window = self.root
        
        # 弹出确认保存窗口
        if self.custom_messagebox(parent_window, "确认保存", f"确定要保存到项目 '{selected_project}' 吗？", ask_yes_no=True):
            # 收集项目内容数据
            project_content = []
            
            # 获取行数
            num_rows = self.content_rows
            
            for row_index in range(num_rows):
                # 收集行数据
                row_data = {
                    "row_index": row_index,
                    "image_path": "",
                    "cn_prompt": "",
                    "en_prompt": "",
                    "image_generated": False,
                    "generated_images": [],
                    "image_params": {
                        "k_sampler_steps": "",
                        "image_height": "",
                        "image_width": "",
                        "image_orientation": ""
                    }
                }
                
                # 图片路径
                if hasattr(self, "image_paths") and row_index < len(self.image_paths):
                    row_data["image_path"] = self.image_paths[row_index] or ""
                
                # 中文提示词
                if hasattr(self, "prompt_texts") and row_index < len(self.prompt_texts):
                    cn_text = self.prompt_texts[row_index].get("1.0", tk.END).strip()
                    if cn_text != "中文提示词":
                        row_data["cn_prompt"] = cn_text
                
                # 英文提示词
                if hasattr(self, "english_texts") and row_index < len(self.english_texts):
                    en_text = self.english_texts[row_index].get("1.0", tk.END).strip()
                    if en_text != "英文翻译":
                        row_data["en_prompt"] = en_text
                
                # 生成的图片路径
                if hasattr(self, "generated_images") and row_index < len(self.generated_images):
                    row_data["generated_images"] = self.generated_images[row_index] or []
                    if row_data["generated_images"]:
                        row_data["image_generated"] = True
                
                # 图片参数
                if hasattr(self, "k_sampler_steps_list") and row_index < len(self.k_sampler_steps_list):
                    row_data["image_params"]["k_sampler_steps"] = self.k_sampler_steps_list[row_index].get()
                
                if hasattr(self, "image_height_list") and row_index < len(self.image_height_list):
                    row_data["image_params"]["image_height"] = self.image_height_list[row_index].get()
                
                if hasattr(self, "image_width_list") and row_index < len(self.image_width_list):
                    row_data["image_params"]["image_width"] = self.image_width_list[row_index].get()
                
                if hasattr(self, "image_orientation_list") and row_index < len(self.image_orientation_list):
                    row_data["image_params"]["image_orientation"] = self.image_orientation_list[row_index].get()
                
                project_content.append(row_data)
            
            project_data = {
                "version": "1.0",
                "config": {
                    "ollama": dict(self.config["Ollama"]),
                    "tencent_translate": dict(self.config["TencentTranslate"]),
                    "comfyui_status": dict(self.config["comfyui_status"]),
                    "comfyui_gen": dict(self.config["comfyui_gen"]),
                    "system": dict(self.config["System"])
                },
                "project_content": project_content,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "current_project": selected_project
            }
            
            try:
                with open(project_file, "w", encoding="utf-8") as f:
                    json.dump(project_data, f, indent=2, ensure_ascii=False)
                
                self.custom_messagebox(parent_window, "提示", "项目保存成功")
                # 更新文件状态为已保存
                self.current_filename = selected_project
                self.is_edited = False
                self.update_window_title()
                
                # 如果是从读取项目窗口调用的，刷新项目列表
                if parent_window and hasattr(parent_window, "title") and parent_window.title() == "读取项目":
                    # 查找项目列表并刷新
                    for widget in parent_window.winfo_children():
                        if hasattr(widget, "winfo_children"):
                            for child in widget.winfo_children():
                                if isinstance(child, tk.Frame):
                                    for grandchild in child.winfo_children():
                                        if isinstance(grandchild, ttk.Treeview):
                                            # 调用load_project_list函数
                                            for func in parent_window.__dict__.values():
                                                if callable(func) and func.__name__ == "load_project_list":
                                                    func()
                                                    break
            except Exception as e:
                self.custom_messagebox(parent_window, "错误", f"项目保存失败：{e}", msg_type="error")
    
    def custom_messagebox(self, parent, title, message, msg_type="info", ask_yes_no=False):
        """自定义消息框，居中显示在父窗口上
        
        Args:
            parent: 父窗口
            title: 消息框标题
            message: 消息内容
            msg_type: 消息类型，可选值：info, warning, error
            ask_yes_no: 是否显示是/否按钮，默认为False（只显示确定按钮）
        
        Returns:
            bool: 如果是ask_yes_no=True，返回用户选择（True为是，False为否）
        """
        msg_window = tk.Toplevel(parent)
        msg_window.title(title)
        
        # 根据消息类型设置不同的尺寸
        if msg_type == "error":
            msg_window.geometry("400x220")
        elif ask_yes_no:
            msg_window.geometry("400x220")
        else:
            msg_window.geometry("400x200")
        
        msg_window.resizable(False, False)
        
        # 设置对话框置顶
        msg_window.transient(parent)
        msg_window.grab_set()
        
        # 居中显示在父窗口上
        msg_window.update_idletasks()
        width = msg_window.winfo_width()
        height = msg_window.winfo_height()
        x = (parent.winfo_width() // 2) - (width // 2) + parent.winfo_x()
        y = (parent.winfo_height() // 2) - (height // 2) + parent.winfo_y()
        msg_window.geometry(f"+{x}+{y}")
        
        # 添加ESC键绑定
        msg_window.bind("<Escape>", lambda e: msg_window.destroy())
        
        # 主框架
        main_frame = ttk.Frame(msg_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 消息文本
        msg_label = ttk.Label(main_frame, text=message, wraplength=350, justify=tk.CENTER)
        
        # 根据消息类型设置不同的前景色
        if msg_type == "warning":
            msg_label.config(foreground="orange")
        elif msg_type == "error":
            msg_label.config(foreground="red")
        
        msg_label.pack(pady=20)
        
        result = tk.BooleanVar()
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        if ask_yes_no:
            # 是/否按钮
            def on_yes():
                result.set(True)
                msg_window.destroy()
            
            def on_no():
                result.set(False)
                msg_window.destroy()
            
            yes_btn = ttk.Button(btn_frame, text="是", command=on_yes)
            yes_btn.pack(side=tk.LEFT, padx=5)
            
            no_btn = ttk.Button(btn_frame, text="否", command=on_no)
            no_btn.pack(side=tk.LEFT, padx=5)
        else:
            # 确定按钮
            def on_ok():
                msg_window.destroy()
            
            ok_btn = ttk.Button(btn_frame, text="确定", command=on_ok)
            ok_btn.pack()
        
        # 等待窗口关闭
        msg_window.wait_window()
        
        return result.get() if ask_yes_no else None
    
    def save_project_from_menu(self):
        """从菜单调用的保存项目功能"""
        project_dir = self.config.get("System", "project_dir").split()[0]
        
        # 如果当前是未保存状态，弹出新建文件名提示框
        if self.current_filename == "未保存":
            from tkinter import simpledialog
            selected_project = simpledialog.askstring("新建项目", "请输入新的项目名称：", parent=self.root)
            
            if not selected_project:
                return
            
            if not selected_project.endswith('.json'):
                selected_project += '.json'
            
            project_file = os.path.join(project_dir, selected_project)
            
            # 检查文件名是否已存在
            if os.path.exists(project_file):
                if not self.custom_messagebox(self.root, "确认覆盖", f"项目 '{selected_project}' 已存在，是否覆盖？", ask_yes_no=True):
                    return
            
            # 保存项目
            self.save_project(selected_project, project_file, self.root)
        else:
            # 已有文件名，执行正常保存流程
            self.save_project(self.current_filename, os.path.join(project_dir, self.current_filename), self.root)
    
    def set_textbox_color(self, text_widget, placeholder):
        """设置单个文本框的颜色，确保它跟随主题
        
        Args:
            text_widget: 要设置颜色的文本框
            placeholder: 该文本框的占位符文本
        """
        # 获取当前文本
        current_text = text_widget.get("1.0", tk.END).strip()
        
        # 如果是占位符文本，使用灰色字体
        if current_text == placeholder:
            text_widget.config(fg="gray")
        else:
            try:
                # 特定主题下使用白色字体
                special_themes_str = self.config.get("UI", "special_themes", fallback="darkly,superhero,cyborg,vapor,solar")
                special_themes = [theme.strip() for theme in special_themes_str.split(",")]
                if self.style.theme_use() in special_themes:
                    text_widget.config(fg="#ffffff")
                else:
                    text_widget.config(fg="black")
            except:
                # 如果出错，默认使用黑色
                text_widget.config(fg="black")
    
    def refresh_all_components(self):
        """刷新所有组件，确保主题切换后所有UI元素都能正确更新
        
        递归遍历所有组件，强制刷新它们的样式
        """
        def refresh_widget(widget):
            # 刷新当前组件
            widget.update()
            widget.update_idletasks()
            
            # 递归刷新所有子组件
            for child in widget.winfo_children():
                refresh_widget(child)
        
        # 从根组件开始刷新
        refresh_widget(self.root)
        
        # 更新所有文本框的颜色，确保它们跟随主题
        # 处理中文提示词文本框
        if hasattr(self, "prompt_texts"):
            for text_widget in self.prompt_texts:
                # 先重置修改标志，避免后续操作触发编辑状态
                text_widget.edit_modified(False)
                self.set_textbox_color(text_widget, "中文提示词")
        
        # 处理英文翻译文本框
        if hasattr(self, "english_texts"):
            for text_widget in self.english_texts:
                # 先重置修改标志，避免后续操作触发编辑状态
                text_widget.edit_modified(False)
                self.set_textbox_color(text_widget, "英文翻译")
        
        # 处理中文负面提示词文本框
        if hasattr(self, "negative_prompt_texts"):
            for text_widget in self.negative_prompt_texts:
                # 先重置修改标志，避免后续操作触发编辑状态
                text_widget.edit_modified(False)
                self.set_textbox_color(text_widget, "中文负面提示词")
        
        # 处理英文负面翻译文本框
        if hasattr(self, "negative_english_texts"):
            for text_widget in self.negative_english_texts:
                # 先重置修改标志，避免后续操作触发编辑状态
                text_widget.edit_modified(False)
                self.set_textbox_color(text_widget, "英文负面翻译")
    
    def reload_binding_options(self):
        """重新加载变量绑定选项（根据当前语言）
        
        在语言切换时调用，从setting.ini重新读取对应语言的绑定选项
        注意：此方法用于CreativeArea类，与JsonToIniDebugWindow类中的同名方法功能类似
        """
        # CreativeArea类不直接管理变量绑定下拉菜单，此方法为占位符
        # 实际的变量绑定选项在JsonToIniDebugWindow窗口中管理
        pass
    
    def _update_prompt_placeholders(self):
        """更新提示词文本框的占位符文本
        
        在语言切换时调用，将占位符文本更新为当前语言
        """
        # 定义占位符映射（旧文本 -> 新文本）
        placeholder_map = {
            "中文提示词": tr("中文提示词"),
            "Chinese Prompt": tr("中文提示词"),
            "英文翻译": tr("英文翻译"),
            "English Translation": tr("英文翻译"),
            "中文负面提示词": tr("中文负面提示词"),
            "Chinese Negative": tr("中文负面提示词"),
            "英文负面翻译": tr("英文负面翻译"),
            "English Negative": tr("英文负面翻译"),
        }
        
        # 更新中文提示词文本框
        if hasattr(self, "prompt_texts"):
            for text_widget in self.prompt_texts:
                current_text = text_widget.get("1.0", tk.END).strip()
                if current_text in placeholder_map:
                    text_widget.delete("1.0", tk.END)
                    text_widget.insert("1.0", placeholder_map[current_text])
                    text_widget.config(fg="gray")
        
        # 更新英文翻译文本框
        if hasattr(self, "english_texts"):
            for text_widget in self.english_texts:
                current_text = text_widget.get("1.0", tk.END).strip()
                if current_text in placeholder_map:
                    text_widget.delete("1.0", tk.END)
                    text_widget.insert("1.0", placeholder_map[current_text])
                    text_widget.config(fg="gray")
        
        # 更新中文负面提示词文本框
        if hasattr(self, "negative_prompt_texts"):
            for text_widget in self.negative_prompt_texts:
                current_text = text_widget.get("1.0", tk.END).strip()
                if current_text in placeholder_map:
                    text_widget.delete("1.0", tk.END)
                    text_widget.insert("1.0", placeholder_map[current_text])
                    text_widget.config(fg="gray")
        
        # 更新英文负面翻译文本框
        if hasattr(self, "negative_english_texts"):
            for text_widget in self.negative_english_texts:
                current_text = text_widget.get("1.0", tk.END).strip()
                if current_text in placeholder_map:
                    text_widget.delete("1.0", tk.END)
                    text_widget.insert("1.0", placeholder_map[current_text])
                    text_widget.config(fg="gray")
    
    def refresh_all_ui_texts(self):
        """刷新所有UI文本，实现语言切换
        
        遍历所有UI组件，更新它们的文本为当前语言
        """
        # 更新窗口标题
        self.update_window_title()
        
        # 更新菜单栏
        self.update_menu_texts()
        
        # 更新顶部框体标题
        if hasattr(self, 'current_workflow_frame'):
            self.current_workflow_frame.configure(text=tr("当前工作流"))
        if hasattr(self, 'img_frame'):
            self.img_frame.configure(text=tr("图片"))
        if hasattr(self, 'prompt_frame'):
            self.prompt_frame.configure(text=tr("动作提示词"))
        if hasattr(self, 'image_gen_frame'):
            self.image_gen_frame.configure(text=tr("批量生成新资源"))
        if hasattr(self, 'global_image_frame'):
            self.global_image_frame.configure(text=tr("图片参数(全局)"))
        
        # 更新内容行图片框体标题 (图A1, 图A2, ... -> ImgA1, ImgA2, ...)
        if hasattr(self, 'content_img_frames'):
            for i, img_frame in enumerate(self.content_img_frames):
                img_frame.configure(text=f"{tr('图A')}{i+1}")
        
        # 更新API状态标签
        if hasattr(self, 'api_status_var'):
            current_status = self.api_status_var.get()
            if "未测试" in current_status or "Not Tested" in current_status:
                self.api_status_var.set(tr("状态: 未测试"))
            elif "测试中" in current_status or "Testing" in current_status:
                self.api_status_var.set(tr("状态: 测试中..."))
            elif "正常" in current_status or "OK" in current_status:
                self.api_status_var.set(tr("状态: 正常"))
            elif "异常" in current_status or "Error" in current_status:
                self.api_status_var.set(tr("状态: 异常"))
        
        # 重新加载变量绑定选项（根据当前语言）
        self.reload_binding_options()
        
        # 更新提示词文本框的占位符文本
        self._update_prompt_placeholders()
        
        # 递归更新所有按钮和标签的文本
        self._update_widget_texts(self.root)
        
        # 强制刷新界面
        self.root.update()
        self.root.update_idletasks()
    
    def _update_widget_texts(self, widget):
        """递归更新组件文本
        
        Args:
            widget: 要更新的组件
        """
        # 定义需要翻译的文本映射
        text_map = {
            # 按钮文本
            "测试API": tr("测试API"),
            "Test API": tr("测试API"),
            "更换API": tr("更换API"),
            "Change API": tr("更换API"),
            "批量导入图片": tr("批量导入图片"),
            "Batch Import": tr("批量导入图片"),
            "批量删除图片": tr("批量删除图片"),
            "Batch Delete": tr("批量删除图片"),
            "批量删除出图": tr("批量删除出图"),
            "Delete Output": tr("批量删除出图"),
            "批量导出图片": tr("批量导出图片"),
            "Batch Export": tr("批量导出图片"),
            "Tencent批量翻译": tr("Tencent批量翻译"),
            "Tencent Batch Trans": tr("Tencent批量翻译"),
            "Ollama批量翻译": tr("Ollama批量翻译"),
            "Ollama Batch Trans": tr("Ollama批量翻译"),
            "批量直译": tr("批量直译"),
            "Batch Copy": tr("批量直译"),
            "停止翻译": tr("停止翻译"),
            "Stop Translation": tr("停止翻译"),
            "批量同步": tr("批量同步"),
            "Sync All": tr("批量同步"),
            "腾讯翻译(正向)": tr("腾讯翻译(正向)"),
            "Tencent Trans(+)": tr("腾讯翻译(正向)"),
            "Ollama翻译(正向)": tr("Ollama翻译(正向)"),
            "Ollama Trans(+)": tr("Ollama翻译(正向)"),
            "删除提示词(正向)": tr("删除提示词(正向)"),
            "Delete Prompt(+)": tr("删除提示词(正向)"),
            "腾讯翻译(负面)": tr("腾讯翻译(负面)"),
            "Tencent Trans(-)": tr("腾讯翻译(负面)"),
            "Ollama翻译(负面)": tr("Ollama翻译(负面)"),
            "Ollama Trans(-)": tr("Ollama翻译(负面)"),
            "删除提示词(负面)": tr("删除提示词(负面)"),
            "Delete Prompt(-)": tr("删除提示词(负面)"),
            "生成图片(单个)": tr("生成图片(单个)"),
            "Generate (Single)": tr("生成图片(单个)"),
            "删除所有图片": tr("删除所有图片"),
            "Delete All Images": tr("删除所有图片"),
            "批量生成": tr("批量生成"),
            "Batch Generate": tr("批量生成"),
            # 标签文本
            "K采样器步数:": tr("K采样器步数:"),
            "K Sampler Steps:": tr("K采样器步数:"),
            "图片尺寸:": tr("图片尺寸:"),
            "Image Size:": tr("图片尺寸:"),
            "高": tr("高"),
            "H": tr("高"),
            "宽": tr("宽"),
            "W": tr("宽"),
            "竖屏": tr("竖屏"),
            "Portrait": tr("竖屏"),
            "横屏": tr("横屏"),
            "Landscape": tr("横屏"),
            "* 重复生成次数": tr("* 重复生成次数"),
            "* Repeat Count": tr("* 重复生成次数"),
            "选择项目": tr("选择项目"),
            "Select Item": tr("选择项目"),
            "拖入图片或点击导入": tr("拖入图片或点击导入"),
            "Drop or Click to Import": tr("拖入图片或点击导入"),
            "将多张图片拖入此区域，按升序分配到每行图片框": tr("将多张图片拖入此区域，按升序分配到每行图片框"),
            "Drag images here to assign to each row in order": tr("将多张图片拖入此区域，按升序分配到每行图片框"),
            "API返回图片显示区域": tr("API返回图片显示区域"),
            "API Output Display Area": tr("API返回图片显示区域"),
            # 全选和批量生成
            "全选": tr("全选"),
            "Select All": tr("全选"),
            "全选项目": tr("全选项目"),
            "批量生成图片": tr("批量生成图片"),
            "Batch Generate Images": tr("批量生成图片"),
            # 计时器
            "生成时间:": tr("生成时间:"),
            "Generation Time:": tr("生成时间:"),
            "总计时:": tr("总计时:"),
            "Total:": tr("总计时:"),
            # 提示词占位符文本
            "中文提示词": tr("中文提示词"),
            "Chinese Prompt": tr("中文提示词"),
            "英文翻译": tr("英文翻译"),
            "English Translation": tr("英文翻译"),
            "中文负面提示词": tr("中文负面提示词"),
            "Chinese Negative": tr("中文负面提示词"),
            "英文负面翻译": tr("英文负面翻译"),
            "English Negative": tr("英文负面翻译"),
        }
        
        # 更新当前组件的文本
        try:
            if isinstance(widget, (ttk.Button, tk.Button)):
                current_text = widget.cget("text")
                if current_text in text_map:
                    widget.configure(text=text_map[current_text])
            elif isinstance(widget, (ttk.Label, tk.Label)):
                current_text = widget.cget("text")
                if current_text in text_map:
                    widget.configure(text=text_map[current_text])
            elif isinstance(widget, ttk.Radiobutton):
                current_text = widget.cget("text")
                if current_text in text_map:
                    widget.configure(text=text_map[current_text])
            elif isinstance(widget, (ttk.Checkbutton, tk.Checkbutton)):
                current_text = widget.cget("text")
                if current_text in text_map:
                    widget.configure(text=text_map[current_text])
            elif isinstance(widget, ttk.Labelframe):
                current_text = widget.cget("text")
                # 处理带状态的Labelframe标题
                for key in text_map:
                    if key in current_text:
                        new_text = current_text.replace(key, text_map[key])
                        widget.configure(text=new_text)
                        break
                # 处理正向/负面提示词框体
                if "正向提示词" in current_text or "Positive Prompt" in current_text:
                    status_part = current_text.split("(")[-1].rstrip(")") if "(" in current_text else ""
                    new_title = tr("正向提示词")
                    if status_part:
                        new_title = f"{new_title} ({status_part})"
                    widget.configure(text=new_title)
                elif "负面提示词" in current_text or "Negative Prompt" in current_text:
                    status_part = current_text.split("(")[-1].rstrip(")") if "(" in current_text else ""
                    new_title = tr("负面提示词")
                    if status_part:
                        new_title = f"{new_title} ({status_part})"
                    widget.configure(text=new_title)
                elif "图片参数" in current_text or "Image Params" in current_text:
                    widget.configure(text=tr("图片参数"))
                elif "批量拖入图片区域" in current_text or "Drag & Drop Area" in current_text:
                    widget.configure(text=tr("批量拖入图片区域"))
                elif "API接口返回的新图片" in current_text or "API Output Image" in current_text:
                    status_part = current_text.split("(")[-1].rstrip(")") if "(" in current_text else "none"
                    widget.configure(text=f"{tr('API返回图片')} ({status_part})")
        except Exception:
            pass
        
        # 递归处理子组件
        for child in widget.winfo_children():
            self._update_widget_texts(child)
    
    def update_menu_texts(self):
        """更新菜单栏文本"""
        # 重新创建菜单栏以更新语言
        self.create_menu()
    
    def create_grid_layout(self):
        """创建网格布局"""
        # 创建顶部标题行
        self.create_top_row()
        
        # 创建批量翻译行
        self.create_batch_translate_row()
        
        # 从配置文件获取行数，如果存在且有效则使用，否则使用默认值6
        config_rows = self.config.get("System", "content_rows", fallback="6")
        content_rows = int(config_rows) if config_rows.isdigit() and int(config_rows) > 0 else 6
        
        # 创建内容行
        for i in range(content_rows):
            self.create_content_row(i)
        
        # 设置所有中文负面提示词
        self.set_all_negative_prompts()
        
        # 记录初始框架可见性配置到日志
        self.log_frame_visibility()
        
    def set_all_negative_prompts(self):
        """从JSON文件加载负面提示词并设置到所有中文负面提示词文本框中"""
        import json
        import os
        import configparser
        
        # 使用配置文件中定义的JSON路径
        json_path = self.WORKFLOW_PATH
        if os.path.exists(json_path):
            try:
                # 生成对应的INI文件路径
                ini_path = os.path.splitext(json_path)[0] + ".ini"
                negative_prompt_node = "89"  # 默认节点ID
                negative_prompt_param = "text"  # 默认参数名
                
                # 读取INI文件获取节点配置和其他参数
                if os.path.exists(ini_path):
                    # 使用MultiConfigParser处理重复section
                    config = MultiConfigParser()
                    config.read(ini_path, encoding='utf-8')
                    # 查找功能模块与节点位置关联section
                    for i, section in enumerate(config.sections()):
                        if section == '功能模块与节点位置关联':
                            negative_prompt_node = config._section_data[i].get('cn_negative_prompt_node', '89')
                            negative_prompt_param = config._section_data[i].get('cn_negative_prompt_param', 'text')
                        elif section == 'K采样步值':
                            # 提取参数值
                            k_sampler_steps = config._section_data[i].get('参数值', '')
                            # 更新全局和所有行的K采样器步数
                            if k_sampler_steps:
                                if hasattr(self, 'global_k_sampler_steps'):
                                    self.global_k_sampler_steps.set(k_sampler_steps)
                                if hasattr(self, 'k_sampler_steps_list'):
                                    for var in self.k_sampler_steps_list:
                                        var.set(k_sampler_steps)
                        elif section == '图片尺寸宽度':
                            # 提取参数值
                            image_width = config._section_data[i].get('参数值', '')
                            # 更新全局和所有行的图片尺寸宽度
                            if image_width:
                                if hasattr(self, 'global_image_width'):
                                    self.global_image_width.set(image_width)
                                if hasattr(self, 'image_width_list'):
                                    for var in self.image_width_list:
                                        var.set(image_width)
                        elif section == '图片尺寸高度':
                            # 提取参数值
                            image_height = config._section_data[i].get('参数值', '')
                            # 更新全局和所有行的图片尺寸高度
                            if image_height:
                                if hasattr(self, 'global_image_height'):
                                    self.global_image_height.set(image_height)
                                if hasattr(self, 'image_height_list'):
                                    for var in self.image_height_list:
                                        var.set(image_height)
                
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if negative_prompt_node in data and "inputs" in data[negative_prompt_node] and negative_prompt_param in data[negative_prompt_node]["inputs"]:
                        negative_prompt = data[negative_prompt_node]["inputs"][negative_prompt_param]
                        # 确保不包含"中文负面提示词"前缀
                        if negative_prompt.startswith("中文负面提示词"):
                            negative_prompt = negative_prompt[len("中文负面提示词"):].strip()
                        # 设置所有中文负面提示词文本框的内容
                        for text_box in self.negative_prompt_texts:
                            text_box.delete("1.0", tk.END)
                            text_box.insert("1.0", negative_prompt)
                            # 更新文本框颜色为正常文本颜色
                            self.set_textbox_color(text_box, "中文负面提示词")
            except Exception as e:
                import traceback
                traceback.print_exc()
    
    def show_tooltip(self, event):
        """显示提示窗口"""
        # 先隐藏可能存在的旧提示窗口
        self.hide_tooltip(event)
        
        # 创建新的提示窗口
        self.tooltip = tk.Toplevel(self.root)
        # 设置为临时窗口，无标题栏和边框
        self.tooltip.wm_overrideredirect(True)
        # 设置背景色和前景色
        self.tooltip.configure(background="#ffffcc", borderwidth=1, relief="solid")
        
        # 创建提示文本标签
        tooltip_label = ttk.Label(self.tooltip, text="数值越大,图质量越好, 耗时更多", 
                                 foreground="#FFFF00", 
                                 font=('宋体', 9),
                                 padding=(5, 3))
        tooltip_label.pack()
        
        # 计算提示窗口位置 - 使用屏幕坐标
        x = event.widget.winfo_rootx() + event.widget.winfo_width() + 5
        y = event.widget.winfo_rooty()
        
        # 显示提示窗口
        self.tooltip.geometry(f"+{x}+{y}")
        self.tooltip.lift()  # 确保显示在最前面
    
    def hide_tooltip(self, event=None):
        """隐藏提示窗口"""
        if self.tooltip and self.tooltip.winfo_exists():
            self.tooltip.destroy()
            self.tooltip = None
    
    def add_ui_log(self, frame, message):
        """添加UI操作日志
        
        Args:
            frame: 操作的窗体对象
            message: 日志消息内容
        """
        print(f"UI日志: {message}")
    
    def layout_top_frames(self):
        """动态布局顶部框体
        
        如果某个框体隐藏了，后边的框体用向左对齐的方式，进行位置自动填补
        """
        # 先将所有框体从网格中移除
        for frame in self.top_frames:
            frame.grid_forget()
        
        # 遍历所有框体，根据可见状态重新布局
        current_column = 0
        for frame in self.top_frames:
            # 检查框体是否可见
            if self.top_frames_visible[frame]:
                # 框体可见，添加到当前列
                frame.grid(row=0, column=current_column, padx=5, pady=5, sticky=tk.NSEW)
                current_column += 1
        
        # 清除所有旧的列配置
        for col in range(5):
            try:
                self.fixed_frame.grid_columnconfigure(col, weight=0)
            except Exception:
                pass
        
        # 根据实际可见的框体数量重新配置列权重
        for col in range(current_column):
            # 为每一列设置相同的权重，确保宽度协调
            self.fixed_frame.grid_columnconfigure(col, weight=1, minsize=100)
    
    def create_top_row(self):
        """创建顶部标题行"""
        # 当前工作流框体 - 放在图片框体左边
        self.current_workflow_frame = ttk.Labelframe(self.fixed_frame, text=tr("当前工作流"), width=107)
        self.current_workflow_frame.grid_propagate(False)
        
        # 当前工作流文件名显示
        # 从配置文件中获取工作流文件名
        workflow_filename = os.path.basename(self.WORKFLOW_PATH)
        self.workflow_file_label = ttk.Label(self.current_workflow_frame, text=workflow_filename, anchor='w', wraplength=180, justify='left')
        self.workflow_file_label.pack(padx=5, pady=5, fill='x', expand=True)
        
        # 测试API按钮框架 - 包含按钮和状态显示
        test_btn_frame = ttk.Frame(self.current_workflow_frame)
        test_btn_frame.pack(padx=5, pady=2, fill='x')
        
        # 测试API按钮
        def test_api():            
            print("测试API按钮被点击")
            self.check_api_status()
        
        test_api_btn = ttk.Button(test_btn_frame, text=tr("测试API"), command=test_api, width=12)
        test_api_btn.pack(side=tk.LEFT, padx=0)
        
        # API状态显示标签 - 放在测试API按钮右侧
        self.api_status_var = tk.StringVar(value=tr("状态: 未测试"))
        self.api_status_label = ttk.Label(test_btn_frame, textvariable=self.api_status_var, font=('宋体', 9, 'bold'), foreground='#666666')
        self.api_status_label.pack(side=tk.LEFT, padx=10, fill='x', expand=True)
        
        # 更新API按钮
        update_api_btn = ttk.Button(self.current_workflow_frame, text=tr("更换API"), command=self.config_comfyui_api, width=12)
        update_api_btn.pack(padx=5, pady=2, anchor='w')
        
        # 显示索引
        self.ini_sections_var = tk.StringVar(value=tr("索引- 未加载"))
        ini_sections_label = ttk.Label(self.current_workflow_frame, textvariable=self.ini_sections_var, font=('宋体', 6), foreground='#FFFFFF', wraplength=200, justify=LEFT)
        ini_sections_label.pack(padx=5, pady=2, anchor='w')
        
        # 更新索引
        def update_ini_sections(sections):
            """更新索引显示"""
            if sections:
                # 格式化sections为字符串
                sections_str = ",".join([f"[{section}]" for section in sections])
                self.ini_sections_var.set(f"索引: {sections_str}")
            else:
                self.ini_sections_var.set("索引: 未找到有效索引")
        
        # 左侧图片区域 - LabelFrame
        self.img_frame = ttk.Labelframe(self.fixed_frame, text=tr("图片"))
        
        # 批量操作按钮框架
        batch_btn_frame = ttk.Frame(self.img_frame)
        batch_btn_frame.pack(padx=5, pady=5, fill=tk.X)
        
        # 批量导入图片按钮
        batch_import_btn = ttk.Button(batch_btn_frame, text=tr("批量导入图片"), command=self.batch_import_images, width=12)
        batch_import_btn.pack(side=tk.LEFT, padx=1)
        
        # 批量删除图片按钮
        batch_delete_btn = ttk.Button(batch_btn_frame, text=tr("批量删除图片"), command=self.batch_delete_images, width=12)
        batch_delete_btn.pack(side=tk.LEFT, padx=1)
        
        # 批量删除出图按钮
        batch_delete_video_btn = ttk.Button(batch_btn_frame, text=tr("批量删除出图"), command=self.batch_delete_videos, width=12)
        batch_delete_video_btn.pack(side=tk.LEFT, padx=1)
        
        # 批量导出图片按钮
        batch_export_btn = ttk.Button(batch_btn_frame, text=tr("批量导出图片"), command=self.batch_export_images, width=12)
        batch_export_btn.pack(side=tk.LEFT, padx=1)
        
        # 批量图片拖入区域
        drag_drop_frame = ttk.Labelframe(self.img_frame, text=tr("批量拖入图片区域"))
        drag_drop_frame.pack(padx=5, pady=5, fill=tk.X)
        
        # 拖入提示
        drag_drop_prompt = ttk.Label(drag_drop_frame, text=tr("将多张图片拖入此区域，按升序分配到每行图片框"), justify=tk.CENTER)
        drag_drop_prompt.pack(padx=10, pady=20, expand=True)
        
        # 绑定拖入事件
        drag_drop_frame.drop_target_register(DND_FILES)
        drag_drop_frame.dnd_bind("<<Drop>>", self.handle_batch_drop)
        
        # 中间动作提示词区域 - LabelFrame
        self.prompt_frame = ttk.Labelframe(self.fixed_frame, text=tr("动作提示词"))
        
        # 右侧批量生成新资源区域 - LabelFrame
        self.image_gen_frame = ttk.Labelframe(self.fixed_frame, text=tr("批量生成新资源"))
        
        # 全局图片参数设置也放在固定框架中
        # 初始化全局图片参数变量（无论global_video_frame是否存在）
        if not hasattr(self, "global_k_sampler_steps") or self.global_k_sampler_steps is None:
            self.global_k_sampler_steps = tk.StringVar(value="4")
        if not hasattr(self, "global_image_height") or self.global_image_height is None:
            self.global_image_height = tk.StringVar(value="832")
        if not hasattr(self, "global_image_width") or self.global_image_width is None:
            self.global_image_width = tk.StringVar(value="480")
        if not hasattr(self, "global_orientation") or self.global_orientation is None:
            self.global_orientation = tk.StringVar(value="portrait")
        # 初始化全局重复生成次数变量
        if not hasattr(self, "global_batch_generate_count") or self.global_batch_generate_count is None:
            self.global_batch_generate_count = tk.StringVar(value="1")
        
        if not hasattr(self, "global_image_frame"):
            self.global_image_frame = ttk.Labelframe(self.fixed_frame, text="图片参数(全局)")
            
            # K采样器步数设置
            global_k_sampler_frame = ttk.Frame(self.global_image_frame)
            global_k_sampler_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
            
            global_k_sampler_label = ttk.Label(global_k_sampler_frame, text="K采样器步数:")
            global_k_sampler_label.pack(side=tk.LEFT, padx=2)
            
            global_k_sampler_entry = ttk.Entry(global_k_sampler_frame, textvariable=self.global_k_sampler_steps, width=5)
            global_k_sampler_entry.pack(side=tk.LEFT, padx=2)
            # 绑定鼠标事件
            global_k_sampler_entry.bind("<Enter>", self.show_tooltip)
            global_k_sampler_entry.bind("<Leave>", self.hide_tooltip)
            
            # 图片尺寸设置
            global_image_size_frame = ttk.Frame(self.global_image_frame)
            global_image_size_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
            
            global_image_size_label = ttk.Label(global_image_size_frame, text="图片尺寸:")
            global_image_size_label.pack(side=tk.LEFT, padx=2)
            
            # 高度输入框
            global_height_label = ttk.Label(global_image_size_frame, text="高")
            global_height_label.pack(side=tk.LEFT, padx=2)
            
            global_height_entry = ttk.Entry(global_image_size_frame, textvariable=self.global_image_height, width=5)
            global_height_entry.pack(side=tk.LEFT, padx=2)
            
            global_x_label = ttk.Label(global_image_size_frame, text="x")
            global_x_label.pack(side=tk.LEFT, padx=2)
            
            # 宽度输入框
            global_width_label = ttk.Label(global_image_size_frame, text="宽")
            global_width_label.pack(side=tk.LEFT, padx=2)
            
            global_width_entry = ttk.Entry(global_image_size_frame, textvariable=self.global_image_width, width=5)
            global_width_entry.pack(side=tk.LEFT, padx=2)
            
            # 图片方向单选按钮
            global_orientation_frame = ttk.Frame(self.global_image_frame)
            global_orientation_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
            
            # 竖屏单选按钮
            global_portrait_radio = ttk.Radiobutton(global_orientation_frame, text="竖屏", variable=self.global_orientation, value="portrait", command=self.on_global_portrait_selected)
            global_portrait_radio.pack(side=tk.LEFT, padx=2)
            
            # 横屏单选按钮
            global_landscape_radio = ttk.Radiobutton(global_orientation_frame, text="横屏", variable=self.global_orientation, value="landscape", command=self.on_global_landscape_selected)
            global_landscape_radio.pack(side=tk.LEFT, padx=2)
            
            
            # 添加垂直分隔符
            separator = ttk.Separator(global_orientation_frame, orient=tk.VERTICAL)
            separator.pack(side=tk.LEFT, fill=tk.Y, padx=10)
            
            # 批量同步按钮 - 放在横屏按钮右侧，调整大小
            sync_btn = ttk.Button(global_orientation_frame, text=tr("批量同步"), command=self.sync_image_params, width=10)
            sync_btn.pack(side=tk.LEFT, padx=2)
            
            # 重复生成次数设置 - 移到竖屏/横屏单选按钮下方
            global_batch_count_frame = ttk.Frame(self.global_image_frame)
            global_batch_count_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
            
            # 创建重复生成次数标签
            global_batch_count_label = ttk.Label(global_batch_count_frame, text="* 重复生成次数")
            global_batch_count_label.pack(side=tk.LEFT, padx=2)
            
            # 创建重复生成次数文本框
            global_batch_count_entry = ttk.Entry(global_batch_count_frame, textvariable=self.global_batch_generate_count, width=5)
            global_batch_count_entry.pack(side=tk.LEFT, padx=2)
            
            # 重复生成次数验证函数
            def validate_global_batch_count(*args):
                # 获取当前输入值
                count_str = self.global_batch_generate_count.get()
                try:
                    count = int(count_str)
                    # 检查是否在1-48范围内
                    if 1 <= count <= 48:
                        # 输入正确，恢复默认颜色
                        global_batch_count_label.configure(foreground="")
                    else:
                        # 输入超出范围，显示红色并强制转换
                        global_batch_count_label.configure(foreground="red")
                        if count < 1:
                            # 输入小于1，强制设为1
                            self.global_batch_generate_count.set("1")
                            global_batch_count_label.configure(foreground="")
                        elif count > 48:
                            # 输入大于48，强制设为48
                            self.global_batch_generate_count.set("48")
                            global_batch_count_label.configure(foreground="")
                except ValueError:
                    # 输入不是数字，显示红色
                    global_batch_count_label.configure(foreground="red")
            
            # 绑定验证函数到变量变化事件
            self.global_batch_generate_count.trace_add("write", validate_global_batch_count)
            # 初始验证
            validate_global_batch_count()
        
        # 初始化顶部框体列表和可见性状态
        self.top_frames = [
            self.current_workflow_frame,
            self.img_frame,
            self.prompt_frame,
            self.image_gen_frame,
            self.global_image_frame
        ]
        
        # 初始化顶部框体可见性状态
        self.top_frames_visible = {
            self.current_workflow_frame: True,
            self.img_frame: True,
            self.prompt_frame: True,
            self.image_gen_frame: True,
            self.global_image_frame: True
        }
        
        # 添加UI日志
        self.add_ui_log(self.current_workflow_frame, "当前工作流: 已加载")
        self.add_ui_log(self.img_frame, "图片: 已初始化")
        self.add_ui_log(self.prompt_frame, "文/图生图动作提示词: 已初始化")
        self.add_ui_log(self.image_gen_frame, "批量生成新资源: 已初始化")
        self.add_ui_log(self.global_image_frame, "图片参数(全局): 已初始化")
        
        # 调用动态布局方法
        self.layout_top_frames()
    
    def start_timer(self):
        """启动计时器"""
        if not self.timer_running:
            self.start_time = time.time()
            self.timer_running = True
            self.update_timer()
    
    def stop_timer(self):
        """停止计时器"""
        if self.timer_running:
            self.timer_running = False
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
                self.timer_id = None
    
    def update_timer(self):
        """更新计时器显示"""
        if self.timer_running:
            elapsed = time.time() - self.start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            self.timer_var.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            # 每秒更新一次
            self.timer_id = self.root.after(1000, self.update_timer)
    
    def start_row_timer(self, row_index):
        """启动指定行的计时器"""
        if hasattr(self, "row_timer_running") and row_index < len(self.row_timer_running):
            if not self.row_timer_running[row_index]:
                # 初始化该行的开始时间
                if len(self.row_timers) <= row_index:
                    self.row_timers.extend([time.time()] * (row_index + 1 - len(self.row_timers)))
                self.row_timers[row_index] = time.time()
                self.row_timer_running[row_index] = True
                # 计时器启动时，标签颜色改为红色
                if hasattr(self, "row_timer_labels") and row_index < len(self.row_timer_labels):
                    if self.row_timer_labels[row_index]:
                        self.row_timer_labels[row_index].config(foreground="red")
                self.update_row_timer(row_index)
    
    def stop_row_timer(self, row_index):
        """停止指定行的计时器"""
        if hasattr(self, "row_timer_running") and row_index < len(self.row_timer_running):
            if self.row_timer_running[row_index]:
                self.row_timer_running[row_index] = False
                if hasattr(self, "row_timer_ids") and row_index < len(self.row_timer_ids):
                    if self.row_timer_ids[row_index]:
                        self.root.after_cancel(self.row_timer_ids[row_index])
                        self.row_timer_ids[row_index] = None
                # 计时器停止时，标签颜色改为白色
                if hasattr(self, "row_timer_labels") and row_index < len(self.row_timer_labels):
                    if self.row_timer_labels[row_index]:
                        self.row_timer_labels[row_index].config(foreground="white")
    
    def update_row_timer(self, row_index):
        """更新指定行的计时器显示"""
        if hasattr(self, "row_timer_running") and row_index < len(self.row_timer_running):
            if self.row_timer_running[row_index]:
                elapsed = time.time() - self.row_timers[row_index]
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                seconds = int(elapsed % 60)
                if hasattr(self, "row_timer_vars") and row_index < len(self.row_timer_vars):
                    self.row_timer_vars[row_index].set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                # 每秒更新一次
                self.row_timer_ids[row_index] = self.root.after(1000, lambda: self.update_row_timer(row_index))
    
    def play_finish_sound(self):
        """播放完成提醒音乐"""
        import subprocess
        import os
        
        # 音乐文件路径（使用相对路径）
        sound_path = os.path.join("config", "Reminder Tone", "ding-finish.mp3")
        
        # 检查文件是否存在
        if os.path.exists(sound_path):
            try:
                # 使用系统默认播放器播放音乐
                subprocess.Popen(["python", "-c", f"import winsound; winsound.PlaySound('{sound_path.replace(chr(92), chr(92)*2)}', winsound.SND_FILENAME | winsound.SND_ASYNC)"])
            except Exception as e:
                print(f"播放音乐失败: {e}")
        else:
            print(f"音乐文件不存在: {sound_path}")
    
    def sync_image_params(self):
        """同步全局参数到所有行
        
        将全局图片参数同步到所有内容行，确保参数一致性
        """
        if hasattr(self, "k_sampler_steps_list") and hasattr(self, "image_height_list") and hasattr(self, "image_width_list") and hasattr(self, "image_orientation_list"):
            # 确保所有全局变量已初始化
            if not hasattr(self, "global_orientation") or self.global_orientation is None:
                self.global_orientation = tk.StringVar(value="portrait")
            if not hasattr(self, "global_k_sampler_steps") or self.global_k_sampler_steps is None:
                self.global_k_sampler_steps = tk.StringVar(value="4")
            if not hasattr(self, "global_image_height") or self.global_image_height is None:
                self.global_image_height = tk.StringVar(value="832")
            if not hasattr(self, "global_image_width") or self.global_image_width is None:
                self.global_image_width = tk.StringVar(value="480")
            # 获取全局参数值
            global_steps = self.global_k_sampler_steps.get()
            global_height = self.global_image_height.get()
            global_width = self.global_image_width.get()
            global_orient = self.global_orientation.get()
            
            # 更新所有行的参数
            for i in range(len(self.k_sampler_steps_list)):
                if i < len(self.k_sampler_steps_list):
                    self.k_sampler_steps_list[i].set(global_steps)
                if i < len(self.image_height_list):
                    self.image_height_list[i].set(global_height)
                if i < len(self.image_width_list):
                    self.image_width_list[i].set(global_width)
                if i < len(self.image_orientation_list):
                    self.image_orientation_list[i].set(global_orient)
                # 同步重复生成次数
                if hasattr(self, "global_batch_generate_count") and hasattr(self, "batch_generate_count_list"):
                    global_batch_count = self.global_batch_generate_count.get()
                    if i < len(self.batch_generate_count_list):
                        self.batch_generate_count_list[i].set(global_batch_count)
    
    def toggle_select_all(self):
        """全选/取消全选所有图片项目
        
        根据全选状态，更新所有图片项目的勾选状态和API返回图片框的背景颜色
        """
        select_all_state = self.select_all_var.get()
        if hasattr(self, "image_item_vars") and hasattr(self, "api_image_frames"):
            for i, var in enumerate(self.image_item_vars):
                if select_all_state:
                    # 勾选时，联动勾选所有行
                    var.set(True)
                    # 同步更新对应API返回图片区域的颜色
                    if i < len(self.api_image_frames):
                        api_frame = self.api_image_frames[i]
                        api_frame.configure(style="Pink.TFrame")
                else:
                    # 取消勾选时，取消所有勾选
                    var.set(False)
                    # 同步更新对应API返回图片区域的颜色
                    if i < len(self.api_image_frames):
                        api_frame = self.api_image_frames[i]
                        api_frame.configure(style="TFrame")
    
    def on_global_portrait_selected(self):
        """处理全局竖屏选择事件
        
        当选择竖屏时，更新全局图片参数为竖屏尺寸
        """
        self.global_orientation.set("portrait")
        # 从当前使用的INI文件中读取竖屏尺寸
        import os
        import configparser
        ini_path = os.path.splitext(self.WORKFLOW_PATH)[0] + ".ini"
        # 从配置文件获取默认值
        portrait_height = self.config.get("ImageToImage_K_Generation", "default_portrait_height", fallback="832")
        portrait_width = self.config.get("ImageToImage_K_Generation", "default_portrait_width", fallback="480")
        
        if os.path.exists(ini_path):
            config = configparser.ConfigParser()
            try:
                config.read(ini_path, encoding='utf-8')
                if '横竖屏默认尺寸' in config:
                    portrait_height = config.get('横竖屏默认尺寸', 'portrait_height', fallback=portrait_height)
                    portrait_width = config.get('横竖屏默认尺寸', 'portrait_width', fallback=portrait_width)
            except (configparser.DuplicateSectionError, configparser.MissingSectionHeaderError, Exception):
                # 如果INI文件格式有问题，使用默认尺寸
                pass
        
        # 设置为固定竖屏尺寸：高度=832，宽度=480
        self.global_image_height.set("832")
        self.global_image_width.set("480")
    
    def on_global_landscape_selected(self):
        """处理全局横屏选择事件
        
        当选择横屏时，更新全局图片参数为横屏尺寸
        """
        self.global_orientation.set("landscape")
        # 从当前使用的INI文件中读取横屏尺寸
        import os
        import configparser
        ini_path = os.path.splitext(self.WORKFLOW_PATH)[0] + ".ini"
        landscape_height = "480"
        landscape_width = "832"
        
        if os.path.exists(ini_path):
            config = configparser.ConfigParser()
            try:
                config.read(ini_path, encoding='utf-8')
                if '横竖屏默认尺寸' in config:
                    landscape_height = config.get('横竖屏默认尺寸', 'landscape_height', fallback=landscape_height)
                    landscape_width = config.get('横竖屏默认尺寸', 'landscape_width', fallback=landscape_width)
            except (configparser.DuplicateSectionError, configparser.MissingSectionHeaderError, Exception):
                # 如果INI文件格式有问题，使用默认尺寸
                pass
        
        # 设置为固定横屏尺寸：高度=480，宽度=832
        self.global_image_height.set("480")
        self.global_image_width.set("832")
    
    def create_batch_translate_row(self):
        """创建批量翻译行"""
        # 中间批量翻译按钮
        batch_trans_btn = ttk.Button(self.prompt_frame, text=tr("Tencent批量翻译"), command=self.batch_translate, width=15)
        batch_trans_btn.pack(padx=5, pady=3)
        
        # Ollama批量翻译按钮
        ollama_batch_trans_btn = ttk.Button(self.prompt_frame, text=tr("Ollama批量翻译"), command=self.ollama_batch_translate, width=15)
        ollama_batch_trans_btn.pack(padx=5, pady=3)
        
        # 批量直译按钮
        batch_copy_btn = ttk.Button(self.prompt_frame, text=tr("批量直译"), command=self.batch_copy_prompts, width=15)
        batch_copy_btn.pack(padx=5, pady=3)
        
        # 停止翻译按钮
        self.stop_translate_btn = ttk.Button(self.prompt_frame, text=tr("停止翻译"), command=self.stop_translate, width=15, style="secondary.TButton")
        self.stop_translate_btn.pack(padx=5, pady=3)
        self.stop_translate_btn.config(state=tk.DISABLED)
        
        # 右侧批量生成设置
        batch_gen_frame = ttk.Frame(self.image_gen_frame)
        batch_gen_frame.pack(padx=5, pady=5, fill=tk.X)
        
        # 全选项目勾选框
        self.select_all_var = tk.BooleanVar()
        self.select_all_var.set(False)
        
        # 计时器框架
        timer_frame = ttk.Frame(self.image_gen_frame, borderwidth=2, relief=tk.SUNKEN)
        timer_frame.pack(padx=5, pady=5, fill=tk.X)
        
        # 计时器标题和显示
        timer_label = ttk.Label(timer_frame, text=tr("生成时间:"))
        timer_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        # 初始化计时器变量
        self.timer_var = tk.StringVar(value="00:00:00")
        self.timer_running = False
        self.start_time = 0
        self.timer_id = None
        
        # 计时器显示标签
        self.timer_display = ttk.Label(timer_frame, textvariable=self.timer_var, font=('宋体', 14, 'bold'))
        self.timer_display.pack(side=tk.LEFT, padx=10, pady=10)
        
        # 全选项目
        select_all_checkbox = ttk.Checkbutton(batch_gen_frame, text=tr("全选项目"), variable=self.select_all_var, command=self.toggle_select_all)
        select_all_checkbox.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 批量生成图片按钮
        batch_gen_btn = ttk.Button(batch_gen_frame, text=tr("批量生成图片"), command=self.process_selected_images)
        batch_gen_btn.pack(side=tk.LEFT, padx=2, pady=2)
        




        
        # 当前工作流框体将在create_grid_layout方法中创建到main_frame的图片列位置
    
    def create_content_row(self, row_index):
        """创建内容行
        
        Args:
            row_index: 行索引，0表示第一行，1表示第二行
        """
        base_row = 2 + row_index * 2  # 每两行一个内容组，更紧凑的布局
        
        # 获取当前模式的框架可见性配置
        def get_frame_visibility(frame_name):
            """获取框架在当前模式下的可见性
            
            Args:
                frame_name: 框架代码名
                
            Returns:
                bool: True表示显示，False表示隐藏
            """
            # 默认显示所有框架
            default_visibility = True
            
            try:
                # 导入必要的模块
                import configparser
                import os
                
                # 创建一个新的配置解析器，用于读取工作流对应的INI文件
                ini_config = configparser.ConfigParser()
                
                # 读取当前工作流对应的INI文件（如果存在）
                if hasattr(self, "ini_path") and os.path.exists(self.ini_path):
                    try:
                        # 使用utf-8-sig编码处理带有BOM的文件
                        with open(self.ini_path, 'r', encoding='utf-8-sig') as f:
                            ini_config.read_file(f)
                    except Exception as e:
                        print(f"警告: 无法读取工作流INI文件 '{self.ini_path}': {str(e)}")
                
                # 同时读取主配置文件，作为备用
                try:
                    with open("setting.ini", 'r', encoding='utf-8-sig') as f:
                        ini_config.read_file(f)
                except Exception as e:
                    print(f"警告: 无法读取主配置文件 'setting.ini': {str(e)}")
                
                # 根据当前工作流类型确定配置节
                workflow_type = self.config.get("ComfyUI", "workflow_path", fallback="图生图")
                
                # 默认配置节
                section = "FrameVisibility_ImageToImage"
                
                # 从配置文件中读取所有可用模式
                if self.config.has_section("FrameVisibility_Modes"):
                    # 遍历所有模式，查找匹配当前工作流类型的模式
                    for mode_config in self.config.items("FrameVisibility_Modes"):
                        mode_name = mode_config[0]
                        mode_info = mode_config[1]
                        
                        # 解析模式配置：section_name, workflow_identifier
                        mode_parts = mode_info.split(",")
                        if len(mode_parts) >= 2:
                            mode_section = mode_parts[0].strip()
                            workflow_identifier = mode_parts[1].strip()
                            
                            # 检查当前工作流类型是否匹配
                            if workflow_identifier in workflow_type:
                                section = mode_section
                                break
                
                # 读取配置
                visibility = ini_config.get(section, frame_name, fallback="Y")
                return visibility.upper() == "Y"
            except:
                # 如果配置读取失败，返回默认值
                return default_visibility
        
        # No.框体 - 显示序号01~30
        no_frame = ttk.Labelframe(self.main_frame, text=f"No.{row_index+1}")
        if get_frame_visibility("no_frame"):
            no_frame.grid(row=base_row, column=0, rowspan=2, padx=3, pady=3, sticky=tk.NSEW)
        
        # 确保content_no_frames列表只包含当前行的框架实例
        # 如果列表索引超出范围，扩展列表；否则替换现有框架
        if row_index < len(self.content_no_frames):
            # 替换现有框架
            self.content_no_frames[row_index] = no_frame
        else:
            # 添加新框架
            self.content_no_frames.append(no_frame)
        
        # 序号标签，居中显示，格式为01~30
        no_label = ttk.Label(no_frame, text=f"{row_index+1:02d}", font=('SimHei', 12, 'bold'), anchor=tk.CENTER)
        no_label.pack(expand=True, fill=tk.BOTH)
        
        # 左侧图片区域
        img_frame = ttk.Labelframe(self.main_frame, text=f"{tr('图A')}{row_index+1}")
        # 计算正确的列索引：No.框体在列0，图片框体在列1
        if get_frame_visibility("img_frame"):
            img_frame.grid(row=base_row, column=1, rowspan=2, padx=3, pady=3, sticky=tk.NSEW)
        
        # 确保content_img_frames列表只包含当前行的框架实例
        # 如果列表索引超出范围，扩展列表；否则替换现有框架
        if row_index < len(self.content_img_frames):
            # 替换现有框架
            self.content_img_frames[row_index] = img_frame
        else:
            # 添加新框架
            self.content_img_frames.append(img_frame)
        
        # 增大图片显示区域大小
        img_frame_inner = ttk.Frame(img_frame, width=200, height=200)
        img_frame_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 拖入/点击导入提示
        if not hasattr(self, "img_prompts"):
            self.img_prompts = []
            self.img_labels = []
        
        img_prompt = ttk.Label(img_frame_inner, text="拖入图片或点击导入", justify=tk.CENTER)
        img_prompt.pack(expand=True)
        self.img_prompts.append(img_prompt)
        
        # 图片显示标签
        img_label = ttk.Label(img_frame_inner, anchor=tk.CENTER)
        img_label.pack(expand=True)
        img_label.pack_forget()  # 初始隐藏
        self.img_labels.append(img_label)
        
        # 绑定鼠标进入和离开事件，实现悬停显示按钮
        def on_click(e):
            # 没有图片时，点击导入图片
            if not (hasattr(self, "image_cache") and row_index < len(self.image_cache) and self.image_cache[row_index] is not None):
                self.import_image(row_index)
        
        def on_mouse_enter(e):
            # 如果已经有图片，显示操作按钮
            if row_index < len(self.img_labels) and hasattr(self, "image_cache") and row_index < len(self.image_cache) and self.image_cache[row_index] is not None:
                self.show_image_buttons(row_index)
        
        def on_mouse_leave(e):
            # 鼠标离开时隐藏操作按钮，但确保鼠标没有移动到按钮上
            # 获取鼠标当前位置
            x, y = img_frame_inner.winfo_pointerxy()
            # 检查鼠标是否在按钮区域内
            if hasattr(self, "button_frame") and self.button_frame is not None:
                button_x = self.button_frame.winfo_rootx()
                button_y = self.button_frame.winfo_rooty()
                button_width = self.button_frame.winfo_width()
                button_height = self.button_frame.winfo_height()
                # 如果鼠标在按钮区域内，不隐藏按钮
                if button_x <= x <= button_x + button_width and button_y <= y <= button_y + button_height:
                    return
            # 否则隐藏按钮
            self.hide_image_buttons()
        
        img_frame_inner.bind("<ButtonPress-1>", on_click)
        img_frame_inner.bind("<Enter>", on_mouse_enter)
        img_frame_inner.bind("<Leave>", on_mouse_leave)
        img_frame_inner.config(cursor="hand2")
        
        # 使用tkinterdnd2实现拖放功能
        img_frame_inner.drop_target_register(DND_FILES)
        img_frame_inner.dnd_bind("<<Drop>>", lambda e, i=row_index: self.handle_drop(e, i))
        
        # 确保所有事件能够触发
        img_prompt.bind("<ButtonPress-1>", on_click)
        img_prompt.bind("<Enter>", on_mouse_enter)
        img_prompt.bind("<Leave>", on_mouse_leave)
        img_label.bind("<ButtonPress-1>", on_click)
        img_label.bind("<Enter>", on_mouse_enter)
        img_label.bind("<Leave>", on_mouse_leave)
        
        # 保存图片框引用
        if not hasattr(self, "img_frames"):
            self.img_frames = []
        self.img_frames.append(img_frame_inner)
        
        # 保存图片框架引用，用于后续控制可见性
        if not hasattr(self, "content_img_frames"):
            self.content_img_frames = []
        self.content_img_frames.append(img_frame)
        
        # 中间提示词区域 - 正向提示词
        prompt_frame = ttk.Labelframe(self.main_frame, text="")
        if get_frame_visibility("prompt_frame"):
            prompt_frame.grid(row=base_row, column=2, padx=3, pady=3, sticky=tk.NSEW)
        self.prompt_frames.append(prompt_frame)
        
        # 创建彩色状态显示系统
        class ColorfulStatusLabelframe:
            def __init__(self, labelframe, title, initial_status):
                self.labelframe = labelframe
                self.title = title
                self.status = initial_status
                
                # 直接设置Labelframe标题，不隐藏
                self.update_status(initial_status)
            
            def update_status(self, status):
                self.status = status
                
                # 根据状态设置颜色代码
                status_colors = {
                    "none": "gray",
                    "translating": "blue",
                    "translated": "darkgreen",
                    "pass": "darkgreen",
                    "error": "red",
                    "无需翻译": "#888888"
                }
                color = status_colors.get(status, "black")
                
                # 创建富文本标题
                self.labelframe.configure(text=f"{self.title} ({status})")
        
        # 初始化状态显示系统
        
        # 创建提示词输入容器，用于放置两个并排的文本框
        prompts_container = ttk.Frame(prompt_frame)
        prompts_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 初始化提示词文本框列表
        if not hasattr(self, "prompt_texts"):
            self.prompt_texts = []
        if not hasattr(self, "english_texts"):
            self.english_texts = []
        if not hasattr(self, "negative_prompt_texts"):
            self.negative_prompt_texts = []
        if not hasattr(self, "negative_english_texts"):
            self.negative_english_texts = []
        if not hasattr(self, "translation_status_labels"):
            self.translation_status_labels = []
        
        # 中文提示词文本框
        cn_prompt = tk.Text(prompts_container, width=8, height=6)
        cn_prompt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.prompt_texts.append(cn_prompt)
        
        # 英文翻译文本框
        en_prompt = tk.Text(prompts_container, width=8, height=6)
        en_prompt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.english_texts.append(en_prompt)
        
        # 中间提示词区域 - 负面提示词
        negative_prompt_frame = ttk.Labelframe(self.main_frame, text="")
        if get_frame_visibility("negative_prompt_frame"):
            negative_prompt_frame.grid(row=base_row, column=3, padx=3, pady=3, sticky=tk.NSEW)
        self.negative_prompt_frames.append(negative_prompt_frame)
        
        # 创建并添加彩色状态显示
        prompt_status = ColorfulStatusLabelframe(
            prompt_frame, "正向提示词", "none"
        )
        negative_status = ColorfulStatusLabelframe(
            negative_prompt_frame, "负面提示词", "none"
        )
        
        # 确保translation_status_labels列表存在且只包含ColorfulStatusLabelframe对象
        if not hasattr(self, "translation_status_labels"):
            self.translation_status_labels = []
        
        # 根据行数计算要插入的位置（每行2个标签）
        insert_pos = 2 * len(self.img_frames) - 2
        if insert_pos < 0:
            insert_pos = 0
        
        # 插入到正确位置
        if insert_pos < len(self.translation_status_labels):
            self.translation_status_labels.insert(insert_pos, prompt_status)
            self.translation_status_labels.insert(insert_pos + 1, negative_status)
        else:
            self.translation_status_labels.append(prompt_status)
            self.translation_status_labels.append(negative_status)
        
        # 创建负面提示词输入容器
        negative_prompts_container = ttk.Frame(negative_prompt_frame)
        negative_prompts_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 中文负面提示词文本框
        cn_negative_prompt = tk.Text(negative_prompts_container, width=8, height=6)
        cn_negative_prompt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.negative_prompt_texts.append(cn_negative_prompt)
        
        # 英文负面提示词翻译文本框
        en_negative_prompt = tk.Text(negative_prompts_container, width=8, height=6)
        en_negative_prompt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        self.negative_english_texts.append(en_negative_prompt)
        
        # 立即应用当前主题的颜色设置
        for text_widget, placeholder in [(cn_prompt, tr("中文提示词")), (en_prompt, tr("英文翻译")), 
                                         (cn_negative_prompt, tr("中文负面提示词")), (en_negative_prompt, tr("英文负面翻译"))]:
            current_text = text_widget.get("1.0", tk.END).strip()
            if current_text == placeholder:
                text_widget.config(fg="gray")
            else:
                try:
                    # 特定主题下使用白色字体
                    special_themes_str = self.config.get("UI", "special_themes", fallback="darkly,superhero,cyborg,vapor,solar")
                    special_themes = [theme.strip() for theme in special_themes_str.split(",")]
                    if self.style.theme_use() in special_themes:
                        text_widget.config(fg="#ffffff")
                    else:
                        text_widget.config(fg="black")
                except:
                    # 如果出错，默认使用黑色
                    text_widget.config(fg="black")
        
        # 定义状态样式
        self.style.configure("status.TLabel", foreground="black", background="white")
        self.style.configure("status_ready.TLabel", foreground="green")
        self.style.configure("status_translating.TLabel", foreground="blue")
        self.style.configure("status_pass.TLabel", foreground="darkgreen")
        self.style.configure("status_error.TLabel", foreground="red")
        self.style.configure("status_none.TLabel", foreground="gray")
        self.style.configure("status_translated.TLabel", foreground="darkgreen")
        self.style.configure("status_no_translate.TLabel", foreground="#888888")
        
        # 定义状态相关的Labelframe样式
        self.style.configure("StatusTLabelframe.TLabelframe.Label", foreground="black")
        self.style.configure("StatusNone.TLabelframe.Label", foreground="gray")
        self.style.configure("StatusTranslating.TLabelframe.Label", foreground="blue")
        self.style.configure("StatusTranslated.TLabelframe.Label", foreground="darkgreen")
        self.style.configure("StatusPass.TLabelframe.Label", foreground="darkgreen")
        self.style.configure("StatusError.TLabelframe.Label", foreground="red")
        self.style.configure("StatusNoTranslate.TLabelframe.Label", foreground="#888888")
        # 为API图片生成状态添加样式 - 设置为白色
        self.style.configure("StatusNone.TLabelframe.Label", foreground="white")
        self.style.configure("StatusGenerating.TLabelframe.Label", foreground="white")
        self.style.configure("StatusFinish.TLabelframe.Label", foreground="white")
        # 定义小字体按钮样式
        self.style.configure("SmallFont.TButton", font=('宋体', 6))
        # 定义翻译相关按钮样式，与生成图片(单个)按钮保持一致
        # 使用与默认按钮完全一致的样式，仅设置字体和标签对齐方式
        self.style.configure("TransButton.TButton", font=('宋体', self.ui_font_size))
        
        # 确保没有覆盖默认的颜色和边框属性
        self.style.map("TransButton.TButton",
            foreground=[],
            background=[],
            bordercolor=[],
            lightcolor=[],
            darkcolor=[])
            
        # 配置多行按钮文本居中对齐
        self.style.configure("TransButton.TButton.Label", justify='center')
        
        # 添加初始灰色提示文字
        def add_placeholder(text_widget, placeholder):
            """添加初始灰色提示文字"""
            text_widget.insert("1.0", placeholder)
            text_widget.config(fg="gray")
            
            # 绑定焦点事件
            def on_focus_in(event):
                if text_widget.get("1.0", tk.END).strip() == placeholder:
                    text_widget.delete("1.0", tk.END)
                    # 特定主题下使用白色字体
                    try:
                        special_themes_str = self.config.get("UI", "special_themes", fallback="darkly,superhero,cyborg,vapor,solar")
                        special_themes = [theme.strip() for theme in special_themes_str.split(",")]
                        if self.style.theme_use() in special_themes:
                            text_widget.config(fg="#ffffff")
                        else:
                            text_widget.config(fg="black")
                    except:
                        # 如果出错，默认使用黑色
                        text_widget.config(fg="black")
            
            def on_focus_out(event):
                if not text_widget.get("1.0", tk.END).strip():
                    text_widget.insert("1.0", placeholder)
                    text_widget.config(fg="gray")
            
            text_widget.bind("<FocusIn>", on_focus_in)
            text_widget.bind("<FocusOut>", on_focus_out)
            
            # 绑定主题切换事件，确保占位符和输入文本颜色正确
            def on_theme_changed():
                current_text = text_widget.get("1.0", tk.END).strip()
                if current_text == placeholder:
                    text_widget.config(fg="gray")
                else:
                    try:
                        # 特定主题下使用白色字体
                        special_themes_str = self.config.get("UI", "special_themes", fallback="darkly,superhero,cyborg,vapor,solar")
                        special_themes = [theme.strip() for theme in special_themes_str.split(",")]
                        if self.style.theme_use() in special_themes:
                            text_widget.config(fg="#ffffff")
                        else:
                            text_widget.config(fg="black")
                    except:
                        # 如果出错，默认使用黑色
                        text_widget.config(fg="black")
            
            text_widget.on_theme_changed = on_theme_changed
            
            # 绑定内容变化事件，将状态设置为编辑中
            def on_content_changed(event):
                # 检查是否真的有修改
                if text_widget.edit_modified():
                    self.is_edited = True
                    self.update_window_title()
                    text_widget.edit_modified(False)
                    # 更新文本框颜色
                    if row_index < len(self.prompt_texts) and text_widget == self.prompt_texts[row_index]:
                        self.set_textbox_color(text_widget, "中文提示词")
                    elif row_index < len(self.english_texts) and text_widget == self.english_texts[row_index]:
                        self.set_textbox_color(text_widget, "英文翻译")
                    elif row_index < len(self.negative_prompt_texts) and text_widget == self.negative_prompt_texts[row_index]:
                        self.set_textbox_color(text_widget, "中文负面提示词")
                    elif row_index < len(self.negative_english_texts) and text_widget == self.negative_english_texts[row_index]:
                        self.set_textbox_color(text_widget, "英文负面翻译")
            
            # 绑定多种事件，确保所有修改操作都能触发状态更新
            text_widget.bind("<KeyRelease>", on_content_changed)
            text_widget.bind("<ButtonRelease-2>", on_content_changed)  # 鼠标中键粘贴
            text_widget.bind("<ButtonRelease-3>", on_content_changed)  # 右键菜单操作
            
            # 绑定Ctrl+V粘贴事件
            text_widget.bind("<Control-v>", on_content_changed)
            text_widget.bind("<Control-V>", on_content_changed)
            
            # 绑定文本修改事件（针对所有修改）
            def on_text_modified(event):
                if text_widget.edit_modified():
                    # 确保每次修改都会触发状态更新
                    self.is_edited = True
                    self.update_window_title()
                    # 重置修改标志
                    text_widget.edit_modified(False)
                    # 更新文本框颜色
                    if row_index < len(self.prompt_texts) and text_widget == self.prompt_texts[row_index]:
                        self.set_textbox_color(text_widget, "中文提示词")
                    elif row_index < len(self.english_texts) and text_widget == self.english_texts[row_index]:
                        self.set_textbox_color(text_widget, "英文翻译")
                    elif row_index < len(self.negative_prompt_texts) and text_widget == self.negative_prompt_texts[row_index]:
                        self.set_textbox_color(text_widget, "中文负面提示词")
                    elif row_index < len(self.negative_english_texts) and text_widget == self.negative_english_texts[row_index]:
                        self.set_textbox_color(text_widget, "英文负面翻译")
            
            text_widget.bind("<<Modified>>", on_text_modified)
        
        # 为两个正向提示词文本框添加提示文字
        add_placeholder(cn_prompt, tr("中文提示词"))
        add_placeholder(en_prompt, tr("英文翻译"))
        
        # 为两个负面提示词文本框添加提示文字
        add_placeholder(cn_negative_prompt, tr("中文负面提示词"))
        add_placeholder(en_negative_prompt, tr("英文负面翻译"))
        
        # 初始化图片项目勾选变量列表
        if not hasattr(self, "image_item_vars"):
            self.image_item_vars = []
        
        # 创建图片项目勾选变量
        image_item_var = tk.BooleanVar()
        image_item_var.set(False)
        self.image_item_vars.append(image_item_var)
        
        # 创建正向提示词按钮容器 - N1框体
        positive_buttons_frame = ttk.Labelframe(self.main_frame, text="N1")
        if get_frame_visibility("positive_buttons_frame"):
            positive_buttons_frame.grid(row=base_row+1, column=2, padx=10, pady=5, sticky=tk.W)
        self.positive_buttons_frames.append(positive_buttons_frame)
        
        # 正向提示词区域的翻译和删除按钮
        positive_trans_btn = ttk.Button(positive_buttons_frame, text="腾讯翻译(正向)", command=lambda: self.translate_prompt(row_index, is_negative=False), width=14)
        positive_trans_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Ollama翻译(正向)按钮
        ollama_positive_trans_btn = ttk.Button(positive_buttons_frame, text="Ollama翻译(正向)", command=lambda: self.ollama_translate_prompt(row_index, is_negative=False), width=14)
        ollama_positive_trans_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        positive_clear_btn = ttk.Button(positive_buttons_frame, text="删除提示词(正向)", command=lambda: self.clear_prompt(row_index, is_positive=True), width=14)
        positive_clear_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 创建负面提示词按钮容器 - N2框体
        negative_buttons_frame = ttk.Labelframe(self.main_frame, text="N2")
        if get_frame_visibility("negative_buttons_frame"):
            negative_buttons_frame.grid(row=base_row+1, column=3, padx=10, pady=5, sticky=tk.W)
        self.negative_buttons_frames.append(negative_buttons_frame)
        
        # 负面提示词区域的翻译和删除按钮
        negative_trans_btn = ttk.Button(negative_buttons_frame, text="腾讯翻译(负面)", command=lambda: self.translate_prompt(row_index, is_negative=True), width=14)
        negative_trans_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Ollama翻译(负面)按钮
        ollama_negative_trans_btn = ttk.Button(negative_buttons_frame, text="Ollama翻译(负面)", command=lambda: self.ollama_translate_prompt(row_index, is_negative=True), width=14)
        ollama_negative_trans_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        negative_clear_btn = ttk.Button(negative_buttons_frame, text="删除提示词(负面)", command=lambda: self.clear_prompt(row_index, is_positive=False), width=14)
        negative_clear_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 右侧图片生成区域
        # API返回图片框
        api_frame = ttk.Labelframe(self.main_frame, text=f"{tr('API返回图片')} (none)", style="StatusNone.TLabelframe")
        if get_frame_visibility("api_frame"):
            api_frame.grid(row=base_row, column=4, padx=3, pady=3, sticky=tk.NSEW)
        
        # 保存API框体引用，用于后续更新标题
        if not hasattr(self, "api_frames"):
            self.api_frames = []
        if len(self.api_frames) <= row_index:
            self.api_frames.extend([None] * (row_index + 1 - len(self.api_frames)))
        self.api_frames[row_index] = api_frame
        
        api_frame_inner = ttk.Frame(api_frame, width=200, height=100)
        api_frame_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        api_prompt = ttk.Label(api_frame_inner, text="API返回图片显示区域", justify=tk.CENTER)
        api_prompt.pack(expand=True)
        
        # 保存内部框架引用，用于后续更新图片显示
        if not hasattr(self, "api_image_frames"):
            self.api_image_frames = []
        if len(self.api_image_frames) <= row_index:
            self.api_image_frames.extend([None] * (row_index + 1 - len(self.api_image_frames)))
        self.api_image_frames[row_index] = api_frame_inner
        
        # 图片参数设置框 - 作为单独一列放在API图片框右边
        image_params_right_frame = ttk.Labelframe(self.main_frame, text="图片参数")
        if get_frame_visibility("image_params_right_frame"):
            image_params_right_frame.grid(row=base_row, column=5, padx=3, pady=3, sticky=tk.NSEW)
        
        # 初始化每行的图片参数变量列表
        if not hasattr(self, "k_sampler_steps_list"):
            self.k_sampler_steps_list = []
            self.image_height_list = []
            self.image_width_list = []
            self.image_orientation_list = []
            self.batch_generate_count_list = []
        
        # 确保变量列表长度足够
        while len(self.k_sampler_steps_list) <= row_index:
            # 添加默认值 - 更新为高832，宽480
            self.k_sampler_steps_list.append(tk.StringVar(value="4"))
            self.image_height_list.append(tk.StringVar(value="832"))
            self.image_width_list.append(tk.StringVar(value="480"))
            self.image_orientation_list.append(tk.StringVar(value="portrait"))
            # 添加批量生成次数默认值
            self.batch_generate_count_list.append(tk.StringVar(value="1"))
        
        # K采样器步数设置
        k_sampler_frame = ttk.Frame(image_params_right_frame)
        k_sampler_frame.pack(side=tk.TOP, fill=tk.X, padx=3, pady=1)
        
        k_sampler_label = ttk.Label(k_sampler_frame, text="K采样器步数:")
        k_sampler_label.pack(side=tk.LEFT, padx=1)
        
        k_sampler_entry = ttk.Entry(k_sampler_frame, textvariable=self.k_sampler_steps_list[row_index], width=5)
        k_sampler_entry.pack(side=tk.LEFT, padx=1)
        # 绑定鼠标事件
        k_sampler_entry.bind("<Enter>", self.show_tooltip)
        k_sampler_entry.bind("<Leave>", self.hide_tooltip)
        
        # 图片尺寸设置
        video_size_frame = ttk.Frame(image_params_right_frame)
        video_size_frame.pack(side=tk.TOP, fill=tk.X, padx=3, pady=1)
        
        video_size_label = ttk.Label(video_size_frame, text="图片尺寸:")
        video_size_label.pack(side=tk.LEFT, padx=1)
        
        # 高度输入框
        height_label = ttk.Label(video_size_frame, text="高")
        height_label.pack(side=tk.LEFT, padx=1)
        
        height_entry = ttk.Entry(video_size_frame, textvariable=self.image_height_list[row_index], width=5)
        height_entry.pack(side=tk.LEFT, padx=1)
        
        x_label = ttk.Label(video_size_frame, text="x")
        x_label.pack(side=tk.LEFT, padx=1)
        
        # 宽度输入框
        width_label = ttk.Label(video_size_frame, text="宽")
        width_label.pack(side=tk.LEFT, padx=1)
        
        width_entry = ttk.Entry(video_size_frame, textvariable=self.image_width_list[row_index], width=5)
        width_entry.pack(side=tk.LEFT, padx=1)
        
        # 图片方向单选按钮
        orientation_frame = ttk.Frame(image_params_right_frame)
        orientation_frame.pack(side=tk.TOP, fill=tk.X, padx=3, pady=1)
        
        # 竖屏单选按钮
        def on_portrait_selected():
            # 竖屏：高度 > 宽度
            self.image_height_list[row_index].set("832")
            self.image_width_list[row_index].set("480")
        
        portrait_radio = ttk.Radiobutton(orientation_frame, text="竖屏", variable=self.image_orientation_list[row_index], value="portrait", command=on_portrait_selected)
        portrait_radio.pack(side=tk.LEFT, padx=1)
        
        # 横屏单选按钮
        def on_landscape_selected():
            # 横屏：宽度 > 高度
            self.image_height_list[row_index].set("480")
            self.image_width_list[row_index].set("832")
        
        landscape_radio = ttk.Radiobutton(orientation_frame, text="横屏", variable=self.image_orientation_list[row_index], value="landscape", command=on_landscape_selected)
        landscape_radio.pack(side=tk.LEFT, padx=1)
        
        # 绑定尺寸输入框变化事件
        def on_size_change(*args):
            # 当用户自行填写尺寸时，根据尺寸比例自动选择合适的单选按钮
            current_height = self.image_height_list[row_index].get()
            current_width = self.image_width_list[row_index].get()
            try:
                height = int(current_height)
                width = int(current_width)
                if height > width:
                    # 高度大于宽度，选择竖屏
                    self.image_orientation_list[row_index].set("portrait")
                else:
                    # 宽度大于等于高度，选择横屏
                    self.image_orientation_list[row_index].set("landscape")
            except ValueError:
                # 数值转换失败，保持当前选择
                pass
        
        # 将事件绑定到变量上
        self.image_height_list[row_index].trace("w", on_size_change)
        self.image_width_list[row_index].trace("w", on_size_change)
        
        # 重复生成次数设置
        batch_count_frame = ttk.Frame(image_params_right_frame)
        batch_count_frame.pack(side=tk.TOP, fill=tk.X, padx=3, pady=1)
        
        # 创建重复生成次数标签
        batch_count_label = ttk.Label(batch_count_frame, text="* 重复生成次数")
        batch_count_label.pack(side=tk.LEFT, padx=1)
        
        # 创建重复生成次数文本框
        batch_count_entry = ttk.Entry(batch_count_frame, textvariable=self.batch_generate_count_list[row_index], width=5)
        batch_count_entry.pack(side=tk.LEFT, padx=1)
        
        # 重复生成次数验证函数
        def validate_batch_count(*args):
            # 获取当前输入值
            count_str = self.batch_generate_count_list[row_index].get()
            try:
                count = int(count_str)
                # 检查是否在1-48范围内
                if 1 <= count <= 48:
                    # 输入正确，恢复默认颜色
                    batch_count_label.configure(foreground="")
                else:
                    # 输入超出范围，显示红色并强制转换
                    batch_count_label.configure(foreground="red")
                    if count < 1:
                        # 输入小于1，强制设为1
                        self.batch_generate_count_list[row_index].set("1")
                        batch_count_label.configure(foreground="")
                    elif count > 48:
                        # 输入大于48，强制设为48
                        self.batch_generate_count_list[row_index].set("48")
                        batch_count_label.configure(foreground="")
            except ValueError:
                # 输入不是数字，显示红色
                batch_count_label.configure(foreground="red")
        
        # 绑定验证函数到变量变化事件
        self.batch_generate_count_list[row_index].trace_add("write", validate_batch_count)
        # 初始验证
        validate_batch_count()
        
        # 生成图片按钮组 - 水平排列 (放在API接口返回的新图片区域下方) - N3框体
        gen_btn_frame = ttk.Labelframe(self.main_frame, text="N3")
        if get_frame_visibility("gen_btn_frame"):
            gen_btn_frame.grid(row=base_row+1, column=4, padx=5, pady=5, sticky=tk.NSEW)
        
        # 获取当前行的勾选变量
        image_item_var = self.image_item_vars[row_index]
        
        # 创建勾选框，并添加颜色切换功能
        def on_checkbox_change():
            # 根据勾选状态切换API返回图片框的背景颜色
            if image_item_var.get():
                # 设置为粉红色背景
                api_frame_inner.configure(style="Pink.TFrame")
            else:
                # 恢复默认背景
                api_frame_inner.configure(style="TFrame")
        
        # 绑定变量变化事件
        image_item_var.trace_add("write", lambda *args: on_checkbox_change())
        
        # 创建单选键变量
        if not hasattr(self, "image_radio_vars"):
            self.image_radio_vars = []
        while len(self.image_radio_vars) <= row_index:
            self.image_radio_vars.append(tk.BooleanVar(value=False))
        
        # 创建不能鼠标操控的单选键
        image_radio = ttk.Radiobutton(gen_btn_frame, variable=self.image_radio_vars[row_index], value=True, state="disabled")
        image_radio.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 添加image标签
        image_label = ttk.Label(gen_btn_frame, text="image")
        image_label.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 选择项目勾选框
        image_item_checkbox = ttk.Checkbutton(gen_btn_frame, variable=image_item_var)
        image_item_checkbox.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 选择项目标签
        image_item_label = ttk.Label(gen_btn_frame, text="选择项目")
        image_item_label.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 单个生成按钮
        single_gen_btn = ttk.Button(gen_btn_frame, text="生成图片(单个)", command=lambda: self.generate_image_single(row_index))
        single_gen_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 删除所有图片按钮
        delete_video_btn = ttk.Button(gen_btn_frame, text=tr("删除所有图片"), command=lambda: self.delete_all_images(row_index))
        delete_video_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 批量生成按钮
        batch_gen_btn = ttk.Button(gen_btn_frame, text=tr("批量生成"), command=lambda: self.batch_generate_images(row_index))
        batch_gen_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 为批量生成按钮添加悬停效果
        def on_hover(event):
            # 鼠标经过时，按钮文字变红色
            batch_gen_btn.config(style="Red.TButton")
        
        def on_leave(event):
            # 鼠标离开时，按钮恢复默认样式
            batch_gen_btn.config(style="TButton")
        
        # 创建红色样式
        if not hasattr(self, "hover_style_created"):
            self.hover_style_created = True
            style = ttk.Style()
            style.configure("Red.TButton", foreground="red")
        
        # 绑定悬停事件
        batch_gen_btn.bind("<Enter>", on_hover)
        batch_gen_btn.bind("<Leave>", on_leave)
        
        # 为每行添加计时器
        if not hasattr(self, "row_timers"):
            self.row_timers = []
            self.row_timer_vars = []
            self.row_timer_running = []
            self.row_timer_ids = []
        
        # 确保计时器列表长度足够
        while len(self.row_timers) <= row_index:
            self.row_timers.append(None)
            self.row_timer_vars.append(tk.StringVar(value="00:00:00"))
            self.row_timer_running.append(False)
            self.row_timer_ids.append(None)
        
        # 计时器标签，默认文字颜色为白色
        timer_label = ttk.Label(gen_btn_frame, textvariable=self.row_timer_vars[row_index], foreground="white")
        timer_label.pack(side=tk.LEFT, padx=10, pady=2)
        
        # 保存计时器标签引用
        if not hasattr(self, "row_timer_labels"):
            self.row_timer_labels = []
        while len(self.row_timer_labels) <= row_index:
            self.row_timer_labels.append(None)
        self.row_timer_labels[row_index] = timer_label
        
        # 绑定尺寸变化事件
        self.image_height_list[row_index].trace_add("write", on_size_change)
        self.image_width_list[row_index].trace_add("write", on_size_change)
        
        # 保存API返回图片显示区域的引用
        if not hasattr(self, "api_image_frames"):
            self.api_image_frames = []
        self.api_image_frames.append(api_frame_inner)
    
    def import_image(self, row_index):
        """点击导入图片
        
        Args:
            row_index: 图片行索引
        """
        file_path = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.gif;*.bmp"), ("所有文件", "*.*")],
            title="选择图片文件"
        )
        
        if file_path:
            self.load_image(file_path, row_index)
    
    def load_image(self, file_path, row_index):
        """加载图片并显示，尽量铺满窗体
        
        Args:
            file_path: 图片文件路径
            row_index: 图片行索引
        """
        try:
            # 保存图片实际路径，用于后续API调用
            if not hasattr(self, "image_paths"):
                self.image_paths = []
            if len(self.image_paths) <= row_index:
                self.image_paths.extend([None] * (row_index + 1 - len(self.image_paths)))
            self.image_paths[row_index] = file_path
            
            # 打开图片
            image = Image.open(file_path)
            
            # 获取显示区域大小
            img_frame = self.img_labels[row_index].master
            width = img_frame.winfo_width()
            height = img_frame.winfo_height()
            
            # 如果尺寸为0，使用默认值
            if width == 0 or height == 0:
                width, height = 150, 150
            
            # 调整缩放参数，尽量铺满窗体
            # 减少边距，让图片更贴近边框
            scale_width = width - 10  # 只留5px边距
            scale_height = height - 10
            
            # 保持宽高比缩放图片
            image.thumbnail((scale_width, scale_height), Image.LANCZOS)
            
            # 转换为Tkinter可用格式
            photo = ImageTk.PhotoImage(image)
            
            # 保存图片引用，防止被垃圾回收
            if not hasattr(self, "image_cache"):
                self.image_cache = []
            if len(self.image_cache) <= row_index:
                self.image_cache.extend([None] * (row_index + 1 - len(self.image_cache)))
            self.image_cache[row_index] = photo
            
            # 显示图片
            self.img_prompts[row_index].pack_forget()
            self.img_labels[row_index].config(image=photo, anchor=tk.CENTER)
            self.img_labels[row_index].pack(expand=True, fill=tk.BOTH)
            
            print(f"成功加载图片: {file_path}")
            print(f"图片尺寸: {image.size}, 显示区域: {width}x{height}")
            
        except Exception as e:
            print(f"加载图片失败: {e}")
            messagebox.showerror("错误", f"加载图片失败: {e}")
    
    def handle_drop(self, event, row_index):
        """处理文件拖放事件
        
        Args:
            event: 事件对象
            row_index: 图片行索引
        """
        try:
            # 获取拖放的文件路径
            file_path = event.widget.tk.splitlist(event.data)
            if file_path:
                # 取第一个文件
                actual_path = file_path[0]
                # 检查是否为图片文件
                if os.path.isfile(actual_path) and actual_path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                    self.load_image(actual_path, row_index)
        except Exception as e:
            print(f"拖放处理失败: {e}")
            messagebox.showerror("错误", f"拖放处理失败: {e}")
    
    def batch_import_images(self):
        """批量导入图片
        
        弹出文件选择对话框，允许用户多选图片，按文件名升序排列后分配到各个图片格子中
        """
        import os
        from tkinter import filedialog
        
        # 弹出文件选择对话框，允许多选图片
        file_paths = filedialog.askopenfilenames(
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.gif;*.bmp"), ("所有文件", "*.*")],
            title="选择多张图片文件"
        )
        
        if not file_paths:
            return
        
        # 按文件名升序排列
        sorted_file_paths = sorted(file_paths, key=lambda x: os.path.basename(x))
        
        # 遍历所有选中的图片文件，依次分配到各个图片格子中
        for i, file_path in enumerate(sorted_file_paths):
            # 只处理已有的图片格子
            if hasattr(self, "img_labels") and i < len(self.img_labels):
                self.load_image(file_path, i)
        
        print(f"成功批量导入 {len(sorted_file_paths)} 张图片")
    
    def handle_batch_drop(self, event):
        """处理批量拖入图片事件
        
        当用户将多张图片拖入批量拖入区域时，按文件名升序排列后分配到各个图片格子中
        """
        import os
        
        # 获取拖入的文件路径列表
        file_paths = self.root.tk.splitlist(event.data)
        
        # 筛选有效的图片文件
        image_files = []
        for file_path in file_paths:
            if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                image_files.append(file_path)
        
        if image_files:
            # 将图片按文件名升序排序
            sorted_files = sorted(image_files, key=lambda x: os.path.basename(x))
            
            # 提示用户确认
            if messagebox.askyesno("确认批量导入", f"将 {len(sorted_files)} 张图片按升序分配到 {self.content_rows} 行图片框，是否确认？"):
                # 遍历图片，分配到对应的行
                for i, file_path in enumerate(sorted_files):
                    if i < self.content_rows:  # 确保不超过最大行数
                        self.load_image(file_path, i)
                
                print(f"成功批量拖入并导入 {len(sorted_files)} 张图片")
                messagebox.showinfo("提示", f"成功导入 {len(sorted_files)} 张图片")
    
    def batch_delete_images(self):
        """批量删除所有图片和相关内容，重置每行数据"""
        # 创建自定义确认对话框
        confirm_window = tk.Toplevel(self.root)
        confirm_window.title(tr("确认批量删除"))
        confirm_window.geometry("350x180")
        confirm_window.resizable(False, False)
        confirm_window.transient(self.root)
        confirm_window.grab_set()
        
        # 计算并设置对话框居中位置
        confirm_window.update_idletasks()
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        dialog_width = confirm_window.winfo_width()
        dialog_height = confirm_window.winfo_height()
        x = root_x + (root_width - dialog_width) // 2
        y = root_y + (root_height - dialog_height) // 2
        confirm_window.geometry(f"+{x}+{y}")
        
        # 使用ttkbootstrap组件和样式
        main_frame = ttk.Frame(confirm_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 提示信息
        message = ttk.Label(main_frame, text=tr("确定要批量删除所有图片和相关内容吗？此操作将重置所有行的数据，不可恢复！"), 
                         font=("宋体", 11), wraplength=300, justify=tk.CENTER)
        message.pack(pady=20)
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        # 确定删除按钮
        def on_confirm():
            confirm_window.destroy()
            # 执行批量删除操作
            self.clear_all_content()
            print("成功批量删除所有图片和相关内容")
            messagebox.showinfo(tr("提示"), tr("成功批量删除所有图片和相关内容"))
        
        confirm_btn = ttk.Button(btn_frame, text=tr("确定删除"), command=on_confirm, style="danger.TButton", width=12)
        confirm_btn.pack(side=tk.LEFT, padx=10)
        
        # 取消按钮
        cancel_btn = ttk.Button(btn_frame, text=tr("取消"), command=confirm_window.destroy, style="secondary.TButton", width=12)
        cancel_btn.pack(side=tk.LEFT, padx=10)
    
    def batch_export_images(self):
        """批量导出所有行的API接口返回的新图片"""
        # 选择导出目录
        export_dir = filedialog.askdirectory(title="选择导出目录")
        if not export_dir:
            return
        
        # 确保导出目录存在
        import os
        os.makedirs(export_dir, exist_ok=True)
        
        exported_count = 0
        error_count = 0
        
        # 遍历所有行的generated_images列表
        if hasattr(self, "generated_images"):
            for row_index in range(len(self.generated_images)):
                row_images = self.generated_images[row_index]
                for img_index in range(len(row_images)):
                    image_path = row_images[img_index]
                    if image_path and os.path.exists(image_path):
                        try:
                            # 构建导出文件名
                            img_name = os.path.basename(image_path)
                            # 添加行号和图片索引，确保文件名唯一
                            base_name, ext = os.path.splitext(img_name)
                            export_name = f"row{row_index+1}_img{img_index+1}_{base_name}{ext}"
                            export_path = os.path.join(export_dir, export_name)
                            
                            # 复制图片
                            import shutil
                            shutil.copy2(image_path, export_path)
                            exported_count += 1
                            print(f"已导出图片: {export_path}")
                        except Exception as e:
                            error_count += 1
                            print(f"导出图片失败: {image_path}, 错误: {e}")
        
        # 显示导出结果
        result_msg = f"批量导出完成\n成功导出: {exported_count}张图片\n失败: {error_count}张图片\n导出目录: {export_dir}"
        messagebox.showinfo("导出完成", result_msg)
    
    def batch_delete_videos(self):
        """批量删除出图显示，清空所有行的图片显示区域，但不删除图片原文件"""
        # 创建自定义确认对话框
        confirm_window = tk.Toplevel(self.root)
        confirm_window.title(tr("确认批量删除出图"))
        confirm_window.geometry("400x200")
        confirm_window.resizable(False, False)
        confirm_window.transient(self.root)
        confirm_window.grab_set()
        
        # 计算并设置对话框居中位置
        confirm_window.update_idletasks()
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        dialog_width = confirm_window.winfo_width()
        dialog_height = confirm_window.winfo_height()
        x = root_x + (root_width - dialog_width) // 2
        y = root_y + (root_height - dialog_height) // 2
        confirm_window.geometry(f"+{x}+{y}")
        
        # 使用ttkbootstrap组件和样式
        main_frame = ttk.Frame(confirm_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 提示信息
        message = ttk.Label(main_frame, text=tr("确定要批量删除所有图片的显示关系吗？\n此操作会清除程序的已生成图片的绑定显示关系，但不会删除png图片原文件。"), 
                         font=("宋体", 11), wraplength=350, justify=tk.CENTER)
        message.pack(pady=20)
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        def delete_all_images_direct(self_inner, row_index):
            """直接删除所有图片显示，不清空确认对话框"""
            try:
                # 检查是否有生成的图片
                if hasattr(self_inner, "generated_images") and row_index < len(self_inner.generated_images):
                    # 获取当前行的图片数量
                    image_count = len(self_inner.generated_images[row_index])
                    
                    # 从后往前逐个删除图片，避免索引错位
                    for idx in range(image_count-1, -1, -1):
                        # 调用每个删除图标的点击事件
                        self_inner.remove_single_image(row_index, idx)
                    
                    print(f"已批量删除第{row_index}行的所有图片显示")
            except Exception as e:
                error_msg = f"删除所有图片显示失败: {e}"
                print(error_msg)
                self_inner.root.after(0, lambda: messagebox.showerror("错误", error_msg))
        
        # 确定删除按钮
        def on_confirm():
            confirm_window.destroy()
            # 执行批量删除出图显示操作
            deleted_count = 0
            
            # 检查所有行的image单选键状态
            if hasattr(self, "image_radio_vars"):
                for row_index in range(len(self.image_radio_vars)):
                    # 如果image单选键是激活状态，则执行对应行的删除所有图片操作
                    if self.image_radio_vars[row_index].get():
                        delete_all_images_direct(self, row_index)
                        deleted_count += 1
            
            print(f"成功批量删除{deleted_count}行的图片显示关系")
            messagebox.showinfo(tr("提示"), f"成功批量删除{deleted_count}行的图片显示关系")
        
        confirm_btn = ttk.Button(btn_frame, text=tr("确定删除"), command=on_confirm, style="danger.TButton", width=12)
        confirm_btn.pack(side=tk.LEFT, padx=10)
        
        # 取消按钮
        cancel_btn = ttk.Button(btn_frame, text=tr("取消"), command=confirm_window.destroy, style="secondary.TButton", width=12)
        cancel_btn.pack(side=tk.LEFT, padx=10)
    
    def clear_all_image_display(self):
        """清空所有行的图片显示区域，但不删除图片原文件"""
        try:
            # 遍历main_frame的所有子组件，找到所有API图片框
            api_frames = []
            for child in self.main_frame.winfo_children():
                # 检查是否为API接口返回的新图片标签框架
                if isinstance(child, ttk.Labelframe) and child.cget("text") == "API接口返回的新图片":
                    api_frames.append(child)
            
            # 清空每个API图片框
            for api_frame in api_frames:
                for inner_child in api_frame.winfo_children():
                    if isinstance(inner_child, ttk.Frame):
                        # 清空原有内容
                        for widget in inner_child.winfo_children():
                            widget.pack_forget()
                        
                        # 恢复初始状态，显示"API返回图片显示区域"提示文字
                        api_prompt = ttk.Label(inner_child, text="API返回图片显示区域", justify=tk.CENTER)
                        api_prompt.pack(expand=True)
            
            print("已清空所有行的图片显示")
        except Exception as e:
            error_msg = f"清空图片显示失败: {e}"
            print(error_msg)
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
    
    def show_image_buttons(self, row_index):
        """显示图片操作按钮
        
        Args:
            row_index: 图片行索引
        """
        # 先关闭之前的按钮
        self.hide_image_buttons()
        
        # 获取图片框
        img_frame = self.img_frames[row_index]
        
        # 创建按钮容器
        self.button_frame = ttk.Frame(img_frame, padding=5, style="Buttons.TFrame")
        self.button_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # 添加查看按钮 - 垂直排列
        view_btn = ttk.Button(self.button_frame, text="查看", command=lambda: self.view_image(row_index))
        view_btn.pack(side=tk.TOP, pady=3, padx=10, fill=tk.X)
        
        # 添加更换按钮 - 垂直排列
        replace_btn = ttk.Button(self.button_frame, text="更换", command=lambda: self.replace_image(row_index))
        replace_btn.pack(side=tk.TOP, pady=3, padx=10, fill=tk.X)
        
        # 添加删除按钮 - 垂直排列
        delete_btn = ttk.Button(self.button_frame, text="删除", command=lambda: self.delete_image(row_index))
        delete_btn.pack(side=tk.TOP, pady=3, padx=10, fill=tk.X)
        
        # 保存当前操作的图片索引
        self.current_image_index = row_index
    
    def hide_image_buttons(self):
        """隐藏图片操作按钮"""
        if hasattr(self, "button_frame") and self.button_frame is not None:
            self.button_frame.destroy()
            delattr(self, "button_frame")
    
    def view_image(self, row_index):
        """查看图片
        
        Args:
            row_index: 图片行索引
        """
        if hasattr(self, "image_paths") and row_index < len(self.image_paths) and self.image_paths[row_index]:
            try:
                # 打开图片
                image = Image.open(self.image_paths[row_index])
                
                # 创建新窗口
                view_window = tk.Toplevel(self.root)
                view_window.title("查看图片")
                view_window.geometry("800x600")
                
                # 计算窗口中心位置
                screen_width = view_window.winfo_screenwidth()
                screen_height = view_window.winfo_screenheight()
                window_width = min(800, screen_width - 100)
                window_height = min(600, screen_height - 100)
                x = (screen_width - window_width) // 2
                y = (screen_height - window_height) // 2
                view_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
                
                # 创建画布并显示图片
                canvas = tk.Canvas(view_window, width=window_width, height=window_height)
                canvas.pack(fill=tk.BOTH, expand=True)
                
                # 调整图片大小以适应窗口
                img_width, img_height = image.size
                ratio = min(window_width / img_width, window_height / img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                resized_image = image.resize((new_width, new_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(resized_image)
                
                # 在画布中心显示图片
                x_offset = (window_width - new_width) // 2
                y_offset = (window_height - new_height) // 2
                canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=photo)
                
                # 保存引用，防止图片被垃圾回收
                view_window.photo = photo
                
            except Exception as e:
                messagebox.showerror("错误", f"无法查看图片: {str(e)}")

    def replace_image(self, row_index):
        """更换图片
        
        Args:
            row_index: 图片行索引
        """
        self.hide_image_buttons()
        self.import_image(row_index)
    
    def delete_image(self, row_index):
        """删除图片
        
        Args:
            row_index: 图片行索引
        """
        # 隐藏操作按钮
        self.hide_image_buttons()
        
        # 恢复提示文字
        self.img_labels[row_index].pack_forget()
        self.img_prompts[row_index].pack(expand=True)
        
        # 清空图片路径
        if hasattr(self, "image_paths") and row_index < len(self.image_paths):
            self.image_paths[row_index] = None
        
        # 清空图片缓存
        if hasattr(self, "image_cache") and row_index < len(self.image_cache):
            self.image_cache[row_index] = None
        
        print(f"已删除图片 {row_index+1}")
    
    def clear_prompt(self, row_index, is_positive=True):
        """清空单个提示词文本框内容（正向或负面）
        
        Args:
            row_index: 图片行索引
            is_positive: 是否是正向提示词
        """
        if is_positive:
            # 清空正向中文提示词文本框
            self.prompt_texts[row_index].delete("1.0", tk.END)
            self.prompt_texts[row_index].insert("1.0", tr("中文提示词"))
            # 调用on_theme_changed方法，让文本框颜色跟随主题
            if hasattr(self.prompt_texts[row_index], "on_theme_changed"):
                self.prompt_texts[row_index].on_theme_changed()
            
            # 清空正向英文翻译文本框
            self.english_texts[row_index].delete("1.0", tk.END)
            self.english_texts[row_index].insert("1.0", tr("英文翻译"))
            # 调用on_theme_changed方法，让文本框颜色跟随主题
            if hasattr(self.english_texts[row_index], "on_theme_changed"):
                self.english_texts[row_index].on_theme_changed()
        else:
            # 清空负面中文提示词文本框
            self.negative_prompt_texts[row_index].delete("1.0", tk.END)
            self.negative_prompt_texts[row_index].insert("1.0", tr("中文负面提示词"))
            # 调用on_theme_changed方法，让文本框颜色跟随主题
            if hasattr(self.negative_prompt_texts[row_index], "on_theme_changed"):
                self.negative_prompt_texts[row_index].on_theme_changed()
            
            # 清空负面英文翻译文本框
            self.negative_english_texts[row_index].delete("1.0", tk.END)
            self.negative_english_texts[row_index].insert("1.0", tr("英文负面翻译"))
            # 调用on_theme_changed方法，让文本框颜色跟随主题
            if hasattr(self.negative_english_texts[row_index], "on_theme_changed"):
                self.negative_english_texts[row_index].on_theme_changed()
        
        print(f"已清空{'正向' if is_positive else '负面'}提示词 {row_index+1}")
    
    def clear_prompts(self, row_index):
        """清空提示词文本框内容
        
        Args:
            row_index: 图片行索引
        """
        # 清空中文提示词文本框
        self.prompt_texts[row_index].delete("1.0", tk.END)
        self.prompt_texts[row_index].insert("1.0", tr("中文提示词"))
        # 调用on_theme_changed方法，让文本框颜色跟随主题
        if hasattr(self.prompt_texts[row_index], "on_theme_changed"):
            self.prompt_texts[row_index].on_theme_changed()
        
        # 清空英文翻译文本框
        self.english_texts[row_index].delete("1.0", tk.END)
        self.english_texts[row_index].insert("1.0", tr("英文翻译"))
        # 调用on_theme_changed方法，让文本框颜色跟随主题
        if hasattr(self.english_texts[row_index], "on_theme_changed"):
            self.english_texts[row_index].on_theme_changed()
        
        # 清空中文负面提示词文本框
        self.negative_prompt_texts[row_index].delete("1.0", tk.END)
        self.negative_prompt_texts[row_index].insert("1.0", tr("中文负面提示词"))
        # 调用on_theme_changed方法，让文本框颜色跟随主题
        if hasattr(self.negative_prompt_texts[row_index], "on_theme_changed"):
            self.negative_prompt_texts[row_index].on_theme_changed()
        
        # 清空英文负面翻译文本框
        self.negative_english_texts[row_index].delete("1.0", tk.END)
        self.negative_english_texts[row_index].insert("1.0", tr("英文负面翻译"))
        # 调用on_theme_changed方法，让文本框颜色跟随主题
        if hasattr(self.negative_english_texts[row_index], "on_theme_changed"):
            self.negative_english_texts[row_index].on_theme_changed()
        
        print(f"已清空提示词 {row_index+1}")
    
    def clear_all_content(self):
        """清空所有内容，用于导入项目前的准备"""
        # 清空图片
        if hasattr(self, "image_paths"):
            self.image_paths = [None] * self.content_rows
        
        if hasattr(self, "image_cache"):
            self.image_cache = [None] * self.content_rows
        
        # 清空所有行的图片显示
        for row_index in range(self.content_rows):
            # 清空提示词
            if hasattr(self, "prompt_texts") and row_index < len(self.prompt_texts):
                self.prompt_texts[row_index].delete("1.0", tk.END)
                self.prompt_texts[row_index].insert("1.0", "中文提示词")
                # 调用on_theme_changed方法，让文本框颜色跟随主题
                if hasattr(self.prompt_texts[row_index], "on_theme_changed"):
                    self.prompt_texts[row_index].on_theme_changed()
                # 重置修改标志
                self.prompt_texts[row_index].edit_modified(False)
            
            if hasattr(self, "english_texts") and row_index < len(self.english_texts):
                self.english_texts[row_index].delete("1.0", tk.END)
                self.english_texts[row_index].insert("1.0", "英文翻译")
                # 调用on_theme_changed方法，让文本框颜色跟随主题
                if hasattr(self.english_texts[row_index], "on_theme_changed"):
                    self.english_texts[row_index].on_theme_changed()
                # 重置修改标志
                self.english_texts[row_index].edit_modified(False)
            
            # 清空中文负面提示词文本框
            if hasattr(self, "negative_prompt_texts") and row_index < len(self.negative_prompt_texts):
                self.negative_prompt_texts[row_index].delete("1.0", tk.END)
                self.negative_prompt_texts[row_index].insert("1.0", "中文负面提示词")
                # 调用on_theme_changed方法，让文本框颜色跟随主题
                if hasattr(self.negative_prompt_texts[row_index], "on_theme_changed"):
                    self.negative_prompt_texts[row_index].on_theme_changed()
                # 重置修改标志
                self.negative_prompt_texts[row_index].edit_modified(False)
            
            # 清空英文负面提示词文本框
            if hasattr(self, "negative_english_texts") and row_index < len(self.negative_english_texts):
                self.negative_english_texts[row_index].delete("1.0", tk.END)
                self.negative_english_texts[row_index].insert("1.0", "英文负面翻译")
                # 调用on_theme_changed方法，让文本框颜色跟随主题
                if hasattr(self.negative_english_texts[row_index], "on_theme_changed"):
                    self.negative_english_texts[row_index].on_theme_changed()
                # 重置修改标志
                self.negative_english_texts[row_index].edit_modified(False)
            
            # 清空图片生成显示
            if hasattr(self, "api_image_frames") and row_index < len(self.api_image_frames):
                api_frame = self.api_image_frames[row_index]
                for widget in api_frame.winfo_children():
                    widget.pack_forget()
                
                # 显示默认文本
                default_label = ttk.Label(api_frame, text="API返回图片显示区域", justify=tk.CENTER)
                default_label.pack(expand=True)
        
        # 清空生成的图片记录
        if hasattr(self, "generated_images"):
            self.generated_images = [[] for _ in range(self.content_rows)]
        
        print("已清空所有内容")
    
    def batch_generate_images(self, row_index):
        """批量生成图片
        
        Args:
            row_index: 图片行索引
        """
        # 获取重复生成次数
        count_str = self.batch_generate_count_list[row_index].get()
        try:
            count = int(count_str)
            # 检查是否在1-48范围内
            if 1 <= count <= 48:
                # 显示确认弹窗
                confirm_msg = f"是否执行批量生成{count}张图片的任务?"
                result = messagebox.askyesno("批量生成确认", confirm_msg)
                if result:
                    # 获取标志位状态
                    has_image_load = getattr(self, 'has_image_load', False)
                    has_positive_prompt = getattr(self, 'has_positive_prompt', False)
                    has_negative_prompt = getattr(self, 'has_negative_prompt', False)
                    
                    # 根据规则类型进行预检查
                    # 规则a：无提示词的图生图模式 - 检查图片
                    if has_image_load and not has_positive_prompt and not has_negative_prompt:
                        if not hasattr(self, "image_paths") or row_index >= len(self.image_paths) or not self.image_paths[row_index]:
                            messagebox.showwarning("提示", "请导入图片再进行生图任务")
                            return
                    
                    # 规则b：有正面负面提示词的文生图模式 - 检查两个提示词
                    elif has_positive_prompt and has_negative_prompt and not has_image_load:
                        en_text = ""
                        if row_index < len(self.english_texts):
                            en_text = self.english_texts[row_index].get("1.0", tk.END).strip()
                        if not en_text or en_text == "英文翻译":
                            messagebox.showwarning("提示", "请输入正向提示词再进行生图任务")
                            return
                        
                        negative_en_text = ""
                        if hasattr(self, 'negative_english_texts') and row_index < len(self.negative_english_texts):
                            negative_en_text = self.negative_english_texts[row_index].get("1.0", tk.END).strip()
                        if not negative_en_text or negative_en_text == "英文负面翻译":
                            messagebox.showwarning("提示", "请输入负面提示词再进行生图任务")
                            return
                    
                    # 规则c：有正面提示词的文生图模式 - 检查正向提示词
                    elif has_positive_prompt and not has_negative_prompt and not has_image_load:
                        en_text = ""
                        if row_index < len(self.english_texts):
                            en_text = self.english_texts[row_index].get("1.0", tk.END).strip()
                        if not en_text or en_text == "英文翻译":
                            messagebox.showwarning("提示", "请输入正向提示词再进行生图任务")
                            return
                    
                    # 兼容模式：图生图+提示词
                    elif has_image_load and has_positive_prompt:
                        if not hasattr(self, "image_paths") or row_index >= len(self.image_paths) or not self.image_paths[row_index]:
                            messagebox.showwarning("提示", "请导入图片再进行生图任务")
                            return
                        en_text = ""
                        if row_index < len(self.english_texts):
                            en_text = self.english_texts[row_index].get("1.0", tk.END).strip()
                        if not en_text or en_text == "英文翻译":
                            messagebox.showwarning("提示", "请输入正向提示词再进行生图任务")
                            return
                    
                    else:
                        messagebox.showwarning("提示", "未匹配任何生图规则，无法执行生图任务")
                        return
                    
                    # 用户点击确认，开始批量生成
                    for i in range(count):
                        # 调用生成图片(单个)方法，传入批量模式参数
                        self.generate_image_single(row_index, is_batch=True, batch_index=i)
            else:
                # 显示错误提示
                messagebox.showerror("错误", "重复生成次数必须在1-48之间")
        except ValueError:
            # 显示错误提示
            messagebox.showerror("错误", "请输入有效的数字")
    
    def generate_image_single(self, row_index, is_batch=False, batch_index=0, callback=None):
        """生成单个图片
        
        Args:
            row_index: 图片行索引
            is_batch: 是否为批量生成模式
            batch_index: 批量生成中的索引位置
            callback: 图片生成完成后的回调函数，接收success参数
        """
        import requests
        import json
        import time
        import os
        import threading
        import shutil
        from PIL import Image, ImageTk, ImageDraw
        
        # 添加详细日志
        print(f"=== 开始执行生成图片(单个)按钮 ===")
        print(f"行索引: {row_index}")
        print(f"是否批量模式: {is_batch}")
        print(f"批量索引: {batch_index}")
        print(f"是否有回调: {callback is not None}")
        
        # ========== 生图规则验证 ==========
        # 获取当前工作流的功能模块结构
        sections_str = ""
        if hasattr(self, 'ini_sections_var'):
            sections_str = self.ini_sections_var.get()
        print(f"当前功能模块结构: {sections_str}")
        
        # 获取标志位状态
        has_image_load = getattr(self, 'has_image_load', False)
        has_positive_prompt = getattr(self, 'has_positive_prompt', False)
        has_negative_prompt = getattr(self, 'has_negative_prompt', False)
        
        print(f"标志位状态: has_image_load={has_image_load}, has_positive_prompt={has_positive_prompt}, has_negative_prompt={has_negative_prompt}")
        
        # 定义显示红色警告的辅助函数
        def show_validation_error():
            """在API返回图片显示区域显示红色警告文字"""
            if not is_batch:
                api_frame = self.api_image_frames[row_index]
                # 清空原有内容
                for widget in api_frame.winfo_children():
                    widget.pack_forget()
                # 显示红色警告文字
                warning_label = ttk.Label(api_frame, 
                                         text="不符合图片生成条件,请再次检查",
                                         foreground="red",
                                         justify=tk.CENTER)
                warning_label.pack(expand=True, pady=20)
            if callback:
                callback(False)
            print(f"=== 生成图片(单个)按钮执行结束 ===")
        
        # 根据功能模块结构判断当前规则类型并进行验证
        validation_passed = False
        
        # 规则a：无提示词的图生图模式
        # 功能模块结构：[图片载入],[图片尺寸高度],[图片尺寸宽度],[K采样步值],[图片输出]
        # 检查逻辑：检查对应行图A框体是否已经导入图片
        if has_image_load and not has_positive_prompt and not has_negative_prompt:
            print(f"匹配规则a：无提示词的图生图模式")
            print(f"1. 检查图片是否已加载:")
            
            # 检查图片是否已导入
            image_valid = (hasattr(self, "image_paths") and 
                          row_index < len(self.image_paths) and 
                          self.image_paths[row_index] and 
                          os.path.exists(self.image_paths[row_index]))
            
            print(f"   - 图片路径: {self.image_paths[row_index] if hasattr(self, 'image_paths') and row_index < len(self.image_paths) else 'None'}")
            print(f"   - 图片检查结果: {'成功' if image_valid else '失败'}")
            
            if not image_valid:
                show_validation_error()
                return
            
            validation_passed = True
        
        # 规则b：有正面负面提示词的文生图模式
        # 功能模块结构：[正向提示词],[负面提示词],[K采样步值],[图片尺寸高度],[图片尺寸宽度],[图片输出]
        # 检查逻辑：检查对应行的正向提示词英文翻译文本框和负面提示词英文翻译文本框是否为空
        elif has_positive_prompt and has_negative_prompt and not has_image_load:
            print(f"匹配规则b：有正面负面提示词的文生图模式")
            print(f"1. 检查正向提示词英文翻译:")
            
            # 获取正向英文提示词
            en_text = ""
            if row_index < len(self.english_texts):
                en_text = self.english_texts[row_index].get("1.0", tk.END).strip()
            
            positive_valid = en_text and en_text != "英文翻译"
            print(f"   - 正向英文提示词: '{en_text}'")
            print(f"   - 正向提示词检查结果: {'成功' if positive_valid else '失败'}")
            
            if not positive_valid:
                show_validation_error()
                return
            
            print(f"2. 检查负面提示词英文翻译:")
            
            # 获取负面英文提示词
            negative_en_text = ""
            if hasattr(self, 'negative_english_texts') and row_index < len(self.negative_english_texts):
                negative_en_text = self.negative_english_texts[row_index].get("1.0", tk.END).strip()
            
            negative_valid = negative_en_text and negative_en_text != "英文负面翻译"
            print(f"   - 负面英文提示词: '{negative_en_text}'")
            print(f"   - 负面提示词检查结果: {'成功' if negative_valid else '失败'}")
            
            if not negative_valid:
                show_validation_error()
                return
            
            validation_passed = True
        
        # 规则c：有正面提示词的文生图模式
        # 功能模块结构：[正向提示词],[K采样步值],[图片尺寸高度],[图片尺寸宽度],[图片输出]
        # 检查逻辑：检查对应行的正向提示词英文翻译文本框是否为空
        elif has_positive_prompt and not has_negative_prompt and not has_image_load:
            print(f"匹配规则c：有正面提示词的文生图模式")
            print(f"1. 检查正向提示词英文翻译:")
            
            # 获取正向英文提示词
            en_text = ""
            if row_index < len(self.english_texts):
                en_text = self.english_texts[row_index].get("1.0", tk.END).strip()
            
            positive_valid = en_text and en_text != "英文翻译"
            print(f"   - 正向英文提示词: '{en_text}'")
            print(f"   - 正向提示词检查结果: {'成功' if positive_valid else '失败'}")
            
            if not positive_valid:
                show_validation_error()
                return
            
            validation_passed = True
        
        # 兼容旧逻辑：图生图模式（有图片载入和正向提示词）
        elif has_image_load and has_positive_prompt:
            print(f"匹配兼容模式：图生图模式（有图片载入和正向提示词）")
            
            # 检查图片是否已导入
            print(f"1. 检查图片是否已加载:")
            image_valid = (hasattr(self, "image_paths") and 
                          row_index < len(self.image_paths) and 
                          self.image_paths[row_index] and 
                          os.path.exists(self.image_paths[row_index]))
            
            print(f"   - 图片路径: {self.image_paths[row_index] if hasattr(self, 'image_paths') and row_index < len(self.image_paths) else 'None'}")
            print(f"   - 图片检查结果: {'成功' if image_valid else '失败'}")
            
            if not image_valid:
                show_validation_error()
                return
            
            # 检查正向英文提示词
            print(f"2. 检查正向提示词英文翻译:")
            en_text = ""
            if row_index < len(self.english_texts):
                en_text = self.english_texts[row_index].get("1.0", tk.END).strip()
            
            positive_valid = en_text and en_text != "英文翻译"
            print(f"   - 正向英文提示词: '{en_text}'")
            print(f"   - 正向提示词检查结果: {'成功' if positive_valid else '失败'}")
            
            if not positive_valid:
                show_validation_error()
                return
            
            # 如果有负面提示词，也需要检查
            if has_negative_prompt:
                print(f"3. 检查负面提示词英文翻译:")
                negative_en_text = ""
                if hasattr(self, 'negative_english_texts') and row_index < len(self.negative_english_texts):
                    negative_en_text = self.negative_english_texts[row_index].get("1.0", tk.END).strip()
                
                negative_valid = negative_en_text and negative_en_text != "英文负面翻译"
                print(f"   - 负面英文提示词: '{negative_en_text}'")
                print(f"   - 负面提示词检查结果: {'成功' if negative_valid else '失败'}")
                
                if not negative_valid:
                    show_validation_error()
                    return
            
            validation_passed = True
        
        else:
            # 未匹配任何规则，显示错误
            print(f"未匹配任何生图规则，无法执行生图任务")
            show_validation_error()
            return
        
        if not validation_passed:
            print(f"验证未通过")
            show_validation_error()
            return
        
        print(f"所有验证通过，继续执行生图任务")
        
        # ========== 获取英文提示词（用于后续API调用） ==========
        en_text = ""
        if has_positive_prompt and row_index < len(self.english_texts):
            en_text = self.english_texts[row_index].get("1.0", tk.END).strip()
        
        # 配置参数
        # 1. 确定工作流类型
        workflow_type = "image_to_image" if has_image_load else "text_to_image"
        print(f"   - 工作流类型: {workflow_type}")
        
        # 2. 根据工作流类型设置不同的参数
        INPUT_IMAGE_PATH = self.image_paths[row_index] if hasattr(self, 'image_paths') and row_index < len(self.image_paths) else ""
        PROMPT = en_text
        COMFYUI_URL = self.COMFYUI_URL
        TIMEOUT = self.TIMEOUT
        WORKFLOW_PATH = self.WORKFLOW_PATH
        IMAGE_SAVE_DIR = self.IMAGE_SAVE_DIR
        
        # 3. 确定使用的生图规则配置
        config_section = "ImageToImage_K_Generation"
        if workflow_type == "text_to_image":
            config_section = "textToImage_K_Generation"
        
        print(f"   - 使用的配置节: {config_section}")
        
        # 确保保存目录存在
        os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)
        
        # 显示生成中的状态
        api_frame = self.api_image_frames[row_index]
        
        # 检查是否已经有生成的图片框架
        has_existing_images = False
        existing_images_frame = None
        
        # 查找现有的images_frame
        for widget in api_frame.winfo_children():
            if isinstance(widget, ttk.Frame):
                # 检查是否是之前创建的images_frame（包含图片）
                has_images = any(isinstance(child, ttk.Frame) for child in widget.winfo_children())
                if has_images:
                    existing_images_frame = widget
                    has_existing_images = True
                    break
        
        if has_existing_images:
            # 已有图片，在右侧添加生成提示
            print(f"已有图片，在右侧添加生成提示")
            # 创建一个生成中的容器
            generating_container = ttk.Frame(existing_images_frame, padding=5, relief="solid", borderwidth=1)
            generating_container.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5, pady=5)
            
            # 显示生成中的信息，确保居中
            generating_label = ttk.Label(generating_container, text=tr("正在生成图片..."), anchor=tk.CENTER)
            generating_label.pack(expand=True, pady=10)
        else:
            # 没有现有图片，显示在中间
            print(f"没有现有图片，显示在中间")
            # 清空原有内容
            for widget in api_frame.winfo_children():
                widget.pack_forget()
            
            # 创建一个横向排列的框架
            images_frame = ttk.Frame(api_frame)
            images_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
            
            # 显示生成中的信息
            generating_container = ttk.Frame(images_frame, padding=5, relief="solid", borderwidth=1)
            generating_container.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5, pady=5)
            
            generating_label = ttk.Label(generating_container, text=tr("正在生成图片..."), anchor=tk.CENTER)
            generating_label.pack(expand=True, pady=10)
        
        # 启动该行的计时器
        self.start_row_timer(row_index)
        
        # 设置生成状态为"Generating"
        self.generation_status = "Generating"
        # 设置总计数
        self.total_count = 1  # 单个图片生成，总计数为1
        self.generated_count = 0  # 初始生成计数为0
        
        # 立即更新API框体标题为Generating状态
        if hasattr(self, "api_frames") and row_index < len(self.api_frames):
            api_label_frame = self.api_frames[row_index]
            # 保留原有标题，只更新样式为生成中
            current_text = api_label_frame.cget("text")
            # 如果当前标题是初始状态，才设置为生成中
            if "(none)" in current_text:
                status_text = f"{tr('API返回图片')} ({tr('生成中')})"
                api_label_frame.configure(text=status_text, style="StatusGenerating.TLabelframe")
            else:
                # 保留原有标题，只更新样式
                api_label_frame.configure(style="StatusGenerating.TLabelframe")
        
        # 定义一个函数，用于在图片生成失败时调用，确保计时器停止
        def handle_image_failure():
            # 停止该行的计时器
            self.stop_row_timer(row_index)
            if callback:
                callback(False)
        
        # 图片生成的后台线程函数
        def generate_image_thread():
            # 加载工作流
            def load_workflow():
                try:
                    with open(WORKFLOW_PATH, 'r', encoding='utf-8') as f:
                        workflow = json.load(f)
                    # 工作流文件已经是正确的API格式，直接返回
                    return workflow
                except Exception as e:
                    error_msg = f"加载工作流失败: {e}"
                    print(error_msg)
                    def show_error():
                        # 清空原有内容，移除"正在生成图片.."
                        for widget in api_frame.winfo_children():
                            widget.pack_forget()
                        # 显示工作流加载错误提示，红色字体
                        error_label = ttk.Label(api_frame, 
                                               text=f"工作流加载失败: {error_msg}",
                                               foreground="red",
                                               justify=tk.CENTER)
                        error_label.pack(expand=True, pady=20)
                        # 停止计时器
                        self.stop_row_timer(row_index)
                    self.root.after(0, show_error)
                    if callback:
                        callback(False)
                    return None
            
            # 修改工作流
            def modify_workflow(workflow):
                # 导入必要的模块
                import os
                
                # 重置图片输出节点ID，防止使用上一次工作流的旧值
                self.image_output_node_id = None
                print(f"重置图片输出节点ID: {self.image_output_node_id}")
                
                # 确定使用的生图规则配置
                ini_path = os.path.splitext(self.WORKFLOW_PATH)[0] + ".ini"
                config = MultiConfigParser()
                config.read(ini_path, encoding='utf-8')
                
                workflow_type = "image_to_image"
                # 从setting.ini中获取当前使用的生图规则
                image_type_config = self.config.get("ImageToImage_K_Generation", "type", fallback="")
                text_type_config = self.config.get("textToImage_K_Generation", "type", fallback="")
                
                # 检查当前工作流是否匹配文生图配置
                if "[正向提示词]" in text_type_config and "[图片载入]" not in text_type_config:
                    workflow_type = "text_to_image"
                
                config_section = "ImageToImage_K_Generation"
                if workflow_type == "text_to_image":
                    config_section = "textToImage_K_Generation"
                
                print(f"   - 修改工作流使用的配置节: {config_section}")
                # 生成唯一的随机种子，防止ComfyUI缓存
                unique_seed = int(time.time() * 1000) % (2**32)
                
                # 工作流文件直接是节点字典
                workflow_nodes = workflow
                
                # 读取INI配置文件获取节点映射 - 使用JSON到INI的绑定规则：相同文件名，不同扩展名
                import os
                ini_path = os.path.splitext(WORKFLOW_PATH)[0] + ".ini"
                node_mapping = {}
                
                # 添加详细的INI和JSON文件信息日志
                print(f"=== API调用配置信息 ===")
                print(f"当前使用的JSON文件: {WORKFLOW_PATH}")
                print(f"当前使用的INI文件: {ini_path}")
                
                # 读取并记录INI文件关键信息
                if os.path.exists(ini_path):
                    # 使用支持重复section的MultiConfigParser
                    config = MultiConfigParser()
                    config.read(ini_path, encoding='utf-8')
                    print(f"INI文件关键变量信息:")
                    # 查找功能模块与节点位置关联section
                    for i, section in enumerate(config.sections()):
                        if section == '功能模块与节点位置关联':
                            node_mapping = config._section_data[i]
                            for key, value in node_mapping.items():
                                print(f"  - {key}: {value}")
                            break
                    
                    # 读取其他可能的配置节
                    for i, section in enumerate(config.sections()):
                        if section != '功能模块与节点位置关联':
                            print(f"{section}:")
                            for key, value in config._section_data[i].items():
                                print(f"  - {key}: {value}")
                else:
                    print(f"警告: INI文件 {ini_path} 不存在")
                
                # 记录JSON文件的API信息
                print(f"JSON文件API信息:")
                print(f"  - 工作流节点数量: {len(workflow_nodes)}")
                # 统计不同类型的节点数量
                node_types = {}
                for node_id, node_data in workflow_nodes.items():
                    class_type = node_data.get('class_type', 'Unknown')
                    node_types[class_type] = node_types.get(class_type, 0) + 1
                
                print(f"  - 节点类型统计:")
                for class_type, count in node_types.items():
                    print(f"    * {class_type}: {count}")
                
                # INI文件已经在上面读取过了，node_mapping已经初始化
                
                # 获取节点ID，使用默认值作为后备
                image_input_node = node_mapping.get('image_input_node', '97')
                cn_prompt_node = node_mapping.get('cn_prompt_node', '93')
                image_display_node = node_mapping.get('image_display_node', '118')
                generate_single_node = node_mapping.get('generate_single_node', '98')
                k_sampler_step_node_1 = node_mapping.get('k_sampler_step_node_1', '85')
                k_sampler_step_node_2 = node_mapping.get('k_sampler_step_node_2', '86')
                image_height_node = node_mapping.get('image_height_node', '98')
                image_width_node = node_mapping.get('image_width_node', '98')
                cn_negative_prompt_node = node_mapping.get('cn_negative_prompt_node', '89')
                
                # 获取当前行的图片参数
                # 从配置文件获取默认值，根据工作流类型选择配置节
                k_sampler_steps = self.config.get(config_section, "default_k_sampler_steps", fallback="4")  # 默认值
                image_height = self.config.get(config_section, "default_image_height", fallback="832")  # 默认值
                image_width = self.config.get(config_section, "default_image_width", fallback="480")  # 默认值
                
                # 确保索引有效
                if hasattr(self, "k_sampler_steps_list") and row_index < len(self.k_sampler_steps_list):
                    k_sampler_steps = self.k_sampler_steps_list[row_index].get()
                if hasattr(self, "image_height_list") and row_index < len(self.image_height_list):
                    image_height = self.image_height_list[row_index].get()
                if hasattr(self, "image_width_list") and row_index < len(self.image_width_list):
                    image_width = self.image_width_list[row_index].get()
                
                # 收集所有修改过的节点ID
                modified_nodes = set()
                
                # 读取并处理INI文件中的所有section，根据section类型和参数键名修改对应参数
                config = MultiConfigParser()
                config.read(ini_path, encoding='utf-8')
                
                # 遍历所有section
                for i, section in enumerate(config.sections()):
                    section_data = config._section_data[i]
                    
                    # 跳过功能模块与节点位置关联section
                    if section == '功能模块与节点位置关联':
                        continue
                    
                    # 检查是否包含必要的参数
                    if all(key in section_data for key in ['数据节点路径', '参数键名']):
                        data_path = section_data['数据节点路径']
                        param_key = section_data['参数键名']
                        
                        # 解析数据节点路径，提取节点ID
                        import re
                        # 支持数字和字母组合的节点ID
                        node_id_match = re.search(r'\["([\w\d]+)"\]', data_path)
                        if node_id_match:
                            node_id = node_id_match.group(1)
                            
                            if node_id in workflow_nodes:
                                # 检查section的变量绑定是否在允许的索引名列表中
                                variable_binding = section_data.get('变量绑定', '')
                                if variable_binding:
                                    # 检查变量绑定是否在允许的索引名列表中
                                    binding_with_brackets = f"[{variable_binding}]"
                                    if binding_with_brackets not in self.allowed_index_names:
                                        print(f"跳过未知的变量绑定: {variable_binding} (允许的索引名: {self.allowed_index_names})")
                                        continue
                                
                                # 根据section类型确定要使用的参数值
                                param_value = None
                                
                                # 匹配section类型并设置对应值
                                # 从配置中读取section名称映射
                                k_sampler_section = self.config.get(config_section, "k_sampler_section", fallback="K采样步值")
                                image_width_section = self.config.get(config_section, "image_width_section", fallback="图片尺寸宽度")
                                image_height_section = self.config.get(config_section, "image_height_section", fallback="图片尺寸高度")
                                positive_prompt_section = self.config.get(config_section, "positive_prompt_section", fallback="正向提示词")
                                negative_prompt_section = self.config.get(config_section, "negative_prompt_section", fallback="负面提示词")
                                image_load_section = self.config.get(config_section, "image_load_section", fallback="图片载入")
                                image_output_section = self.config.get(config_section, "image_output_section", fallback="图片输出")
                                
                                if section.startswith(k_sampler_section):
                                    param_value = int(k_sampler_steps)
                                elif section.startswith(image_width_section):
                                    param_value = int(image_width)
                                elif section.startswith(image_height_section):
                                    param_value = int(image_height)
                                elif section.startswith(positive_prompt_section):
                                    param_value = PROMPT
                                elif section.startswith(negative_prompt_section):
                                    # 负面提示词需要特殊处理
                                    negative_prompt = ""
                                    if hasattr(self, 'has_negative_prompt') and self.has_negative_prompt and hasattr(self, 'negative_english_texts') and row_index < len(self.negative_english_texts):
                                        negative_prompt = self.negative_english_texts[row_index].get("1.0", tk.END).strip()
                                    if negative_prompt:
                                        param_value = negative_prompt
                                elif section.startswith(image_load_section):
                                    # LoadImage节点的image参数需要完整路径，而不仅仅是文件名
                                    # 使用完整的图片路径
                                    param_value = INPUT_IMAGE_PATH
                                elif section.startswith(image_output_section):
                                    # 图片输出节点的filename_prefix参数，使用INI文件中定义的参数值
                                    # 从INI文件中读取实际的参数值
                                    param_value = section_data.get('参数值', 'wyAI-ComfyUI')
                                    # 记录图片输出节点ID，用于后续图片选择
                                    old_node_id = getattr(self, 'image_output_node_id', None)
                                    self.image_output_node_id = node_id
                                    print(f"记录图片输出节点ID: {node_id} (section: {section}, 旧值: {old_node_id})")
                                    print(f"   - 数据节点路径: {data_path}")
                                    print(f"   - 参数值: {param_value}")
                                
                                # 如果找到了对应的参数值，则修改工作流
                                if param_value is not None:
                                    # 修改工作流中的参数
                                    if param_key in workflow_nodes[node_id]["inputs"]:
                                        old_value = workflow_nodes[node_id]["inputs"][param_key]
                                        workflow_nodes[node_id]["inputs"][param_key] = param_value
                                        print(f"修改节点 {node_id} 的{param_key}为: {param_value} (原值: {old_value})")
                                        modified_nodes.add(node_id)
                                    else:
                                        print(f"警告: 节点 {node_id} 的inputs中不存在参数 {param_key}")
                
                for node_id, node_data in workflow_nodes.items():
                    
                    # 为所有节点添加唯一的noise_seed，防止缓存
                    if "inputs" in node_data:
                        # 检查是否有seed或noise_seed参数
                        if "seed" in node_data["inputs"]:
                            workflow_nodes[node_id]["inputs"]["seed"] = unique_seed
                            print(f"节点 {node_id} 添加唯一seed: {unique_seed}")
                            modified_nodes.add(node_id)
                        elif "noise_seed" in node_data["inputs"]:
                            workflow_nodes[node_id]["inputs"]["noise_seed"] = unique_seed
                            print(f"节点 {node_id} 添加唯一noise_seed: {unique_seed}")
                            modified_nodes.add(node_id)
                    
                    # 修改所有K采样器(高级)节点的步数
                    if node_data["class_type"] == "KSamplerAdvanced":
                        try:
                            # 获取K采样器步数输入
                            steps = int(k_sampler_steps)
                            
                            # 获取原始参数
                            original_steps = node_data["inputs"].get("steps", 4)
                            original_start = node_data["inputs"].get("start_at_step", 0)
                            original_end = node_data["inputs"].get("end_at_step", original_steps)
                            
                            # 计算原始百分比位置，保持相同的相对位置
                            if original_steps > 0:
                                start_ratio = original_start / original_steps if original_start < original_steps else 0
                                end_ratio = original_end / original_steps if original_end <= original_steps else 1
                            else:
                                start_ratio = 0
                                end_ratio = 1
                            
                            # 计算新的start_at_step和end_at_step，保持原始比例
                            new_start = int(steps * start_ratio)
                            new_end = int(steps * end_ratio)
                            
                            # 确保新值合理
                            new_start = max(0, new_start)
                            new_end = min(steps, max(new_start, new_end))
                            
                            # 只修改必要的参数
                            # 使用配置中的参数名
                            step_param = node_mapping.get('k_sampler_step_param_1', 'steps')
                            workflow_nodes[node_id]["inputs"][step_param] = steps
                            # 只修改steps参数，不修改其他参数
                            
                            print(f"修改K采样器(高级)节点 {node_id} 的{step_param}为 {steps}")
                            modified_nodes.add(node_id)
                        except ValueError:
                            # 如果输入无效，保持原始值
                            print(f"K采样器步数输入无效，节点 {node_id} 保持原始值")
                
                # 修改Wan图像到图片的尺寸
                if generate_single_node in workflow_nodes:
                    try:
                        # 获取图片尺寸输入
                        # 从UI获取：宽 = image_width，高 = image_height
                        # API中：width = UI中的宽，height = UI中的高
                        ui_width = int(image_width)
                        ui_height = int(image_height)
                        # 使用配置中的参数名
                        width_param = node_mapping.get('image_width_param', 'width')
                        height_param = node_mapping.get('image_height_param', 'height')
                        # 直接使用UI值
                        workflow_nodes[generate_single_node]["inputs"][width_param] = ui_width
                        workflow_nodes[generate_single_node]["inputs"][height_param] = ui_height
                        # 从配置获取参数值


                        # 修改batch_size，防止批量生成导致的缓存问题

                        # 修改length参数，增加微小变化防止缓存

                        print(f"修改Wan图像到图片节点 {generate_single_node} 的尺寸：API width={ui_width}, API height={ui_height} (UI宽={ui_width}, UI高={ui_height})")
                        modified_nodes.add(generate_single_node)
                    
                    except ValueError:
                        # 如果输入无效，使用配置中的默认值
                        default_width = int(node_mapping.get('default_width', 832))
                        default_height = int(node_mapping.get('default_height', 480))


                        workflow_nodes[generate_single_node]["inputs"]["width"] = default_width
                        workflow_nodes[generate_single_node]["inputs"]["height"] = default_height


                        print(f"图片尺寸输入无效，使用默认值 width={default_width}, height={default_height}")
                        modified_nodes.add(generate_single_node)
                
                # 修改所有EmptyLatentImage节点的尺寸
                ui_width = int(image_width)
                ui_height = int(image_height)
                steps = int(k_sampler_steps)
                
                # 1. 查找并修改所有EmptyLatentImage节点的尺寸
                for node_id, node_data in workflow_nodes.items():
                    if node_data["class_type"] == "EmptyLatentImage":
                        # 修改EmptyLatentImage节点的尺寸
                        workflow_nodes[node_id]["inputs"]["width"] = ui_width
                        workflow_nodes[node_id]["inputs"]["height"] = ui_height
                        print(f"修改EmptyLatentImage节点 {node_id} 的尺寸：width={ui_width}, height={ui_height}")
                        modified_nodes.add(node_id)
                
                # 2. 确保K采样器步数被正确应用到所有KSampler节点
                for node_id, node_data in workflow_nodes.items():
                    if node_data["class_type"] in ["KSampler", "KSamplerAdvanced"]:
                        workflow_nodes[node_id]["inputs"]["steps"] = steps
                        print(f"修改{node_data['class_type']}节点 {node_id} 的steps为 {steps}")
                        modified_nodes.add(node_id)
                
                # 修改所有相关节点的尺寸和参数
                ui_width = int(image_width)
                ui_height = int(image_height)
                steps = int(k_sampler_steps)
                
                # 1. 查找并修改所有EmptyLatentImage节点的尺寸
                for node_id, node_data in workflow_nodes.items():
                    if node_data["class_type"] == "EmptyLatentImage":
                        # 修改EmptyLatentImage节点的尺寸
                        workflow_nodes[node_id]["inputs"]["width"] = ui_width
                        workflow_nodes[node_id]["inputs"]["height"] = ui_height
                        print(f"修改EmptyLatentImage节点 {node_id} 的尺寸：width={ui_width}, height={ui_height}")
                        modified_nodes.add(node_id)
                
                # 2. 确保K采样器步数被正确应用到所有KSampler节点
                for node_id, node_data in workflow_nodes.items():
                    if node_data["class_type"] in ["KSampler", "KSamplerAdvanced"]:
                        workflow_nodes[node_id]["inputs"]["steps"] = steps
                        print(f"修改{node_data['class_type']}节点 {node_id} 的steps为 {steps}")
                        modified_nodes.add(node_id)
                
                # 打印修改后的工作流节点的完整信息，用于调试
                print(f"=== 修改工作流参数 ===")
                for node_id in modified_nodes:
                    if node_id in workflow_nodes:
                        print(f"修改后的节点{node_id}信息: {json.dumps(workflow_nodes[node_id]['inputs'], indent=2)}")
                
                # 打印最终的图片输出节点ID
                final_node_id = getattr(self, 'image_output_node_id', None)
                print(f"=== 工作流参数修改完成 ===")
                print(f"最终图片输出节点ID: {final_node_id}")
                return workflow
            
            # 发送工作流到API
            def send_prompt(workflow):
                try:
                    # 直接使用workflow作为节点字典，API只需要节点字典
                    nodes_dict = workflow
                    
                    # 打印调试信息
                    print(f"=== 发送工作流到API ===")
                    print(f"工作流类型: {type(workflow)}")
                    print(f"节点字典类型: {type(nodes_dict)}")
                    print(f"节点数量: {len(nodes_dict)}")
                    print(f"节点ID列表: {list(nodes_dict.keys())[:10]}...")  # 只显示前10个节点ID
                    
                    response = requests.post(
                        f"{COMFYUI_URL}/prompt",
                        json={"prompt": nodes_dict},
                        timeout=TIMEOUT
                    )
                    
                    # 打印响应信息
                    print(f"API响应状态码: {response.status_code}")
                    print(f"API响应头: {dict(response.headers)}")
                    print(f"API响应内容: {response.text}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"API响应JSON: {json.dumps(result, indent=2)}")
                        return result.get('prompt_id')
                    else:
                        error_msg = f"API请求失败，状态码: {response.status_code}"
                        print(error_msg)
                        # 将变量捕获到闭包中
                        def show_error(api_frame_local=api_frame, response_status_code=response.status_code, response_text=response.text, row_index_local=row_index):
                            # 清空原有内容
                            for widget in api_frame_local.winfo_children():
                                widget.pack_forget()
                            # 显示详细错误提示
                            simple_error = f"API接口调用错误，状态码: {response_status_code}\n\n详细信息: {response_text[:200]}..."  # 只显示前200个字符，避免过长
                            # 显示API错误提示，红色字体
                            error_label = ttk.Label(api_frame_local, 
                                               text=simple_error,
                                               foreground="red",
                                               justify=tk.LEFT,
                                               wraplength=400)  # 设置自动换行
                            error_label.pack(expand=True, pady=20, padx=10)
                            # 停止计时器
                            self.stop_row_timer(row_index_local)
                        self.root.after(0, show_error)
                        if callback:
                            callback(False)
                        return None
                except Exception as e:
                    error_msg = f"发送请求失败: {e}"  # pyright: ignore[reportUnusedVariable]
                    print(error_msg)
                    import traceback
                    traceback.print_exc()
                    # 将错误信息捕获到闭包中
                    def show_error(error_message=e):
                        # 清空原有内容
                        for widget in api_frame.winfo_children():
                            widget.pack_forget()
                        # 简化连接错误提示
                        error_str = str(error_message)
                        if "WinError 10061" in error_str or "connection refused" in error_str.lower():
                            simple_error = "无法连接到API接口，请检查服务是否已启动"
                        else:
                            simple_error = "API接口调用错误"
                        # 显示API错误提示，红色字体
                        error_label = ttk.Label(api_frame, 
                                           text=simple_error,
                                           foreground="red",
                                           justify=tk.CENTER)
                        error_label.pack(expand=True, pady=20)
                        # 停止计时器
                        self.stop_row_timer(row_index)
                    self.root.after(0, show_error)
                    if callback:
                        callback(False)
                    return None
            
            # 等待任务完成
            def wait_for_completion(prompt_id):
                start_time = time.time()
                while True:
                    # 检查历史记录
                    try:
                        response = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=TIMEOUT)
                        if response.status_code == 200:
                            history = response.json()
                            if prompt_id in history and "outputs" in history[prompt_id]:
                                return history[prompt_id]
                    except Exception:
                        pass
                    
                    # 检查超时
                    if time.time() - start_time > TIMEOUT:
                        print(f"任务超时，已超过 {TIMEOUT} 秒")
                        def show_error():
                            # 清空原有内容，移除"正在生成图片.."
                            for widget in api_frame.winfo_children():
                                widget.pack_forget()
                            # 显示任务超时错误提示，红色字体
                            error_label = ttk.Label(api_frame, 
                                                   text="任务超时，未能在指定时间内完成",
                                                   foreground="red",
                                                   justify=tk.CENTER)
                            error_label.pack(expand=True, pady=20)
                            # 停止计时器
                            self.stop_row_timer(row_index)
                        self.root.after(0, show_error)
                        if callback:
                            callback(False)
                        return None
                    
                    # 等待5秒
                    time.sleep(5)
            
            # 主流程
            print(f"开始生成图片，图片: {INPUT_IMAGE_PATH}, 提示词: {PROMPT}")
            
            # 1. 加载工作流
            workflow = load_workflow()
            if not workflow:
                if callback:
                    callback(False)
                return
            
            # 2. 修改工作流
            modified_workflow = modify_workflow(workflow)
            
            # 3. 发送工作流
            prompt_id = send_prompt(modified_workflow)
            if not prompt_id:
                if callback:
                    callback(False)
                return
            
            # 4. 等待任务完成
            history = wait_for_completion(prompt_id)
            if not history:
                if callback:
                    callback(False)
                return
            
            # 5. 处理结果
            print(f"图片生成完成，结果: {history}")
            
            # 获取生成的图片路径和workflow PNG路径
            outputs = history.get("outputs", {})
            image_path = None
            workflow_png_path = None
            
            # 检查是否使用了缓存结果
            is_cached = False
            status_messages = history.get("status", {}).get("messages", [])
            for msg in status_messages:
                if msg[0] == "execution_cached":
                    is_cached = True
                    break
            
            print(f"=== 缓存处理调试信息 ===")
            print(f"是否缓存: {is_cached}")
            print(f"outputs是否为空: {not outputs}")
            print(f"outputs内容: {json.dumps(outputs, indent=2)}")
            
            # 处理缓存情况
            if is_cached:
                # 缓存情况下，直接复制上一个图片，不尝试生成新文件
                print("使用缓存结果，复制上一个图片")
                # 检查generated_images列表状态
                generated_images_status = "不存在"
                if hasattr(self, "generated_images"):
                    generated_images_status = f"存在，长度: {len(self.generated_images)}"
                    if row_index < len(self.generated_images):
                        generated_images_status += f"，行{row_index}图片数量: {len(self.generated_images[row_index])}"
                        if self.generated_images[row_index]:
                            generated_images_status += f"，最后图片: {self.generated_images[row_index][-1]}"
                print(f"generated_images状态: {generated_images_status}")
                
                # 只有当没有outputs且有历史图片时，才尝试复制缓存
                if not outputs and hasattr(self, "generated_images") and row_index < len(self.generated_images) and self.generated_images[row_index]:
                    # 取最后一个图片路径
                    last_image_path = self.generated_images[row_index][-1]
                    # 解析最后一个图片的文件名，生成新的文件名
                    base_name = os.path.basename(last_image_path)
                    name_parts = base_name.split("_")
                    if len(name_parts) > 1 and name_parts[-1].startswith("000"):
                        # 尝试生成新的文件名，例如 AnimateDiff_00008.mp4 -> AnimateDiff_00009.mp4
                        try:
                            number_part = name_parts[-1].split(".")[0]
                            number = int(number_part)
                            new_number = number + 1
                            new_base_name = f"{name_parts[0]}_{str(new_number).zfill(5)}_.png"
                            new_png_name = f"{name_parts[0]}_{str(new_number).zfill(5)}_.png"
                            
                            # 从本地图片目录复制文件
                            new_image_path = os.path.join(IMAGE_SAVE_DIR, new_base_name)
                            new_png_path = os.path.join(IMAGE_SAVE_DIR, new_png_name)
                            
                            # 复制图片文件
                            shutil.copy2(last_image_path, new_image_path)
                            # 复制PNG文件
                            last_png_path = last_image_path  # 已经是PNG文件
                            if os.path.exists(last_png_path):
                                shutil.copy2(last_png_path, new_png_path)
                            
                            # 设置图片路径和PNG路径
                            image_path = new_image_path
                            workflow_png_path = new_png_path
                            print(f"使用缓存结果，复制生成新的图片: {image_path}")
                        except (ValueError, IndexError, IOError) as e:
                            print(f"无法复制缓存图片: {e}")
                            image_path = last_image_path
                            workflow_png_path = last_image_path  # 已经是PNG文件
                            print(f"使用原图片路径: {image_path}")
                # 如果缓存处理条件不满足，不报错，继续尝试从outputs获取图片
                print("缓存处理条件不满足，继续尝试从outputs获取图片")
            
            # 正常情况：从outputs中获取图片路径
            if not image_path:
                # 打印完整outputs信息，用于调试
                print(f"=== 从outputs获取图片路径 ===")
                print(f"完整outputs结构: {json.dumps(outputs, indent=2)}")
                
                # 优化逻辑：优先使用配置的图片输出节点
                has_configured_node = hasattr(self, 'image_output_node_id') and self.image_output_node_id
                configured_node_id = self.image_output_node_id if has_configured_node else None
                print(f"配置的图片输出节点ID: {configured_node_id}")
                
                # 先处理配置的图片输出节点
                if has_configured_node and configured_node_id in outputs:
                    print(f"优先处理配置的图片输出节点: {configured_node_id}")
                    node_id = configured_node_id
                    node_outputs = outputs[node_id]
                    print(f"检查节点 {node_id} 的输出: {list(node_outputs.keys())}")
                    
                    # 检查是否有images字段，支持直接在outputs中或在ui子字段中
                    images_field = None
                    if "images" in node_outputs:
                        images_field = node_outputs["images"]
                    elif "ui" in node_outputs and isinstance(node_outputs["ui"], dict) and "images" in node_outputs["ui"]:
                        images_field = node_outputs["ui"]["images"]
                    
                    if images_field:
                        print(f"节点 {node_id} 包含images字段，数量: {len(images_field)}")
                        for image_info in images_field:
                            # 过滤出类型为output的图片（如果有type字段）
                            if "type" in image_info and image_info["type"] != "output":
                                print(f"跳过非output类型图片: {image_info['type']}")
                                continue
                            
                            print(f"图片信息: {json.dumps(image_info, indent=2)}")
                            # 直接获取第一个可用的图片
                            image_filename = image_info["filename"]
                            
                            # 从ComfyUI服务器下载图片1
                            download_url = f"{COMFYUI_URL}/view?filename={image_filename}&type=output"
                            print(f"开始下载图片文件")
                            print(f"下载URL: {download_url}")
                            
                            try:
                                # 下载图片
                                download_response = requests.get(download_url, timeout=30)
                                download_response.raise_for_status()
                                
                                # 确保下载目录存在
                                os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)
                                
                                # 保存图片到本地
                                image_path = os.path.join(IMAGE_SAVE_DIR, image_filename)
                                with open(image_path, 'wb') as f:
                                    f.write(download_response.content)
                                print(f"文件下载成功，大小: {len(download_response.content)}字节")
                                print(f"文件已保存到: {image_path}")
                                
                                # 下载workflow PNG（如果存在）
                                workflow_png_path = None
                                if "workflow" in image_info:
                                    workflow_filename = image_info["workflow"]
                                    workflow_download_url = f"{COMFYUI_URL}/view?filename={workflow_filename}&type=output"
                                    workflow_png_path = os.path.join(IMAGE_SAVE_DIR, workflow_filename)
                                    
                                    workflow_response = requests.get(workflow_download_url, timeout=30)
                                    workflow_response.raise_for_status()
                                    with open(workflow_png_path, 'wb') as f:
                                        f.write(workflow_response.content)
                                    print(f"Workflow文件下载成功，大小: {len(workflow_response.content)}字节")
                                    print(f"Workflow文件已保存到: {workflow_png_path}")
                                
                                # 跳出循环，已找到图片
                                break
                            except Exception as e:
                                print(f"下载图片失败: {e}")
                                # 如果下载失败，尝试使用output_path作为备选
                                if self.output_path:
                                    image_path = os.path.join(self.output_path, image_filename)
                                    workflow_png_path = os.path.join(self.output_path, image_info["workflow"]) if "workflow" in image_info else None
                                    print(f"使用备选路径: {image_path}")
                                    # 跳出循环，已找到图片路径
                                    break
                                else:
                                    print("无法获取图片路径，output_path为空")
                                    # 继续尝试其他图片
                                    continue
                        # 如果找到图片，跳出循环
                        if image_path:
                            pass  # 已经获取到图片，不需要继续处理
                        
                        # 检查是否有其他可能的图片输出字段
                        if not image_path:
                            for output_key, output_value in node_outputs.items():
                                if isinstance(output_value, list) and output_value:
                                    # 检查列表中的元素是否为图片信息
                                    for item in output_value:
                                        if isinstance(item, dict) and "filename" in item:
                                            # 过滤出类型为output的图片（如果有type字段）
                                            if "type" in item and item["type"] != "output":
                                                print(f"跳过非output类型图片: {item['type']}")
                                                continue
                                            
                                            image_filename = item["filename"]
                                            
                                            # 从ComfyUI服务器下载图片
                                            download_url = f"{COMFYUI_URL}/view?filename={image_filename}&type=output"
                                            print(f"开始下载图片文件")
                                            print(f"下载URL: {download_url}")
                                            
                                            try:
                                                # 下载图片
                                                download_response = requests.get(download_url, timeout=30)
                                                download_response.raise_for_status()
                                                
                                                # 确保下载目录存在
                                                os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)
                                                
                                                # 保存图片到本地
                                                image_path = os.path.join(IMAGE_SAVE_DIR, image_filename)
                                                with open(image_path, 'wb') as f:
                                                    f.write(download_response.content)
                                                print(f"文件下载成功，大小: {len(download_response.content)}字节")
                                                print(f"文件已保存到: {image_path}")
                                                workflow_png_path = None
                                                # 跳出循环，已找到图片
                                                break
                                            except Exception as e:
                                                print(f"下载图片失败: {e}")
                                                # 如果下载失败，尝试使用output_path作为备选
                                                if self.output_path:
                                                    image_path = os.path.join(self.output_path, image_filename)
                                                    workflow_png_path = None
                                                    print(f"使用备选路径: {image_path}")
                                                    # 跳出循环，已找到图片路径
                                                    break
                                                else:
                                                    print("无法获取图片路径，output_path为空")
                                                    # 继续尝试其他图片
                                                    continue
                                    # 如果找到图片，跳出循环
                                    if image_path:
                                        break
                                # 如果找到图片，跳出循环
                                if image_path:
                                    break
                
                # 如果配置的节点没有找到图片，遍历所有输出节点
                if not image_path:
                    print(f"{'配置节点未找到图片' if has_configured_node else '未配置输出节点'}，遍历所有输出节点")
                    
                    # 收集所有可用的图片，按type分类
                    output_images = []  # type为output的图片
                    temp_images = []    # type为temp的图片
                    other_images = []   # 没有type字段的图片
                    
                    for node_id, node_outputs in outputs.items():
                        # 跳过已经处理过的配置节点
                        if has_configured_node and node_id == configured_node_id:
                            continue
                        print(f"检查节点 {node_id} 的输出: {list(node_outputs.keys())}")
                        
                        # 检查是否有images字段，支持直接在outputs中或在ui子字段中
                        images_field = None
                        if "images" in node_outputs:
                            images_field = node_outputs["images"]
                        elif "ui" in node_outputs and isinstance(node_outputs["ui"], dict) and "images" in node_outputs["ui"]:
                            images_field = node_outputs["ui"]["images"]
                        
                        if images_field:
                            print(f"节点 {node_id} 包含images字段，数量: {len(images_field)}")
                            for image_info in images_field:
                                print(f"图片信息: {json.dumps(image_info, indent=2)}")
                                image_type = image_info.get("type", "unknown")
                                if image_type == "output":
                                    output_images.append((node_id, image_info))
                                elif image_type == "temp":
                                    temp_images.append((node_id, image_info))
                                else:
                                    other_images.append((node_id, image_info))
                        
                        # 检查是否有其他可能的图片输出字段
                        for output_key, output_value in node_outputs.items():
                            if output_key == "images":
                                continue  # 已经处理过
                            if isinstance(output_value, list) and output_value:
                                for item in output_value:
                                    if isinstance(item, dict) and "filename" in item:
                                        image_type = item.get("type", "unknown")
                                        if image_type == "output":
                                            output_images.append((node_id, item))
                                        elif image_type == "temp":
                                            temp_images.append((node_id, item))
                                        else:
                                            other_images.append((node_id, item))
                    
                    # 优先选择output类型的图片，其次是other，最后是temp
                    print(f"图片分类统计: output={len(output_images)}, other={len(other_images)}, temp={len(temp_images)}")
                    selected_image = None
                    if output_images:
                        selected_image = output_images[0]
                        print(f"选择output类型图片: 节点{selected_image[0]}")
                    elif other_images:
                        selected_image = other_images[0]
                        print(f"选择unknown类型图片: 节点{selected_image[0]}")
                    elif temp_images:
                        selected_image = temp_images[0]
                        print(f"选择temp类型图片: 节点{selected_image[0]}")
                    
                    if selected_image:
                        node_id, image_info = selected_image
                        image_filename = image_info["filename"]
                        image_type = image_info.get("type", "output")
                        
                        # 从ComfyUI服务器下载图片
                        download_url = f"{COMFYUI_URL}/view?filename={image_filename}&type={image_type}"
                        print(f"开始下载图片文件")
                        print(f"下载URL: {download_url}")
                        
                        try:
                            # 下载图片
                            download_response = requests.get(download_url, timeout=30)
                            download_response.raise_for_status()
                            
                            # 确保下载目录存在
                            os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)
                            
                            # 保存图片到本地
                            image_path = os.path.join(IMAGE_SAVE_DIR, image_filename)
                            with open(image_path, 'wb') as f:
                                f.write(download_response.content)
                            print(f"文件下载成功，大小: {len(download_response.content)}字节")
                            print(f"文件已保存到: {image_path}")
                            
                            # 下载workflow PNG（如果存在）
                            workflow_png_path = None
                            if "workflow" in image_info:
                                workflow_filename = image_info["workflow"]
                                workflow_download_url = f"{COMFYUI_URL}/view?filename={workflow_filename}&type={image_type}"
                                workflow_png_path = os.path.join(IMAGE_SAVE_DIR, workflow_filename)
                                
                                workflow_response = requests.get(workflow_download_url, timeout=30)
                                workflow_response.raise_for_status()
                                with open(workflow_png_path, 'wb') as f:
                                    f.write(workflow_response.content)
                                print(f"Workflow文件下载成功，大小: {len(workflow_response.content)}字节")
                                print(f"Workflow文件已保存到: {workflow_png_path}")
                            
                        except Exception as e:
                            print(f"下载图片失败: {e}")
                            # 如果下载失败，尝试使用output_path作为备选
                            if self.output_path:
                                image_path = os.path.join(self.output_path, image_filename)
                                workflow_png_path = os.path.join(self.output_path, image_info["workflow"]) if "workflow" in image_info else None
                                print(f"使用备选路径: {image_path}")
                            else:
                                print("无法获取图片路径，output_path为空")
            
            if not image_path:
                print("未找到生成的图片路径")
                # 清空原有内容，移除"正在生成图片.."
                def show_error():
                    api_frame = self.api_image_frames[row_index]
                    for widget in api_frame.winfo_children():
                        widget.pack_forget()
                    # 显示红色错误提示
                    error_label = ttk.Label(api_frame, 
                                           text="未找到生成的图片路径，检查工作流配置",
                                           foreground="red",
                                           justify=tk.CENTER)
                    error_label.pack(expand=True, pady=20)
                    # 停止计时器
                    self.stop_row_timer(row_index)
                self.root.after(0, show_error)
                if callback:
                    callback(False)
                return
            
            # 6. 保存图片和workflow PNG到指定目录
            try:
                # 确保image_path是字符串类型
                if not isinstance(image_path, (str, bytes, os.PathLike)):
                    print(f"图片路径类型错误: {type(image_path)}")
                    # 停止计时器
                    self.stop_row_timer(row_index)
                    if callback:
                        callback(False)
                    return
                    
                # 由于已经直接下载到IMAGE_SAVE_DIR目录，不需要再复制图片
                image_filename = os.path.basename(image_path)
                image_save_path = image_path
                print(f"图片已保存到: {image_save_path}")
                
                # 检查workflow PNG文件
                if workflow_png_path:
                    print(f"Workflow PNG路径: {workflow_png_path}")
                    if os.path.exists(workflow_png_path):
                        print(f"Workflow PNG已存在: {workflow_png_path}")
                    else:
                        print(f"未找到workflow PNG文件: {workflow_png_path}")
                else:
                    print(f"未找到workflow PNG文件或路径无效: {workflow_png_path}")
            except Exception as e:
                error_msg = f"保存文件失败: {e}"
                print(error_msg)
                def show_error():
                    # 清空原有内容，移除"正在生成图片.."
                    api_frame = self.api_image_frames[row_index]
                    for widget in api_frame.winfo_children():
                        widget.pack_forget()
                    # 显示红色错误提示
                    error_label = ttk.Label(api_frame, 
                                           text=f"保存文件失败: {e}",
                                           foreground="red",
                                           justify=tk.CENTER)
                    error_label.pack(expand=True, pady=20)
                    # 停止计时器
                    self.stop_row_timer(row_index)
                self.root.after(0, show_error)
                if callback:
                    callback(False)
                return
            
            # 7. 在API返回图片显示区域显示结果
            def update_ui():
                """更新UI显示图片缩略图，支持批量生成的横向排列"""
                # 停止该行的计时器
                self.stop_row_timer(row_index)
                
                # 更新UI显示
                api_frame = self.api_image_frames[row_index]
                
                # 保存图片路径
                if not hasattr(self, "generated_images"):
                    self.generated_images = []
                if len(self.generated_images) <= row_index:
                    self.generated_images.extend([[] for _ in range(row_index + 1 - len(self.generated_images))])
                
                # 将当前图片添加到列表中
                if is_batch:
                    self.generated_images[row_index].append(image_save_path)
                    images_to_display = self.generated_images[row_index]
                else:
                    # 非批量模式下，也保留之前生成的图片，横向排列
                    self.generated_images[row_index].append(image_save_path)
                    images_to_display = self.generated_images[row_index]
                
                # 更新已生成图片数量
                self.generated_count = len(self.generated_images[row_index])
                
                # 清空原有内容
                for widget in api_frame.winfo_children():
                    widget.pack_forget()
                
                # 创建一个横向排列的框架
                images_frame = ttk.Frame(api_frame)
                images_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
                
                # 显示所有生成的图片缩略图，横向排列
                for idx, image_path in enumerate(images_to_display):
                    try:
                        # 使用生成的图片作为缩略图
                        if os.path.exists(image_path):
                            # 直接使用生成的图片作为缩略图
                            thumbnail = Image.open(image_path)
                            # 确保缩略图对象是有效的
                            if thumbnail:
                                # 调整缩略图大小，保持宽高比，使用正确的抗锯齿滤镜
                                # 处理不同PIL版本的滤镜名称差异
                                try:
                                    thumbnail.thumbnail((200, 150), Image.LANCZOS)
                                except AttributeError:
                                    # 对于旧版本PIL，使用ANTIALIAS
                                    thumbnail.thumbnail((200, 150), Image.ANTIALIAS)
                        else:
                            # 如果找不到图片文件，创建一个简单的缩略图
                            thumbnail = Image.new('RGB', (200, 150), color='gray')
                            # 在缩略图上绘制一个简单的图片图标
                            draw = ImageDraw.Draw(thumbnail)
                            # 图片图标：矩形
                            image_icon = [(60, 40), (140, 110)]
                            draw.rectangle(image_icon, outline='white', width=3)
                        
                        photo = ImageTk.PhotoImage(thumbnail)
                        
                        # 创建缩略图容器框架，用于添加间距
                        image_container = ttk.Frame(images_frame, padding=5)
                        image_container.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10, pady=10)
                        
                        # 创建缩略图标签
                        thumbnail_label = ttk.Label(image_container, image=photo, cursor="hand2")
                        thumbnail_label.image = photo  # 保存引用，防止被垃圾回收
                        thumbnail_label.pack(expand=True, fill=tk.BOTH)
                        
                        # 绑定点击事件
                        thumbnail_label.bind("<Button-1>", lambda e, path=image_path: self.play_image(row_index, path))
                        
                    except Exception as e:
                        print(f"生成缩略图失败: {e}")
                        # 显示播放按钮作为备选
                        image_container = ttk.Frame(images_frame, padding=5)
                        image_container.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5, pady=5)
                        
                        play_btn = ttk.Button(image_container, text="查看图片", command=lambda path=image_path: self.play_image(row_index, path))
                        play_btn.pack(expand=True, padx=5, pady=5)
                
                # 图片生成完成，更新状态为Finish
                self.generation_status = "Finish"
                
                # 刷新图片显示
                self.refresh_image_display(row_index)
                
                # 调用回调函数，通知图片生成完成
                if callback:
                    callback(True)
                
                # 单个图片生成完成且非批量模式时，播放提醒音乐
                if not is_batch:
                    self.play_finish_sound()
            
            # 在主线程更新UI
            self.root.after(0, update_ui)
        
        # 启动后台线程执行图片生成
        threading.Thread(target=generate_image_thread, daemon=True).start()

    def translate_prompt(self, row_index, callback=None, is_negative=False):
        """调用腾讯翻译API将中文提示词翻译成英文
        
        Args:
            row_index: 图片行索引
            callback: 翻译完成后的回调函数
            is_negative: 是否是负面提示词
        """
        from src.api.tencent_translate import TencentTranslateAPI
        
        prompt_type = "负面" if is_negative else "正向"
        self.logger.info(f"开始翻译第{row_index+1}行{prompt_type}提示词")
        
        # 获取中文提示词
        if is_negative:
            cn_text = self.negative_prompt_texts[row_index].get("1.0", tk.END).strip()
        else:
            cn_text = self.prompt_texts[row_index].get("1.0", tk.END).strip()
        
        # 确定标签索引（每行有两个标签：正向和负面）
        label_index = 2 * row_index + 1 if is_negative else 2 * row_index
        
        self.logger.debug(f"第{row_index+1}行{prompt_type}提示词内容: {cn_text}")
        
        # 检查是否有内容需要翻译
        if not cn_text or cn_text == ("中文负面提示词" if is_negative else "中文提示词"):
            self.logger.info(f"第{row_index+1}行{prompt_type}提示词为空或为默认值，无需翻译")
            # 更新状态为none
            if label_index < len(self.translation_status_labels):
                if hasattr(self.translation_status_labels[label_index], 'update_status'):
                    self.translation_status_labels[label_index].update_status("none")
                else:
                    self.translation_status_labels[label_index].configure(text=f"填入动作提示词-{prompt_type}提示词 (none)")
            if callback:
                callback(row_index, cn_text, "", is_negative=is_negative)
            return
        
        # 检查是否包含中文
        import re
        has_chinese = bool(re.search('[一-龥]', cn_text))
        if not has_chinese:
            self.logger.info(f"第{row_index+1}行{prompt_type}提示词不包含中文，无需翻译")
            # 更新状态为无需翻译
            if label_index < len(self.translation_status_labels):
                if hasattr(self.translation_status_labels[label_index], 'update_status'):
                    self.translation_status_labels[label_index].update_status("无需翻译")
                else:
                    self.translation_status_labels[label_index].configure(text=f"填入动作提示词-{prompt_type}提示词 (无需翻译)")
            
            # 直接将英文内容复制到对应的英文翻译文本框
            if is_negative:
                if self.negative_english_texts[row_index].get("1.0", tk.END).strip() == "英文负面翻译":
                    self.negative_english_texts[row_index].delete("1.0", tk.END)
                else:
                    self.negative_english_texts[row_index].delete("1.0", tk.END)
                self.negative_english_texts[row_index].insert("1.0", cn_text)
            else:
                if self.english_texts[row_index].get("1.0", tk.END).strip() == "英文翻译":
                    self.english_texts[row_index].delete("1.0", tk.END)
                else:
                    self.english_texts[row_index].delete("1.0", tk.END)
                self.english_texts[row_index].insert("1.0", cn_text)
            
            if callback:
                callback(row_index, cn_text, cn_text, is_negative=is_negative)
            return
        
        # 检查是否包含中文
        import re
        # 使用更全面的中文检测正则表达式
        has_chinese = re.search('[\u4e00-\u9fa5]', cn_text)
        if not has_chinese:
            self.logger.info(f"第{row_index+1}行{prompt_type}提示词不包含中文，无需翻译")
            # 更新状态为none（无需翻译）
            if label_index < len(self.translation_status_labels):
                self.translation_status_labels[label_index].configure(text=f"填入动作提示词-{prompt_type}提示词 (无需翻译)")
            if callback:
                callback(row_index, cn_text, cn_text, is_negative=is_negative)
            return
        
        # 更新状态为translating
        if label_index < len(self.translation_status_labels):
            if hasattr(self.translation_status_labels[label_index], 'update_status'):
                self.translation_status_labels[label_index].update_status("translating")
            else:
                self.translation_status_labels[label_index].configure(text=f"填入动作提示词-{prompt_type}提示词 (translating)")
        
        # 检查是否需要停止翻译
        if hasattr(self, "stop_translation") and self.stop_translation:
            self.logger.info(f"翻译已被停止")
            return
        
        # 腾讯翻译API配置 - 从config获取最新配置
        SECRET_ID = self.config.get("tencent_translate", "secret_id", fallback="")
        SECRET_KEY = self.config.get("tencent_translate", "secret_key", fallback="")
        API_REGION = self.config.get("tencent_translate", "region", fallback="ap-guangzhou")
        
        # 记录详细的API配置信息（隐藏敏感信息）
        self.logger.info(f"腾讯翻译API配置: SECRET_ID={SECRET_ID[:10]}..., REGION={API_REGION}")
        
        try:
            # 记录完整的请求信息（隐藏敏感信息）
            self.logger.info(f"正在调用腾讯翻译API翻译第{row_index+1}行{prompt_type}提示词: {cn_text}")
            
            # 使用修复后的翻译模块
            translate_api = TencentTranslateAPI(SECRET_ID, SECRET_KEY, API_REGION)
            target_text = translate_api.translate_text(cn_text)
            
            self.logger.info(f"第{row_index+1}行{prompt_type}提示词翻译成功: {cn_text} -> {target_text}")
            # 更新状态为pass
            if label_index < len(self.translation_status_labels):
                self.translation_status_labels[label_index].update_status("pass")
            if callback:
                callback(row_index, cn_text, target_text, is_negative=is_negative)
            else:
                if is_negative:
                    # 清空英文负面翻译文本框
                    if self.negative_english_texts[row_index].get("1.0", tk.END).strip() == "英文负面翻译":
                        self.negative_english_texts[row_index].delete("1.0", tk.END)
                        self.negative_english_texts[row_index].config(fg="black")
                    else:
                        self.negative_english_texts[row_index].delete("1.0", tk.END)
                    # 填入翻译结果
                    self.negative_english_texts[row_index].insert("1.0", target_text)
                else:
                    # 清空英文翻译文本框
                    if self.english_texts[row_index].get("1.0", tk.END).strip() == "英文翻译":
                        self.english_texts[row_index].delete("1.0", tk.END)
                        self.english_texts[row_index].config(fg="black")
                    else:
                        self.english_texts[row_index].delete("1.0", tk.END)
                    # 填入翻译结果
                    self.english_texts[row_index].insert("1.0", target_text)
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"第{row_index+1}行{prompt_type}提示词翻译失败: {error_msg}", exc_info=True)
            self.logger.debug(f"完整错误堆栈:", exc_info=True)
            # 更新状态为error
            if label_index < len(self.translation_status_labels):
                if hasattr(self.translation_status_labels[label_index], 'update_status'):
                    self.translation_status_labels[label_index].update_status("error")
                else:
                    self.translation_status_labels[label_index].configure(text=f"填入动作提示词-{'负面' if is_negative else '正向'}提示词 (error)")
            # 检查是否是超时或连接错误
            if "timeout" in error_msg.lower() or "connect" in error_msg.lower() or "connection" in error_msg.lower():
                def show_api_error():
                    messagebox.showerror("错误", "腾讯翻译API接口失效，请检查网络连接或API配置")
                self.root.after(0, show_api_error)
            if callback:
                callback(row_index, cn_text, "", error_msg)
    
    def translate_both_prompts(self, row_index):
        """同时翻译正向和负面提示词
        
        Args:
            row_index: 图片行索引
        """
        # 先翻译正向提示词
        def translate_negative_after_positive(*args, **kwargs):
            # 再翻译负面提示词
            self.translate_prompt(row_index, is_negative=True)
        
        self.translate_prompt(row_index, callback=translate_negative_after_positive)
    
    def process_selected_images(self):
        """处理选中的图片项目，按顺序执行生成图片逻辑
        
        检查所有选择项目的勾选框，对勾选的行执行生成图片(单个)的逻辑，按队列顺序执行
        """
        # 检查是否有勾选框变量
        if not hasattr(self, "image_item_vars"):
            messagebox.showwarning("提示", "没有图片项目可供选择")
            return
        
        # 收集所有勾选的行索引
        selected_rows = []
        for row_index, var in enumerate(self.image_item_vars):
            if var.get():
                selected_rows.append(row_index)
        
        if not selected_rows:
            messagebox.showwarning("提示", "请先选择需要生成图片的项目")
            return
        
        # 显示确认弹窗
        confirm_msg = "是否执行可批量生成任务?"
        result = messagebox.askyesno("批量生成确认", confirm_msg)
        if not result:
            return
        
        # 分离成功和失败的行
        success_rows = []
        for row_index in selected_rows:
            if not hasattr(self, "image_paths") or row_index >= len(self.image_paths) or not self.image_paths[row_index]:
                continue
            success_rows.append(row_index)
        
        # 准备合并的提示信息
        combined_message = ""
        
        # 添加成功的提示信息
        if success_rows:
            success_count = len(success_rows)
            if success_count == 1:
                combined_message += f"成功: 第{success_rows[0]+1}项能成功进行生图任务\n"
            else:
                combined_message += f"成功: 第1-{success_count}项能成功进行生图任务\n"
        
        # 添加失败的提示信息
        if len(success_rows) < len(selected_rows):
            failed_rows = [str(row_index+1) for row_index in selected_rows if row_index not in success_rows]
            row_numbers = ",".join(failed_rows)
            combined_message += f"失败: 第{row_numbers}行未导入图片，请导入图片再进行生图任务"
        
        # 显示提示
        if combined_message:
            # 移除末尾可能的换行符
            combined_message = combined_message.rstrip()
            
            # 检查是否包含失败信息
            if "失败:" in combined_message:
                # 使用showerror显示红色错误提示
                messagebox.showerror("批量生成错误", combined_message)
            else:
                # 使用普通信息提示
                messagebox.showinfo("批量生成提示", combined_message)
        
        # 检查是否有成功的行需要处理
        if not success_rows:
            return
        
        # 更新selected_rows为成功的行
        selected_rows = success_rows
        
        print(f"开始批量生成图片，共 {len(selected_rows)} 个项目")
        
        # 导入所需模块
        import threading
        import time
        
        # 启动计时器
        self.start_timer()
        
        # 定义一个简单的处理函数，不使用递归
        def simple_process():
            # 依次处理每个选中的行
            total_items = len(selected_rows)
            for i, row_index in enumerate(selected_rows):
                # 获取当前行的重复生成次数
                count_str = self.batch_generate_count_list[row_index].get()
                try:
                    repeat_count = int(count_str)
                    # 确保重复次数在1-48范围内
                    repeat_count = max(1, min(48, repeat_count))
                except ValueError:
                    # 默认为1
                    repeat_count = 1
                
                print(f"正在生成第 {i+1}/{total_items} 个图片项目，重复生成 {repeat_count} 次")
                
                # 根据重复次数生成多张图片
                for repeat_idx in range(repeat_count):
                    print(f"  正在生成第 {repeat_idx+1}/{repeat_count} 张图片")
                    # 调用生成图片(单个)方法，不使用回调
                    self.generate_image_single(row_index, is_batch=True, batch_index=repeat_idx)
                    # 生成之间添加小延迟，避免API请求过于频繁
                    time.sleep(2)
            
            # 所有项目处理完成
            print("所有图片项目生成完成")
            self.stop_timer()
            self.play_finish_sound()
        
        # 启动后台线程处理
        threading.Thread(target=simple_process, daemon=True).start()
        return
    
    # 以下是原始方法的备份，已被重写
    def _old_process_selected_images(self):
        """处理选中的图片项目，按顺序执行生成图片逻辑
        
        检查所有选择项目的勾选框，对勾选的行执行生成图片(单个)的逻辑，按队列顺序执行
        """
        # 检查是否有勾选框变量
        if not hasattr(self, "image_item_vars"):
            messagebox.showwarning("提示", "没有图片项目可供选择")
            return
        
        # 收集所有勾选的行索引
        selected_rows = []
        for row_index, var in enumerate(self.image_item_vars):
            if var.get():
                selected_rows.append(row_index)
        
        if not selected_rows:
            messagebox.showwarning("提示", "请先选择需要生成图片的项目")
            return
        
        # 显示确认弹窗
        confirm_msg = "是否执行可批量生成任务?"
        result = messagebox.askyesno("批量生成确认", confirm_msg)
        if not result:
            return
        
        print(f"开始批量生成图片，共 {len(selected_rows)} 个项目")
        
        # 导入所需模块
        import threading
        import time
        
        # 启动计时器
        self.start_timer()
        
        # 定义队列处理函数
        def process_queue(queue):
            if not queue:
                # 所有项目处理完成
                print("所有图片项目生成完成")
                # 停止计时器
                self.stop_timer()
                # 播放完成提醒音乐
                self.play_finish_sound()
                return
            
            # 获取当前要处理的行索引
            current_row = queue.pop(0)
            print(f"正在生成第 {len(selected_rows) - len(queue)} 个图片项目")
            
            # 定义图片生成完成的回调函数
            def on_image_generated(success):
                if success:
                    print(f"第 {current_row + 1} 行图片生成成功")
                else:
                    print(f"第 {current_row + 1} 行图片生成失败")
                
                # 生成之间添加小延迟，避免API请求过于频繁
                time.sleep(1)
                
                # 继续处理队列中的下一个项目
                process_queue(queue)
            
            # 调用生成单个图片的逻辑，传递回调函数
            self.generate_image_single(current_row, is_batch=True, callback=on_image_generated)
        
        # 定义一个简单的处理函数，不使用递归
        def simple_process():
            # 依次处理每个选中的行
            for i, row_index in enumerate(selected_rows):
                print(f"正在生成第 {i+1}/{len(selected_rows)} 个图片项目")
                # 调用生成图片(单个)方法，不使用回调
                self.generate_image_single(row_index, is_batch=True)
                # 生成之间添加小延迟
                time.sleep(2)
            
            # 所有项目处理完成
            print("所有图片项目生成完成")
            self.stop_timer()
            self.play_finish_sound()
        
        # 启动后台线程处理
        threading.Thread(target=simple_process, daemon=True).start()
    
    def batch_translate(self):
        """批量翻译所有非默认值的中文提示词
        
        使用多线程并行翻译，提高效率
        """
        import threading
        import time
        
        # 重置停止标志
        self.stop_translating = False
        
        # 启用停止翻译按钮
        self.stop_translate_btn.config(state=tk.NORMAL, style="danger.TButton")
        
        # 收集需要翻译的行 - 包括全英文内容（需要同步）
        rows_to_translate = []
        import re
        for row_index in range(len(self.prompt_texts)):
            # 检查正向提示词
            cn_text = self.prompt_texts[row_index].get("1.0", tk.END).strip()
            if cn_text and cn_text != "中文提示词":
                rows_to_translate.append((row_index, False))
            
            # 检查负面提示词
            cn_text = self.negative_prompt_texts[row_index].get("1.0", tk.END).strip()
            if cn_text and cn_text != "中文负面提示词":
                rows_to_translate.append((row_index, True))
        
        if not rows_to_translate:
            messagebox.showinfo(tr("提示"), tr("没有需要翻译的内容"))
            self.stop_translate_btn.config(state=tk.DISABLED, style="secondary.TButton")
            return
        
        # 翻译计数
        translated_count = 0
        total_count = len(rows_to_translate)
        
        # 翻译结果回调函数
        def translate_callback(row_index, cn_text, target_text, error_msg="", is_negative=False):
            """翻译完成后的回调函数，在主线程更新UI
            
            Args:
                row_index: 图片行索引
                cn_text: 中文提示词
                target_text: 翻译结果
                error_msg: 错误信息
                is_negative: 是否是负面提示词
            """
            nonlocal translated_count
            
            def update_ui():
                """在主线程更新UI"""
                nonlocal translated_count
                translated_count += 1
                
                if error_msg:
                    self.logger.error(f"行 {row_index+1} {'负面' if is_negative else '正向'}翻译失败: {error_msg}")
                elif target_text:
                    # 选择要更新的文本框
                    if is_negative:
                        text_widget = self.negative_english_texts[row_index]
                        default_text = "英文负面翻译"
                    else:
                        text_widget = self.english_texts[row_index]
                        default_text = "英文翻译"
                    
                    # 清空英文翻译文本框
                    if text_widget.get("1.0", tk.END).strip() == default_text:
                        text_widget.delete("1.0", tk.END)
                    else:
                        text_widget.delete("1.0", tk.END)
                    # 填入翻译结果
                    text_widget.insert("1.0", target_text)
                    # 根据当前主题设置文本颜色
                    try:
                        special_themes_str = self.config.get("UI", "special_themes", fallback="darkly,superhero,cyborg,vapor,solar")
                        special_themes = [theme.strip() for theme in special_themes_str.split(",")]
                        if self.style.theme_use() in special_themes:
                            text_widget.config(fg="#ffffff")
                        else:
                            text_widget.config(fg="black")
                    except:
                        # 如果出错，默认使用黑色
                        text_widget.config(fg="black")
                    self.logger.info(f"行 {row_index+1} {'负面' if is_negative else '正向'}翻译成功: {cn_text[:30]}... -> {target_text[:30]}...")
                
                # 所有翻译完成后显示提示
                if translated_count == total_count:
                    self.logger.info(f"批量翻译完成，共翻译 {total_count} 条内容")
            
            # 使用after在主线程更新UI
            self.root.after(0, update_ui)
        
        # 简化实现，使用单线程逐个翻译，避免死机问题
        # 单线程实现更稳定，适合API调用场景
        def translate_in_thread():
            """在单独的线程中进行翻译，避免阻塞UI"""
            for row_index, is_negative in rows_to_translate:
                # 检查是否需要停止翻译
                if self.stop_translating:
                    self.logger.info("翻译已停止")
                    break
                # 翻译一行
                self.translate_prompt(row_index, translate_callback, is_negative=is_negative)
                # 增加小延迟，避免API调用过于频繁
                time.sleep(0.5)
            
            # 翻译完成或停止后，禁用停止翻译按钮
            def disable_stop_button():
                self.stop_translate_btn.config(state=tk.DISABLED, style="secondary.TButton")
            self.root.after(0, disable_stop_button)
        
        # 启动翻译线程，不阻塞UI
        translation_thread = threading.Thread(
            target=translate_in_thread,
            daemon=True
        )
        translation_thread.start()
        
        # 不等待线程完成，避免阻塞UI
        self.logger.info(f"开始批量翻译，共 {total_count} 条内容")
    
    def ollama_translate_prompt(self, row_index, callback=None, is_negative=False):
        """调用Ollama API将中文提示词翻译成英文
        
        Args:
            row_index: 图片行索引
            callback: 翻译完成后的回调函数
            is_negative: 是否是负面提示词
        """
        import subprocess
        import time
        
        # 获取中文提示词
        if is_negative:
            cn_text = self.negative_prompt_texts[row_index].get("1.0", tk.END).strip()
        else:
            cn_text = self.prompt_texts[row_index].get("1.0", tk.END).strip()
        
        # 确定标签索引（每行有两个标签：正向和负面）
        label_index = 2 * row_index + 1 if is_negative else 2 * row_index
        
        # 检查是否有内容需要翻译
        if not cn_text or cn_text == ("中文负面提示词" if is_negative else "中文提示词"):
            # 更新状态为none
            if label_index < len(self.translation_status_labels):
                self.translation_status_labels[label_index].update_status("none")
            if callback:
                callback(row_index, cn_text, "", is_negative=is_negative)
            return
        
        # 检查是否包含中文
        import re
        has_chinese = bool(re.search('[一-龥]', cn_text))
        if not has_chinese:
            # 更新状态为无需翻译
            if label_index < len(self.translation_status_labels):
                self.translation_status_labels[label_index].update_status("无需翻译")
            
            # 直接将英文内容复制到对应的英文翻译文本框
            if is_negative:
                if self.negative_english_texts[row_index].get("1.0", tk.END).strip() == "英文负面翻译":
                    self.negative_english_texts[row_index].delete("1.0", tk.END)
                else:
                    self.negative_english_texts[row_index].delete("1.0", tk.END)
                self.negative_english_texts[row_index].insert("1.0", cn_text)
            else:
                if self.english_texts[row_index].get("1.0", tk.END).strip() == "英文翻译":
                    self.english_texts[row_index].delete("1.0", tk.END)
                else:
                    self.english_texts[row_index].delete("1.0", tk.END)
                self.english_texts[row_index].insert("1.0", cn_text)
            
            if callback:
                callback(row_index, cn_text, cn_text, is_negative=is_negative)
            return
        
        # 更新状态为translating
        if label_index < len(self.translation_status_labels):
            self.translation_status_labels[label_index].update_status("translating")
        
        try:
            # 构建Ollama命令，使用配置页面里的模型名称
            # 从config获取最新的Ollama配置
            ollama_model = self.config.get("ollama", "model", fallback="llama3")
            ollama_timeout = int(self.config.get("ollama", "timeout", fallback="10"))
            cmd = ["ollama", "run", ollama_model, f"将 '{cn_text}' 翻译成英语，仅输出翻译结果，无其他文字"]
            
            # 记录Ollama命令信息
            self.logger.info(f"正在调用Ollama翻译第{row_index+1}行{'负面' if is_negative else '正向'}提示词: {cn_text}")
            self.logger.debug(f"Ollama命令: {' '.join(cmd)}")
            self.logger.debug(f"Ollama超时设置: {ollama_timeout}秒")
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=ollama_timeout)
            
            if result.returncode == 0:
                self.logger.debug(f"Ollama命令执行成功，返回码: {result.returncode}")
                self.logger.debug(f"Ollama输出: {result.stdout.strip()[:100]}...")
                
                # 解析输出，只取最后一行的翻译结果
                output_lines = result.stdout.strip().splitlines()
                target_text = output_lines[-1].strip() if output_lines else ""
                
                self.logger.debug(f"Ollama翻译结果解析: 输出行数={len(output_lines)}, 最终结果={target_text}")
                
                # 更新状态为translated
                if label_index < len(self.translation_status_labels):
                    if hasattr(self.translation_status_labels[label_index], 'update_status'):
                        self.translation_status_labels[label_index].update_status("translated")
                    else:
                        self.translation_status_labels[label_index].configure(text=f"填入动作提示词-{prompt_type}提示词 (translated)")
                
                # 更新英文提示词
                if is_negative:
                    # 清空英文负面翻译文本框
                    if self.negative_english_texts[row_index].get("1.0", tk.END).strip() == "英文负面翻译":
                        self.negative_english_texts[row_index].delete("1.0", tk.END)
                    else:
                        self.negative_english_texts[row_index].delete("1.0", tk.END)
                    # 插入新翻译结果
                    self.negative_english_texts[row_index].insert("1.0", target_text)
                else:
                    # 清空英文翻译文本框
                    if self.english_texts[row_index].get("1.0", tk.END).strip() == "英文翻译":
                        self.english_texts[row_index].delete("1.0", tk.END)
                    else:
                        self.english_texts[row_index].delete("1.0", tk.END)
                    # 插入新翻译结果
                    self.english_texts[row_index].insert("1.0", target_text)
                
                # 调用回调函数
                if callback:
                    callback(row_index, cn_text, target_text, is_negative=is_negative)
            else:
                error_msg = result.stderr.strip() or "翻译失败"
                self.logger.error(f"Ollama翻译失败: {error_msg}")
                self.logger.debug(f"Ollama错误输出: {result.stderr.strip()}")
                self.logger.debug(f"Ollama命令返回码: {result.returncode}")
                if callback:
                    callback(row_index, cn_text, "", error_msg=error_msg, is_negative=is_negative)
                    
        except subprocess.TimeoutExpired:
            error_msg = "Ollama翻译API响应超时，接口可能失效"
            self.logger.error(f"Ollama翻译超时: {error_msg}", exc_info=True)
            # 更新状态为error
            if label_index < len(self.translation_status_labels):
                if hasattr(self.translation_status_labels[label_index], 'update_status'):
                    self.translation_status_labels[label_index].update_status("error")
                else:
                    self.translation_status_labels[label_index].configure(text=f"填入动作提示词-{prompt_type}提示词 (error)")
            # 显示接口失效提示
            def show_timeout_error():
                messagebox.showerror("错误", "Ollama翻译API接口失效，请检查Ollama服务是否正常运行")
            self.root.after(0, show_timeout_error)
            if callback:
                callback(row_index, cn_text, "", error_msg=error_msg, is_negative=is_negative)
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Ollama翻译异常: {error_msg}", exc_info=True)
            self.logger.debug(f"完整错误堆栈:", exc_info=True)
            self.logger.debug(f"Ollama命令: {' '.join(cmd) if 'cmd' in locals() else '未定义'}")
            # 更新状态为error
            if label_index < len(self.translation_status_labels):
                self.translation_status_labels[label_index].configure(text=f"填入动作提示词-{'负面' if is_negative else '正向'}提示词 (error)")
            # 检查是否是连接错误
            if "timeout" in error_msg.lower() or "connect" in error_msg.lower() or "connection" in error_msg.lower() or "not found" in error_msg.lower() or "failed to run" in error_msg.lower():
                def show_api_error():
                    messagebox.showerror("错误", "Ollama翻译API接口失效，请检查Ollama服务是否正常运行")
                self.root.after(0, show_api_error)
            if callback:
                callback(row_index, cn_text, "", error_msg=error_msg, is_negative=is_negative)
    
    def ollama_batch_translate(self):
        """使用Ollama批量翻译所有非默认值的中文提示词
        
        使用多线程翻译，提高效率，同时避免阻塞UI
        """
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # 收集需要翻译的行 - 包括全英文内容（需要同步）
        rows_to_translate = []
        import re
        for row_index in range(len(self.prompt_texts)):
            # 检查正向提示词
            cn_text = self.prompt_texts[row_index].get("1.0", tk.END).strip()
            if cn_text and cn_text != "中文提示词":
                rows_to_translate.append((row_index, False))
            
            # 检查负面提示词
            cn_text = self.negative_prompt_texts[row_index].get("1.0", tk.END).strip()
            if cn_text and cn_text != "中文负面提示词":
                rows_to_translate.append((row_index, True))
        
        if not rows_to_translate:
            messagebox.showinfo(tr("提示"), tr("没有需要翻译的内容"))
            self.stop_translate_btn.config(state=tk.DISABLED, style="secondary.TButton")
            return
        
        # 翻译计数
        translated_count = 0
        total_count = len(rows_to_translate)
        
        # 重置停止标志
        self.stop_translating = False
        
        # 启用停止翻译按钮
        self.stop_translate_btn.config(state=tk.NORMAL, style="danger.TButton")
        
        # 翻译结果回调函数
        def translate_callback(row_index, cn_text, target_text, error_msg="", is_negative=False):
            """翻译完成后的回调函数，在主线程更新UI
            
            Args:
                row_index: 图片行索引
                cn_text: 中文提示词
                target_text: 翻译结果
                error_msg: 错误信息
                is_negative: 是否是负面提示词
            """
            nonlocal translated_count
            
            def update_ui():
                """在主线程更新UI"""
                nonlocal translated_count
                translated_count += 1
                
                if error_msg:
                    self.logger.error(f"Ollama行 {row_index+1} {'负面' if is_negative else '正向'}翻译失败: {error_msg}")
                elif target_text:
                    self.logger.info(f"Ollama行 {row_index+1} {'负面' if is_negative else '正向'}翻译成功: {cn_text[:50]}{'...' if len(cn_text) > 50 else ''} -> {target_text[:50]}{'...' if len(target_text) > 50 else ''}")
                
                # 所有翻译完成后显示提示
                if translated_count == total_count:
                    self.logger.info(f"Ollama批量翻译完成，共翻译 {total_count} 条内容")
                    # 翻译完成后禁用停止翻译按钮
                    self.stop_translate_btn.config(state=tk.DISABLED, style="secondary.TButton")
            
            # 使用after在主线程更新UI
            self.root.after(0, update_ui)
        
        # 多线程实现，使用线程池控制并发数量
        def translate_in_thread():
            """在单独的线程中进行翻译，避免阻塞UI"""
            # 控制并发数量为3，避免API调用过于频繁
            max_workers = 3
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有翻译任务
                future_to_task = {executor.submit(self.ollama_translate_prompt, row_index, translate_callback, is_negative=is_negative): (row_index, is_negative) 
                                 for row_index, is_negative in rows_to_translate}
                
                # 处理完成的任务
                for future in as_completed(future_to_task):
                    # 检查是否需要停止翻译
                    if self.stop_translating:
                        self.logger.info("翻译已停止")
                        # 取消所有未完成的任务
                        for f in future_to_task:
                            f.cancel()
                        # 在主线程禁用停止按钮
                        def disable_stop():
                            self.stop_translate_btn.config(state=tk.DISABLED, style="secondary.TButton")
                        self.root.after(0, disable_stop)
                        break
                        
                    row_index, is_negative = future_to_task[future]
                    try:
                        # 获取结果，捕获任何异常
                        future.result()
                    except Exception as e:
                        print(f"Ollama行 {row_index+1} {'负面' if is_negative else '正向'}翻译任务执行异常: {e}")
                    
                    # 增加小延迟，避免API调用过于频繁
                    time.sleep(0.3)
        
        # 启动翻译线程，不阻塞UI
        translation_thread = threading.Thread(
            target=translate_in_thread,
            daemon=True
        )
        translation_thread.start()
        
        print(f"Ollama开始批量翻译，共 {total_count} 条内容，最大并发数: 3")
    
    def stop_translate(self):
        """停止批量翻译"""
        self.stop_translating = True
        print("正在停止翻译...")
    
    def remove_single_image(self, row_index, image_index):
        """移除单张图片显示，不删除原文件
        
        Args:
            row_index: 图片行索引
            image_index: 图片索引
        """
        if hasattr(self, "generated_images") and row_index < len(self.generated_images):
            if 0 <= image_index < len(self.generated_images[row_index]):
                # 移除图片路径
                self.generated_images[row_index].pop(image_index)
                
                # 刷新图片显示
                self.refresh_image_display(row_index)
                
                # 更新生图状态
                if hasattr(self, "generated_count") and hasattr(self, "total_count"):
                    self.generated_count = max(0, self.generated_count - 1)
        
    def save_image(self, image_path):
        """保存图片到指定位置
        
        Args:
            image_path: 图片路径
        """
        if os.path.exists(image_path):
            # 弹出文件选择对话框
            save_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
                initialfile=os.path.basename(image_path)
            )
            if save_path:
                try:
                    # 复制文件
                    shutil.copy2(image_path, save_path)
                    messagebox.showinfo("提示", f"图片已保存到: {save_path}")
                except Exception as e:
                    messagebox.showerror("错误", f"保存图片失败: {e}")
        
    def refresh_image_display(self, row_index):
        """刷新图片显示
        
        Args:
            row_index: 图片行索引
        """
        if hasattr(self, "api_image_frames") and row_index < len(self.api_image_frames):
            api_frame_inner = self.api_image_frames[row_index]
            
            # 获取要显示的图片列表
            images_to_display = self.generated_images[row_index] if hasattr(self, "generated_images") and row_index < len(self.generated_images) else []
            
            # 更新image单选键状态：只要有图片，就有删除图标
            has_delete_icon = len(images_to_display) > 0
            if hasattr(self, "image_radio_vars") and row_index < len(self.image_radio_vars):
                self.image_radio_vars[row_index].set(has_delete_icon)
            
            # 清空原有内容
            for widget in api_frame_inner.winfo_children():
                widget.pack_forget()
            
            # 获取要显示的图片列表
            images_to_display = self.generated_images[row_index] if hasattr(self, "generated_images") and row_index < len(self.generated_images) else []
            
            # 创建主框架，包含图片区域
            main_api_frame = ttk.Frame(api_frame_inner)
            main_api_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
            
            # 更新API框体标题
            if hasattr(self, "api_frames") and row_index < len(self.api_frames):
                api_label_frame = self.api_frames[row_index]
                if images_to_display:
                    # 更新生图状态
                    current_count = len(images_to_display)
                    # 统一使用"已生图- X张"格式，显示当前图片数量
                    status_text = f"{tr('API返回图片')} ({tr('已生图')}- {current_count}{tr('张')})"
                    # 使用默认样式，统一颜色
                    api_label_frame.configure(text=status_text, style="StatusNone.TLabelframe")
                else:
                    status_text = f"{tr('API返回图片')} (none)"
                    self.generation_status = "none"
                    self.generated_count = 0
                    self.total_count = 0
                    # 应用none样式，黑色字体
                    api_label_frame.configure(text=status_text, style="StatusNone.TLabelframe")
            
            # 创建图片容器框架
            images_frame = ttk.Frame(main_api_frame)
            images_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
            
            # 显示所有生成的图片缩略图，每行8张
            images_per_row = 8
            current_row = ttk.Frame(images_frame)
            current_row.pack(fill=tk.X, expand=True, pady=5)
            
            for idx, image_path in enumerate(images_to_display):
                try:
                    # 如果是第8张图片，创建新行
                    if idx % images_per_row == 0 and idx > 0:
                        current_row = ttk.Frame(images_frame)
                        current_row.pack(fill=tk.X, expand=True, pady=5)
                    
                    # 使用生成的图片作为缩略图
                    if os.path.exists(image_path):
                        # 直接使用生成的图片作为缩略图
                        thumbnail = Image.open(image_path)
                    else:
                        # 如果找不到图片文件，创建一个简单的缩略图
                        thumbnail = Image.new('RGB', (200, 150), color='gray')
                        # 在缩略图上绘制一个简单的图片图标
                        draw = ImageDraw.Draw(thumbnail)
                        # 图片图标：矩形
                        image_icon = [(60, 40), (140, 110)]
                        draw.rectangle(image_icon, outline='white', width=3)
                    
                    # 调整缩略图大小，保持宽高比
                    # 处理不同PIL版本的滤镜名称差异
                    try:
                        thumbnail.thumbnail((200, 150), Image.LANCZOS)
                    except AttributeError:
                        # 对于旧版本PIL，使用ANTIALIAS
                        thumbnail.thumbnail((200, 150), Image.ANTIALIAS)
                    
                    photo = ImageTk.PhotoImage(thumbnail)
                    
                    # 创建图片容器，用于包含图片、文件名和按钮
                    # 使用Labelframe作为图片容器，添加边框和阴影效果，设置固定大小200x250
                    filename = os.path.basename(image_path)
                    # 将文件名作为框体名称，显示为 "name: 文件名" 格式
                    image_container = ttk.Labelframe(current_row, text=f"○ {filename}", padding=10, relief="groove", borderwidth=1, width=200, height=250)
                    image_container.pack(side=tk.LEFT, padx=10, pady=10)
                    image_container.pack_propagate(False)  # 禁止容器随内容大小变化
                    
                    # 创建缩略图标签，确保图片居中
                    thumbnail_label = ttk.Label(image_container, image=photo, cursor="hand2", anchor=tk.CENTER)
                    thumbnail_label.image = photo  # 保存引用，防止被垃圾回收
                    thumbnail_label.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
                    
                    # 绑定点击事件
                    thumbnail_label.bind("<Button-1>", lambda e, path=image_path: self.play_image(row_index, path))
                    
                    # 创建按钮容器，使用网格布局
                    buttons_frame = ttk.Frame(image_container)
                    buttons_frame.pack(fill=tk.X, pady=5, padx=5)
                    buttons_frame.columnconfigure(0, weight=1)
                    buttons_frame.columnconfigure(1, weight=1)
                    
                    # 删除按钮
                    delete_btn = ttk.Button(buttons_frame, text="❌", width=3, command=lambda current_idx=idx: self.remove_single_image(row_index, current_idx), style="Outline.TButton")
                    delete_btn.grid(row=0, column=0, padx=3, pady=1, sticky=tk.NSEW)
                    # 添加删除按钮悬停提示
                    delete_btn.bind("<Enter>", lambda e, btn=delete_btn: btn.configure(text="删除", style="Danger.TButton"))
                    delete_btn.bind("<Leave>", lambda e, btn=delete_btn: btn.configure(text="❌", style="Outline.TButton"))
                    
                    # 保存按钮
                    save_btn = ttk.Button(buttons_frame, text="💾", width=3, command=lambda path=image_path: self.save_image(path), style="Outline.TButton")
                    save_btn.grid(row=0, column=1, padx=3, pady=1, sticky=tk.NSEW)
                    # 添加保存按钮悬停提示
                    save_btn.bind("<Enter>", lambda e, btn=save_btn: btn.configure(text="另存为", style="Danger.TButton"))
                    save_btn.bind("<Leave>", lambda e, btn=save_btn: btn.configure(text="💾", style="Outline.TButton"))
                    
                except Exception as e:
                    print(f"生成缩略图失败: {e}")
                    # 显示播放按钮作为备选
                    # 使用Labelframe作为图片容器，添加边框和阴影效果，设置固定大小200x250
                    filename = os.path.basename(image_path)
                    image_container = ttk.Labelframe(current_row, text=f"name: {filename}", padding=10, relief="groove", borderwidth=1, width=200, height=250)
                    image_container.pack(side=tk.LEFT, padx=10, pady=10)
                    image_container.pack_propagate(False)  # 禁止容器随内容大小变化
                    
                    play_btn = ttk.Button(image_container, text="查看图片", command=lambda path=image_path: self.play_image(row_index, path))
                    play_btn.pack(expand=True, padx=5, pady=5)
                    
                    # 文件名
                    filename = os.path.basename(image_path)
                    filename_label = ttk.Label(image_container, text=filename, font=('宋体', 8), wraplength=180, justify=tk.CENTER)
                    filename_label.pack(pady=5)
                    
                    # 按钮容器
                    buttons_frame = ttk.Frame(image_container)
                    buttons_frame.pack(fill=tk.X, pady=5)
                    
                    # 删除按钮
                    delete_btn = ttk.Button(buttons_frame, text="🗑️", width=3, command=lambda current_idx=idx: self.remove_single_image(row_index, current_idx))
                    delete_btn.pack(side=tk.LEFT, expand=True, padx=2)
                    
                    # 保存按钮
                    save_btn = ttk.Button(buttons_frame, text="💾", width=3, command=lambda path=image_path: self.save_image(path))
                    save_btn.pack(side=tk.LEFT, expand=True, padx=2)
        
    def batch_copy_prompts(self):
        """批量直译功能
        
        将每行的中文提示词直接赋值到英文提示词文本框，
        将中文负面提示词直接赋值到英文负面提示词文本框
        """
        copied_count = 0
        
        for row_index in range(len(self.prompt_texts)):
            # 处理正向提示词
            cn_text = self.prompt_texts[row_index].get("1.0", tk.END).strip()
            if cn_text and cn_text != "中文提示词":
                # 直接赋值到英文提示词文本框
                self.english_texts[row_index].delete("1.0", tk.END)
                self.english_texts[row_index].insert("1.0", cn_text)
                copied_count += 1
            
            # 处理负面提示词
            cn_negative_text = self.negative_prompt_texts[row_index].get("1.0", tk.END).strip()
            if cn_negative_text and cn_negative_text != "中文负面提示词":
                # 直接赋值到英文负面提示词文本框
                self.negative_english_texts[row_index].delete("1.0", tk.END)
                self.negative_english_texts[row_index].insert("1.0", cn_negative_text)
                copied_count += 1
        
        self.logger.info(f"批量直译完成，共复制 {copied_count} 条内容")
        messagebox.showinfo(tr("提示"), tr("批量直译完成，共复制 {count} 条内容").format(count=copied_count))
    
    def configure_grid_weights(self):
        """配置网格权重"""
        # 配置列权重 - 确保fixed_frame和main_frame使用相同的列配置
        for frame in [self.fixed_frame, self.main_frame]:
            # No.列
            frame.columnconfigure(0, weight=0, minsize=60)  # 固定宽度，显示序号
            # 图片列
            frame.columnconfigure(1, weight=1, minsize=120)  # 进一步减小最小宽度
            # 正向提示词列
            frame.columnconfigure(2, weight=1)
            # 负面提示词列
            frame.columnconfigure(3, weight=1)
            # 批量生成新资源列
            frame.columnconfigure(4, weight=1, minsize=120)  # 进一步减小最小宽度
            # 图片参数列
            frame.columnconfigure(5, weight=1, minsize=80)  # 进一步减小最小宽度
        
        # 配置行权重 - 只对main_frame，每个内容行占用2行网格空间
        for i in range(12):
            self.main_frame.rowconfigure(i, weight=1)
        

            
    def batch_export_videos(self):
        """批量导出图片
        将所有每行已经通过API成功生成的图片文件，全部导出到指定文件夹
        导出文件名格式：tu1_AnimateDiff_00016.mp4
        """
        import shutil
        import os
        
        # 检查是否有已生成的图片
        if not hasattr(self, "generated_videos"):
            messagebox.showinfo("提示", "没有已生成的图片可以导出")
            return
        
        # 选择导出文件夹
        export_dir = filedialog.askdirectory(title="选择导出文件夹")
        if not export_dir:
            return
        
        # 统计成功导出的图片数量
        success_count = 0
        
        # 遍历所有行
        for row_index in range(len(self.generated_videos)):
            videos = self.generated_videos[row_index]
            if not videos:
                continue
            
            # 生成图标识：tu1, tu2, ...
            tu_id = f"tu{row_index + 1}"
            
            # 遍历该行所有图片
            for video_path in videos:
                if os.path.exists(video_path):
                    # 获取原文件名
                    original_filename = os.path.basename(video_path)
                    # 生成新文件名：tu1_AnimateDiff_00016.mp4
                    new_filename = f"{tu_id}_{original_filename}"
                    # 构建目标路径
                    target_path = os.path.join(export_dir, new_filename)
                    
                    try:
                        # 复制文件
                        shutil.copy2(video_path, target_path)
                        success_count += 1
                        print(f"成功导出图片：{new_filename}")
                    except Exception as e:
                        print(f"导出图片失败 {video_path} -> {target_path}: {str(e)}")
        
        # 显示导出结果
        if success_count > 0:
            messagebox.showinfo("导出完成", f"成功导出 {success_count} 个图片文件到 {export_dir}")
        else:
            messagebox.showinfo("提示", "没有找到可导出的图片文件")
    
        
        # 居中显示
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (self.root.winfo_width() // 2) - (width // 2) + self.root.winfo_x()
        y = (self.root.winfo_height() // 2) - (height // 2) + self.root.winfo_y()
        dialog.geometry(f"+{x}+{y}")
        
        # 添加ESC键绑定
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="请选择创作篇幅", font=("宋体", 12, "bold"))
        title_label.pack(pady=10)
        
        # 当前选中的行数
        selected_length = tk.IntVar(value=30)
        
        # 单选按钮框架
        radio_frame = ttk.Frame(main_frame)
        radio_frame.pack(pady=10)
        
        # 30行单选按钮
        radio_30 = ttk.Radiobutton(radio_frame, text="30行", variable=selected_length, value=30)
        radio_30.pack(anchor=tk.W, pady=5)
        
        # 50行单选按钮
        radio_50 = ttk.Radiobutton(radio_frame, text="50行", variable=selected_length, value=50)
        radio_50.pack(anchor=tk.W, pady=5)
        
        # 100行单选按钮
        radio_100 = ttk.Radiobutton(radio_frame, text="100行", variable=selected_length, value=100)
        radio_100.pack(anchor=tk.W, pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 确定按钮
        def confirm():
            length = selected_length.get()
            self.change_content_length(length)
            dialog.destroy()
        
        confirm_btn = ttk.Button(button_frame, text="确定", command=confirm, width=10)
        confirm_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 取消按钮
        cancel_btn = ttk.Button(button_frame, text="取消", command=dialog.destroy, width=10)
        cancel_btn.pack(side=tk.RIGHT, padx=5, pady=5)
    

        """更改内容行数"""
        # 更新配置文件
        if "system" not in self.config:
            self.config["system"] = {}
        self.config["system"]["content_rows"] = str(length)
        self.save_config()
        
        # 获取当前已有的行数
        current_rows = 30  # 默认值
        if hasattr(self, "k_sampler_steps_list"):
            current_rows = len(self.k_sampler_steps_list)
        
        # 如果需要增加行数
        if length > current_rows:
            for i in range(current_rows, length):
                self.create_content_row(i)
        # 如果需要减少行数
        elif length < current_rows:
            # 这里需要更复杂的逻辑来删除多余的行
            # 首先更新所有列表的长度
            if hasattr(self, "k_sampler_steps_list"):
                self.k_sampler_steps_list = self.k_sampler_steps_list[:length]
            if hasattr(self, "image_height_list"):
                self.image_height_list = self.image_height_list[:length]
            if hasattr(self, "image_width_list"):
                self.image_width_list = self.image_width_list[:length]
            if hasattr(self, "image_orientation_list"):
                self.image_orientation_list = self.image_orientation_list[:length]
            if hasattr(self, "video_item_vars"):
                self.video_item_vars = self.video_item_vars[:length]
            if hasattr(self, "prompt_texts"):
                self.prompt_texts = self.prompt_texts[:length]
            if hasattr(self, "english_texts"):
                self.english_texts = self.english_texts[:length]
            if hasattr(self, "img_prompts"):
                self.img_prompts = self.img_prompts[:length]
            if hasattr(self, "img_labels"):
                self.img_labels = self.img_labels[:length]
            if hasattr(self, "img_frames"):
                self.img_frames = self.img_frames[:length]
            if hasattr(self, "api_video_frames"):
                self.api_image_frames = self.api_image_frames[:length]
            if hasattr(self, "image_paths"):
                self.image_paths = self.image_paths[:length]
            if hasattr(self, "image_cache"):
                self.image_cache = self.image_cache[:length]
            
            # 重新创建整个布局
            for widget in self.main_frame.winfo_children():
                widget.destroy()
            self.create_grid_layout()
            
            # 强制更新canvas的滚动区域
            self.main_frame.update_idletasks()  # 确保所有widget都已绘制
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))  # 更新canvas滚动区域
        
        messagebox.showinfo("提示", f"已切换到{length}行模式")
    
    def config_ollama_api(self):
        """配置Ollama API"""
        self.show_config_dialog(tr("Ollama API配置"), "ollama", [
            ("Ollama URL", "url", self.ollama_url, False),
            (tr("模型名称"), "model", self.ollama_model, False),
            (tr("响应超时时间"), "timeout", "10", False)
        ])
    
    def config_translate_api(self):
        """配置腾讯翻译API"""
        self.show_config_dialog(tr("腾讯翻译API配置"), "tencent_translate", [
            ("APPID", "appid", self.tencent_appid, False),
            ("Secret ID", "secret_id", self.tencent_secret_id, False),
            ("Secret Key", "secret_key", self.tencent_secret_key, False),
            (tr("API主机"), "host", self.tencent_api_host, False),
            (tr("API动作"), "action", self.tencent_api_action, False),
            (tr("API版本"), "version", self.tencent_api_version, False),
            (tr("API区域"), "region", self.tencent_api_region, False)
        ])
    
    def config_comfyui_status_api(self):
        """配置ComfyUI API状态"""
        self.show_config_dialog("ComfyUI API状态配置", "comfyui_status", [
            ("ComfyUI URL", "url", self.COMFYUI_URL, False),
            ("超时时间", "timeout", "10", False),
            ("工作流路径", "workflow_path", r"config\API\test_wan2.2-14B状态+生图_接口.json", True)
        ])
    
    def config_comfyui_gen_api(self):
        """配置ComfyUI API生图"""
        self.show_config_dialog("ComfyUI API生图配置", "comfyui_gen", [
            ("ComfyUI URL", "url", "http://127.0.0.1:8188", False),
            ("超时时间", "timeout", "300", False),
            ("工作流路径", "workflow_path", r"config\API\test_wan2.2-14B状态+生图_接口.json", True),
            ("图片保存目录", "video_save_dir", "video", True)
        ])
    
    def config_comfyui_api(self):
        """配置ComfyUI API"""
        # 创建配置对话框
        config_window = tk.Toplevel(self.root)
        config_window.title(tr("ComfyUI API配置"))
        config_window.geometry("800x700")
        config_window.resizable(False, False)
        
        # 设置对话框置顶
        config_window.transient(self.root)
        
        # 居中显示在屏幕正中央
        # 强制更新窗口尺寸信息
        config_window.update()
        # 获取窗口实际尺寸
        width = config_window.winfo_width()
        height = config_window.winfo_height()
        
        # 获取主窗口的位置和尺寸
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        
        # 计算相对于主窗口的中心坐标
        x = root_x + (root_width - width) // 2
        y = root_y + (root_height - height) // 2
        
        # 设置窗口位置
        config_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # 确保窗口在顶层
        config_window.lift()
        
        # 添加ESC键绑定，按ESC键关闭窗口
        config_window.bind("<Escape>", lambda e: config_window.destroy())
        
        main_frame = ttk.Frame(config_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加标题
        title_label = ttk.Label(main_frame, text=tr("ComfyUI API配置"), font=("宋体", 14, "bold"))
        title_label.pack(pady=10)
        
        # ComfyUI文件列表展示栏
        file_frame = ttk.Labelframe(main_frame, text=tr("ComfyUI文件列表"))
        file_frame.pack(fill=tk.BOTH, pady=10, expand=True)
        file_frame.grid_rowconfigure(0, weight=1)
        file_frame.grid_columnconfigure(0, weight=1)
        file_frame.grid_columnconfigure(1, weight=0)
        file_frame.grid_columnconfigure(2, weight=0)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(file_frame)
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # 创建Treeview表格，显示序号和文件名
        file_list = ttk.Treeview(file_frame, columns=("index", "name"), show="headings", yscrollcommand=scrollbar.set)
        file_list.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        scrollbar.configure(command=file_list.yview)
        
        # 设置列宽和标题
        file_list.heading("index", text=tr("序号"), anchor=tk.CENTER)
        file_list.column("index", width=50, anchor=tk.CENTER, stretch=tk.NO)
        file_list.heading("name", text=tr("文件名"), anchor=tk.W)
        file_list.column("name", width=600, anchor=tk.W)
        
        # 右侧按钮框架
        right_btn_frame = ttk.Frame(file_frame, padding=10)
        right_btn_frame.grid(row=0, column=2, sticky="ns")
        
        # 选择API目录函数
        def select_api_dir():
            """选择API目录"""
            from tkinter import filedialog
            # 打开文件夹选择对话框
            selected_dir = filedialog.askdirectory(
                title="选择API目录",
                initialdir=self.api_dir
            )
            if selected_dir:
                # 修改load_file_list函数，使用选择的目录
                def updated_load_file_list():
                    # 清空现有列表
                    for item in file_list.get_children():
                        file_list.delete(item)
                    
                    # 使用选择的目录
                    comfyui_api_dir = selected_dir
                    if not os.path.exists(comfyui_api_dir):
                        os.makedirs(comfyui_api_dir)
                    
                    # 获取所有JSON文件和文件夹
                    all_items = []
                    for item in os.listdir(comfyui_api_dir):
                        item_path = os.path.join(comfyui_api_dir, item)
                        if os.path.isdir(item_path) or item.endswith(".json"):
                            all_items.append(item)
                
                    # 按名称排序，文件夹在前，文件在后
                    all_items.sort(key=lambda x: (os.path.isfile(os.path.join(comfyui_api_dir, x)), x))
                
                    # 添加到Treeview
                    for i, item in enumerate(all_items, 1):
                        item_path = os.path.join(comfyui_api_dir, item)
                        if os.path.isdir(item_path):
                            # 文件夹：添加文件夹图标和斜杠标识
                            display_name = f"📁 {item}/"
                        else:
                            # JSON文件：添加文件图标
                            display_name = f"📄 {item}"
                        file_list.insert("", tk.END, values=(i, display_name))
                    
                    # 如果没有文件，提示用户
                    if not all_items:
                        file_list.insert("", tk.END, values=(1, "(暂无文件或文件夹)"))
                
                updated_load_file_list()
        
        # 选择API目录按钮
        select_dir_btn = ttk.Button(right_btn_frame, text=tr("选择API目录"), command=select_api_dir, width=15)
        select_dir_btn.pack(pady=5, anchor="center")
        
        # 加载文件列表
        def load_file_list():
            """加载ComfyUI文件列表"""
            # 清空现有列表
            for item in file_list.get_children():
                file_list.delete(item)
            
            # 获取ComfyUI API文件目录（从配置文件读取）
            comfyui_api_dir = self.api_dir
            if not os.path.exists(comfyui_api_dir):
                os.makedirs(comfyui_api_dir)
            
            # 获取所有JSON文件和文件夹
            all_items = []
            for item in os.listdir(comfyui_api_dir):
                item_path = os.path.join(comfyui_api_dir, item)
                if os.path.isdir(item_path) or item.endswith(".json"):
                    all_items.append(item)
            
            # 按名称排序，文件夹在前，文件在后
            all_items.sort(key=lambda x: (os.path.isfile(os.path.join(comfyui_api_dir, x)), x))
            
            # 添加到Treeview
            for i, item in enumerate(all_items, 1):
                item_path = os.path.join(comfyui_api_dir, item)
                if os.path.isdir(item_path):
                    # 文件夹：添加文件夹图标和斜杠标识
                    display_name = f"📁 {item}/"
                else:
                    # JSON文件：添加文件图标
                    display_name = f"📄 {item}"
                file_list.insert("", tk.END, values=(i, display_name))
            
            # 如果没有文件，提示用户
            if not all_items:
                file_list.insert("", tk.END, values=(1, "(暂无文件或文件夹)"))
        
        # 加载初始文件列表
        load_file_list()
        
        # 正在使用的ComfyUI工作流
        current_frame = ttk.Labelframe(main_frame, text=tr("正在使用的ComfyUI工作流"))
        current_frame.pack(fill=tk.X, pady=10)
        current_frame.pack_propagate(True)  # 允许框架自动调整大小
        
        # 获取当前使用的工作流文件
        current_workflow_path = self.config.get("comfyui_gen", "workflow_path", fallback="")
        if current_workflow_path:
            current_filename = os.path.basename(current_workflow_path)
        else:
            current_filename = tr("未选择")
        
        # 当前使用工作流显示区域
        current_workflow_frame = ttk.Frame(current_frame)
        current_workflow_frame.pack(pady=(10, 2), padx=10, fill=tk.X)
        
        current_workflow_var = tk.StringVar(value=f"{tr('当前API:')} {current_filename}")
        current_workflow_label = ttk.Label(current_workflow_frame, textvariable=current_workflow_var, font=("宋体", 10))
        current_workflow_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # API状态显示标签
        api_status_var = tk.StringVar(value=tr("状态: 未测试"))
        api_status_label = ttk.Label(current_workflow_frame, textvariable=api_status_var, font=("宋体", 10, "bold"), foreground="#666666")
        api_status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # INI文件信息显示 - 基于当前工作流文件自动生成
        current_ini_file = os.path.splitext(os.path.basename(current_workflow_path))[0] + ".ini" if current_workflow_path else tr("未选择")
        
        # 创建INI文件名称的StringVar，方便后续更新
        current_ini_var = tk.StringVar(value=f"{tr('当前脚本:')} {current_ini_file}")
        ttk.Label(current_frame, textvariable=current_ini_var, font=("宋体", 10)).pack(pady=(5, 10), padx=10, anchor=tk.W)
        
        # 测试API函数
        def test_selected_api():
            """测试当前选定的ComfyUI API"""
            try:
                # 更新状态为测试中
                api_status_var.set("状态: 测试中...")
                api_status_label.configure(foreground="#ff9900")
                
                # 获取当前选择的工作流
                selected_file = ""
                if file_list.selection():
                    selected_item = file_list.selection()[0]
                    selected_file = file_list.item(selected_item, "values")[1]
                # 提取原始文件名（去掉图标）
                if selected_file.startswith("📁 "):
                    selected_file = selected_file[2:-1]  # 去掉📁 和末尾的/
                elif selected_file.startswith("📄 "):
                    selected_file = selected_file[2:]  # 去掉📄 图标
                elif selected_file.startswith("(暂无文件或文件夹)"):
                    # 跳过提示信息
                    selected_file = ""
                elif current_workflow_path:
                    selected_file = current_filename
                
                if not selected_file or selected_file == "未选择" or selected_file == "(暂无文件，请使用导入功能添加)":
                    messagebox.showwarning("提示", "请先选择工作流文件", parent=config_window)
                    api_status_var.set("状态: 未测试")
                    api_status_label.configure(foreground="#666666")
                    return
                
                # 获取ComfyUI API URL
                comfyui_url = self.config.get("ComfyUI", "api_url", fallback=self.COMFYUI_URL)
                
                # 测试API
                def api_test_thread():
                    import requests
                    status = False
                    try:
                        response = requests.get(comfyui_url, timeout=5)
                        status = response.status_code == 200
                    except Exception:
                        status = False
                    
                    # 更新UI
                    def update_ui():
                        if status:
                            api_status_var.set(tr("状态: 正常"))
                            api_status_label.configure(foreground="green")
                        else:
                            api_status_var.set(tr("状态: 异常"))
                            api_status_label.configure(foreground="red")
                    
                    config_window.after(0, update_ui)
                
                # 启动测试线程
                import threading
                threading.Thread(target=api_test_thread, daemon=True).start()
                
            except Exception as e:
                messagebox.showerror(tr("错误"), f"API测试失败: {str(e)}", parent=config_window)
                api_status_var.set(tr("状态: 未测试"))
                api_status_label.configure(foreground="#666666")
        
        # 工作流操作按钮框架
        workflow_btn_frame = ttk.Frame(current_frame)
        workflow_btn_frame.pack(pady=(0, 20), padx=10)
        
        # 选定工作流按钮（原使用该工作流）
        def select_workflow():
            """选定工作流"""
            selected_items = file_list.selection()
            if not selected_items:
                messagebox.showwarning("提示", "请选择要使用的工作流文件", parent=config_window)
                return
            
            selected_item = selected_items[0]
            display_name = file_list.item(selected_item, "values")[1]
            
            # 提取原始文件名（去掉图标）
            selected_file = display_name
            if display_name.startswith("📁 "):
                selected_file = display_name[2:-1]  # 去掉📁 和末尾的/
            elif display_name.startswith("📄 "):
                selected_file = display_name[2:]  # 去掉📄 图标
            elif display_name.startswith("(暂无文件或文件夹)"):
                # 跳过提示信息
                return
            
            # 更新配置 - 使用相对路径
            # 使用当前浏览的目录
            workflow_path = os.path.join(current_dir, selected_file)
            # 转换为相对路径
            workflow_path = os.path.relpath(workflow_path, os.path.dirname(os.path.abspath(__file__)))
            if not self.config.has_section("comfyui_gen"):
                self.config["comfyui_gen"] = {}
            self.config["comfyui_gen"]["workflow_path"] = workflow_path
            # 同时更新ComfyUI部分的workflow_path配置
            if not self.config.has_section("ComfyUI"):
                self.config["ComfyUI"] = {}
            self.config["ComfyUI"]["workflow_path"] = workflow_path
            
            try:
                # 直接读取源文件进行验证 - 使用绝对路径
                abs_workflow_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), workflow_path))
                with open(abs_workflow_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 更新显示
                current_workflow_var.set(f"当前使用: {selected_file}")
                # 重置API状态为未测试
                api_status_var.set("API状态: 未测试")
                api_status_label.configure(foreground="#666666")
                self.save_config()
                # 更新主程序中的工作流路径和显示
                self.WORKFLOW_PATH = workflow_path
                if hasattr(self, "workflow_file_label"):
                    self.workflow_file_label.config(text=selected_file)
                
                # 更新workflow_path和对应的ini_path实例变量
                self.workflow_path = self.WORKFLOW_PATH
                # 根据workflow_path自动生成对应的ini_path
                self.ini_path = os.path.splitext(self.workflow_path)[0] + ".ini"
                
                # 更新INI文件名称显示 - 使用JSON到INI的绑定规则：相同文件名，不同扩展名
                current_ini_file = os.path.splitext(selected_file)[0] + ".ini"
                current_ini_var.set(f"当前脚本: {current_ini_file}")
                
                # 读取并更新负面提示词
                # 生成对应的INI文件路径
                ini_path = os.path.splitext(workflow_path)[0] + ".ini"
                
                # 读取INI文件获取负面提示词
                if os.path.exists(ini_path):
                    # 使用MultiConfigParser处理重复section
                    config = MultiConfigParser()
                    config.read(ini_path, encoding='utf-8')
                        
                    # 获取所有section名称
                    sections = config.sections()
                        
                    # 更新索引显示
                    if hasattr(self, "ini_sections_var"):
                        # 格式化sections为字符串
                        sections_str = ",".join([f"[{section}]" for section in sections])
                        self.ini_sections_var.set(f"索引-{sections_str}")
                        
                        # 检查工作流类型，动态调整必需的sections
                        has_image_load = any(section == "图片载入" or section.startswith("图片载入_") for section in sections)
                        has_positive_prompt = any(section == "正向提示词" or section.startswith("正向提示词_") for section in sections)
                        
                        # 验证所有sections是否都在允许的索引名列表中
                        invalid_sections = []
                        allowed_base_names = [name.strip('[]') for name in self.allowed_index_names]
                        # 检查每个section是否在允许的索引名列表中
                        for section in sections:
                            # 提取section的基础名称（去掉可能的后缀，如"正向提示词_3"）
                            section_base = section.split('_')[0]
                            # 检查是否在允许的列表中
                            if section_base not in allowed_base_names:
                                invalid_sections.append(section)
                        
                        # 如果存在无效的sections，显示错误提示
                        if invalid_sections:
                            messagebox.showerror("规则匹配失败", f"所选工作流的INI文件包含以下无效的功能模块：\n{', '.join(invalid_sections)}\n\n允许的功能模块：\n{', '.join(self.allowed_index_names)}")
                            return
                        
                        # 初始化标志位
                        has_positive_prompt = False
                        has_negative_prompt = False
                        
                        # 遍历所有section查找配置
                        for i, section in enumerate(config.sections()):
                            if section == '正向提示词':
                                has_positive_prompt = True
                                # 提取参数值
                                positive_prompt = config._section_data[i].get('参数值', '')
                                
                                # 只有当参数值不为空时，才设置到文本框中
                                if positive_prompt.strip():
                                    # 设置所有中文正向提示词文本框的内容
                                    for text_box in self.prompt_texts:
                                        text_box.delete("1.0", tk.END)
                                        text_box.insert("1.0", positive_prompt)
                                        # 更新文本框颜色为正常文本颜色
                                        self.set_textbox_color(text_box, "中文提示词")
                            
                            elif section == '负面提示词':
                                has_negative_prompt = True
                                # 提取参数值
                                negative_prompt = config._section_data[i].get('参数值', '')
                                
                                # 只有当参数值不为空时，才设置到文本框中
                                if negative_prompt.strip():
                                    # 设置所有中文负面提示词文本框的内容
                                    for text_box in self.negative_prompt_texts:
                                        text_box.delete("1.0", tk.END)
                                        text_box.insert("1.0", negative_prompt)
                                        # 更新文本框颜色为正常文本颜色
                                        self.set_textbox_color(text_box, "中文负面提示词")
                            
                            # 处理K采样步值
                            elif section == 'K采样步值':
                                # 提取参数值
                                k_sampler_steps = config._section_data[i].get('参数值', '')
                                
                                # 更新全局和所有行的K采样器步数
                                if k_sampler_steps:
                                    # 更新全局参数
                                    if hasattr(self, 'global_k_sampler_steps'):
                                        self.global_k_sampler_steps.set(k_sampler_steps)
                                    # 更新所有行参数
                                    if hasattr(self, 'k_sampler_steps_list'):
                                        for var in self.k_sampler_steps_list:
                                            var.set(k_sampler_steps)
                            
                            # 处理图片尺寸宽度
                            elif section == '图片尺寸宽度':
                                # 提取参数值
                                image_width = config._section_data[i].get('参数值', '')
                                
                                # 更新全局和所有行的图片尺寸宽度
                                if image_width:
                                    # 更新全局参数
                                    if hasattr(self, 'global_image_width'):
                                        self.global_image_width.set(image_width)
                                    # 更新所有行参数
                                    if hasattr(self, 'image_width_list'):
                                        for var in self.image_width_list:
                                            var.set(image_width)
                            
                            # 处理图片尺寸高度
                            elif section == '图片尺寸高度':
                                # 提取参数值
                                image_height = config._section_data[i].get('参数值', '')
                                
                                # 更新全局和所有行的图片尺寸高度
                                if image_height:
                                    # 更新全局参数
                                    if hasattr(self, 'global_image_height'):
                                        self.global_image_height.set(image_height)
                                    # 更新所有行参数
                                    if hasattr(self, 'image_height_list'):
                                        for var in self.image_height_list:
                                            var.set(image_height)
                        
                        # 更新标志位
                        self.has_positive_prompt = has_positive_prompt
                        self.has_negative_prompt = has_negative_prompt
                        self.has_image_load = has_image_load  # 新增：保存图片载入模块标志位
                        
                        # 重新创建get_frame_visibility函数，确保使用最新的配置
                        def get_frame_visibility(frame_name):
                            # 默认显示所有框架
                            default_visibility = True
                            
                            try:
                                import configparser
                                import os
                                
                                ini_config = configparser.ConfigParser()
                                
                                # 读取当前工作流对应的INI文件（如果存在）
                                if hasattr(self, "ini_path") and os.path.exists(self.ini_path):
                                    try:
                                        with open(self.ini_path, 'r', encoding='utf-8-sig') as f:
                                            ini_config.read_file(f)
                                    except Exception as e:
                                        print(f"警告: 无法读取工作流INI文件 '{self.ini_path}': {str(e)}")
                                
                                # 同时读取主配置文件，作为备用
                                try:
                                    with open("setting.ini", 'r', encoding='utf-8-sig') as f:
                                        ini_config.read_file(f)
                                except Exception as e:
                                    print(f"警告: 无法读取主配置文件 'setting.ini': {str(e)}")
                                
                                # 根据当前工作流类型确定配置节
                                workflow_type = self.config.get("ComfyUI", "workflow_path", fallback="图生图")
                                section = "FrameVisibility_ImageToImage"
                                
                                # 从配置文件中读取所有可用模式
                                if self.config.has_section("FrameVisibility_Modes"):
                                    for mode_config in self.config.items("FrameVisibility_Modes"):
                                        mode_name = mode_config[0]
                                        mode_info = mode_config[1]
                                        
                                        mode_parts = mode_info.split(",")
                                        if len(mode_parts) >= 2:
                                            mode_section = mode_parts[0].strip()
                                            workflow_identifier = mode_parts[1].strip()
                                            
                                            if workflow_identifier in workflow_type:
                                                section = mode_section
                                                break
                                
                                # 读取配置
                                visibility = ini_config.get(section, frame_name, fallback="Y")
                                return visibility.upper() == "Y"
                            except Exception as e:
                                print(f"获取框架可见性时出错: {str(e)}")
                                return default_visibility
                        
                        # 获取当前行数
                        config_rows = self.config.get("System", "content_rows", fallback="30")
                        content_rows = int(config_rows) if config_rows.isdigit() and int(config_rows) > 0 else 30
                        print(f"当前行数: {content_rows}")
                        
                        # 控制No.框体可见性
                        if hasattr(self, "content_no_frames"):
                            print(f"No.框体数量: {len(self.content_no_frames)}")
                            no_frame_visible = get_frame_visibility("no_frame")
                            print(f"No.框体可见性配置: {no_frame_visible}")
            
                            # 只处理与当前行数对应的框架实例
                            for i in range(content_rows):
                                if i < len(self.content_no_frames):
                                    no_frame = self.content_no_frames[i]
                                    base_row = 2 + i * 2
                                    if no_frame_visible:
                                        no_frame.grid(row=base_row, column=0, rowspan=2, padx=3, pady=3, sticky=tk.NSEW)
                                    else:
                                        no_frame.grid_forget()
                        
                        # 根据工作流类型控制图片框体可见性
                        if hasattr(self, "content_img_frames"):
                            # 确定工作流类型：文生图工作流（有正向提示词但没有图片载入）
                            is_text_to_image = has_positive_prompt and not has_image_load
                            
                            print(f"工作流类型检测: 有正向提示词={has_positive_prompt}, 有图片载入={has_image_load}, 是文生图={is_text_to_image}")
                            print(f"图片框体数量: {len(self.content_img_frames)}")
                            
                            img_frame_visible = get_frame_visibility("img_frame")
                            print(f"图片框体可见性配置: {img_frame_visible}")
                            print(f"工作流类型: 文生图={is_text_to_image}")
                            
                            # 优先尊重配置文件中的设置
                            # 只有当配置文件中明确设置为隐藏，或者工作流类型为文生图时才隐藏
                            # 但如果配置文件中明确设置为显示，即使是文生图工作流也应该显示
                            for i, img_frame in enumerate(self.content_img_frames):
                                base_row = 2 + i * 2
                                # 配置文件中明确设置为显示，或者是图生图工作流
                                if img_frame_visible:
                                    print(f"显示图片框体 {i+1}")
                                    img_frame.grid(row=base_row, column=1, rowspan=2, padx=3, pady=3, sticky=tk.NSEW)
                                else:
                                    print(f"隐藏图片框体 {i+1}")
                                    img_frame.grid_forget()
                        
                        # 根据标志位隐藏/显示控件
                        self.toggle_prompt_widgets()
                
                # 直接生效，不弹出提示窗口
                print(f"已成功选定工作流: {selected_file}")
                
                # 记录框架可见性配置到日志
                self.log_frame_visibility()
            except Exception as e:
                messagebox.showerror("错误", f"选定工作流失败: {str(e)}", parent=config_window)
        
        select_btn = ttk.Button(workflow_btn_frame, text=tr("选定工作流"), command=select_workflow, style="danger.TButton")
        select_btn.pack(side=tk.LEFT, padx=5)
        
        # 目录导航相关变量
        dir_history = []
        current_dir = self.api_dir
        
        # 双击文件列表事件处理
        def on_file_double_click(event):
            """双击文件列表项处理"""
            nonlocal dir_history, current_dir
            selected_items = file_list.selection()
            if not selected_items:
                return
            
            selected_item = selected_items[0]
            display_name = file_list.item(selected_item, "values")[1]
            
            # 提取原始文件名（去掉图标）
            if display_name.startswith("← "):
                # 是返回上一级选项
                if dir_history:
                    # 弹出当前目录，返回上一级目录
                    current_dir = dir_history.pop()
                    # 重新加载文件列表
                    load_file_list()
            elif display_name.startswith("📁 "):
                # 是文件夹，进入该文件夹
                folder_name = display_name[2:-1]  # 去掉📁 和末尾的/
                folder_path = os.path.join(current_dir, folder_name)
                
                # 将当前目录添加到历史记录
                dir_history.append(current_dir)
                
                # 更新当前目录
                current_dir = folder_path
                
                # 重新加载文件列表
                load_file_list()
            elif display_name.startswith("📄 "):
                # 是JSON文件，显示确认弹窗
                if messagebox.askyesno("确认", f"是否选择该comfyui工作流: {display_name}？", parent=config_window):
                    select_workflow()
            elif display_name.startswith("(暂无文件或文件夹)"):
                # 跳过提示信息
                return
        
        # 返回上一级目录
        def go_back():
            """返回上一级目录"""
            nonlocal dir_history, current_dir
            if dir_history:
                # 弹出当前目录，返回上一级目录
                current_dir = dir_history.pop()
                
                # 重新加载文件列表
                load_file_list()
        
        # 重新定义load_file_list函数，使其使用current_dir
        def load_file_list():
            '''加载ComfyUI文件列表'''
            nonlocal current_dir, dir_history
            # 清空现有列表
            for item in file_list.get_children():
                file_list.delete(item)
            # 如果目录不存在，创建目录
            if not os.path.exists(current_dir):
                os.makedirs(current_dir)
            
            # 添加返回上一级选项（如果有历史记录）
            if dir_history:
                file_list.insert("", tk.END, values=("-", "← 返回上一级"))
            
            # 获取所有JSON文件和文件夹
            all_items = []
            for item in os.listdir(current_dir):
                item_path = os.path.join(current_dir, item)
                if os.path.isdir(item_path) or item.endswith(".json"):
                    all_items.append(item)
            # 按名称排序，文件夹在前，文件在后
            all_items.sort(key=lambda x: (os.path.isfile(os.path.join(current_dir, x)), x))
            # 添加到Treeview
            start_index = 2 if dir_history else 1  # 如果有返回项，从2开始编号
            for i, item in enumerate(all_items, start_index):
                item_path = os.path.join(current_dir, item)
                if os.path.isdir(item_path):
                    # 文件夹：添加文件夹图标和斜杠标识
                    display_name = f"📁 {item}/"
                else:
                    # JSON文件：添加文件图标
                    display_name = f"📄 {item}"
                file_list.insert("", tk.END, values=(i-1, display_name))  # 调整序号，返回项为"-"
            # 如果没有文件，提示用户
            if not all_items:
                if not dir_history:
                    # 如果没有返回项且没有文件，显示提示
                    file_list.insert("", tk.END, values=(1, "(暂无文件或文件夹)"))
                else:
                    # 如果有返回项但没有文件，显示提示（序号为2）
                    file_list.insert("", tk.END, values=(2, "(暂无文件或文件夹)"))
        # 当前目录显示
        current_dir_var = tk.StringVar(value=f"当前目录: {current_dir}")
        current_dir_label = ttk.Label(file_frame, textvariable=current_dir_var)
        current_dir_label.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        # 绑定双击事件
        file_list.bind("<Double-1>", on_file_double_click)
        
        # 测试API按钮
        test_api_btn = ttk.Button(workflow_btn_frame, text=tr("测试API"), command=test_selected_api, style="primary.TButton")
        test_api_btn.pack(side=tk.LEFT, padx=5)
        
        # 取消按钮
        def cancel_and_close():
            """取消并关闭窗口"""
            config_window.destroy()
        
        cancel_btn = ttk.Button(workflow_btn_frame, text=tr("取消"), command=cancel_and_close)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        

        # 重命名按钮
        def rename_file():
            """重命名文件"""
            selected_items = file_list.selection()
            if not selected_items:
                messagebox.showwarning("提示", "请选择要重命名的文件", parent=config_window)
                return
            
            selected_item = selected_items[0]
            display_name = file_list.item(selected_item, "values")[1]
            
            # 提取原始文件名（去掉图标）
            selected_file = display_name
            if display_name.startswith("📁 "):
                selected_file = display_name[2:-1]  # 去掉📁 和末尾的/
            elif display_name.startswith("📄 "):
                selected_file = display_name[2:]  # 去掉📄 图标
            elif display_name.startswith("(暂无文件或文件夹)"):
                # 跳过提示信息
                return
            
            # 创建重命名对话框
            rename_window = tk.Toplevel(config_window)
            rename_window.title("重命名文件")
            rename_window.geometry("400x250")
            rename_window.transient(config_window)
            rename_window.grab_set()
            # 居中于主窗口
            rename_window.update_idletasks()
            x = config_window.winfo_x() + (config_window.winfo_width() // 2) - (rename_window.winfo_width() // 2)
            y = config_window.winfo_y() + (config_window.winfo_height() // 2) - (rename_window.winfo_height() // 2)
            rename_window.geometry(f"+{x}+{y}")
            
            frame = ttk.Frame(rename_window, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(frame, text="新文件名:").pack(pady=10, anchor='w')
            new_name_var = tk.StringVar(value=selected_file)
            entry = ttk.Entry(frame, textvariable=new_name_var, width=60)
            entry.pack(pady=10, anchor='w')
            
            def do_rename():
                new_name = new_name_var.get().strip()
                if not new_name:
                    messagebox.showwarning("提示", "文件名不能为空", parent=rename_window)
                    return
                
                if not new_name.endswith(".json"):
                    new_name += ".json"
                
                comfyui_api_dir = os.path.join("config", "API", "confiui_api")
                old_path = os.path.join(comfyui_api_dir, selected_file)
                new_path = os.path.join(comfyui_api_dir, new_name)
                
                if os.path.exists(new_path):
                    messagebox.showwarning("提示", "文件名已存在", parent=rename_window)
                    return
                
                try:
                    os.rename(old_path, new_path)
                    # 更新Treeview
                    load_file_list()
                    rename_window.destroy()
                    messagebox.showinfo("提示", "重命名成功", parent=config_window)
                except Exception as e:
                    messagebox.showerror("错误", f"重命名失败: {str(e)}", parent=rename_window)
            
            ttk.Button(frame, text="确定", command=do_rename).pack(side=tk.LEFT, padx=5, pady=20)
            ttk.Button(frame, text="取消", command=rename_window.destroy).pack(side=tk.LEFT, padx=5, pady=20)
        
        rename_btn = ttk.Button(right_btn_frame, text=tr("重命名"), command=rename_file)
        rename_btn.pack(pady=5, fill=tk.X)
        
        # 删除按钮
        def delete_file():
            """删除文件，支持多选"""
            selected_items = file_list.selection()
            if not selected_items:
                messagebox.showwarning("提示", "请选择要删除的文件", parent=config_window)
                return
            
            # 获取选中的所有文件名
            display_names = [file_list.item(item, "values")[1] for item in selected_items]
            
            # 提取原始文件名（去掉图标）
            selected_files = []
            for display_name in display_names:
                if display_name.startswith("📁 "):
                    selected_files.append(display_name[2:-1])  # 去掉📁 和末尾的/
                elif display_name.startswith("📄 "):
                    selected_files.append(display_name[2:])  # 去掉📄 图标
                elif display_name.startswith("(暂无文件或文件夹)"):
                    # 跳过提示信息
                    continue
                else:
                    selected_files.append(display_name)
            
            # 确认删除
            if messagebox.askyesno("确认", f"确定要删除选中的 {len(selected_files)} 个文件吗？", parent=config_window):
                comfyui_api_dir = os.path.join("config", "API", "confiui_api")
                success_count = 0
                error_count = 0
                
                for filename in selected_files:
                    file_path = os.path.join(comfyui_api_dir, filename)
                    try:
                        os.remove(file_path)
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"删除文件 '{filename}' 失败: {str(e)}")
                
                # 更新Treeview
                load_file_list()
                
                if error_count == 0:
                    messagebox.showinfo("提示", f"成功删除 {success_count} 个文件", parent=config_window)
                else:
                    messagebox.showwarning("提示", f"成功删除 {success_count} 个文件，失败 {error_count} 个文件", parent=config_window)
        
        delete_btn = ttk.Button(right_btn_frame, text=tr("删除"), command=delete_file)
        delete_btn.pack(pady=5, fill=tk.X)
        
        # 刷新列表按钮
        refresh_btn = ttk.Button(right_btn_frame, text=tr("刷新列表"), command=load_file_list)
        refresh_btn.pack(pady=5, fill=tk.X)
        
        # 导入按钮
        def import_file():
            """导入文件"""
            file_path = filedialog.askopenfilename(
                title="选择要导入的JSON文件",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
            )
            if not file_path:
                return
            
            comfyui_api_dir = os.path.join("config", "API", "confiui_api")
            filename = os.path.basename(file_path)
            dest_path = os.path.join(comfyui_api_dir, filename)
            
            if os.path.exists(dest_path):
                if not messagebox.askyesno("确认", "文件已存在，是否覆盖？", parent=config_window):
                    return
            
            try:
                shutil.copy2(file_path, dest_path)
                # 更新Treeview
                load_file_list()
                messagebox.showinfo("提示", "导入成功", parent=config_window)
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {str(e)}", parent=config_window)
        
        import_btn = ttk.Button(right_btn_frame, text=tr("导入"), command=import_file)
        import_btn.pack(pady=5, fill=tk.X)
        
        # 导出按钮
        def export_file():
            """导出文件，支持多选"""
            selected_items = file_list.selection()
            if not selected_items:
                messagebox.showwarning("提示", "请选择要导出的文件", parent=config_window)
                return
            
            # 获取选中的所有文件名
            selected_files = [file_list.item(item, "values")[1] for item in selected_items]
            comfyui_api_dir = os.path.join("config", "API", "confiui_api")
            
            if len(selected_files) == 1:
                # 单个文件导出
                selected_file = selected_files[0]
                file_path = os.path.join(comfyui_api_dir, selected_file)
                
                save_path = filedialog.asksaveasfilename(
                    title="导出文件",
                    defaultextension=".json",
                    filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
                    initialfile=selected_file
                )
                if not save_path:
                    return
                
                try:
                    shutil.copy2(file_path, save_path)
                    messagebox.showinfo("提示", "导出成功", parent=config_window)
                except Exception as e:
                    messagebox.showerror("错误", f"导出失败: {str(e)}", parent=config_window)
            else:
                # 多个文件导出
                export_dir = filedialog.askdirectory(title="选择导出目录")
                if not export_dir:
                    return
                
                success_count = 0
                error_count = 0
                
                for filename in selected_files:
                    source_path = os.path.join(comfyui_api_dir, filename)
                    target_path = os.path.join(export_dir, filename)
                    
                    try:
                        shutil.copy2(source_path, target_path)
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"导出文件 '{filename}' 失败: {str(e)}")
                
                if error_count == 0:
                    messagebox.showinfo("提示", f"成功导出 {success_count} 个文件", parent=config_window)
                else:
                    messagebox.showwarning("提示", f"成功导出 {success_count} 个文件，失败 {error_count} 个文件", parent=config_window)
        
        export_btn = ttk.Button(right_btn_frame, text=tr("导出"), command=export_file)
        export_btn.pack(pady=5, fill=tk.X)
        
        # ini编辑按钮
        def open_ini_edit():
            """打开INI编辑窗口"""
            JsonToIniDebugWindow(config_window)
        
        # 使用淡黄色样式，在ttkbootstrap中对应的样式名称是"warning.TButton"
        ini_edit_btn = ttk.Button(right_btn_frame, text=tr("ini编辑"), command=open_ini_edit, style="warning.TButton")
        ini_edit_btn.pack(pady=5, fill=tk.X)
        

    
    def show_system_settings(self):
        """显示系统设置对话框，用于修改API超时时间"""
        # 创建系统设置对话框
        settings_window = tk.Toplevel(self.root)
        settings_window.title(tr("系统设置"))
        settings_window.geometry("500x500")
        settings_window.resizable(False, False)
        
        # 设置对话框置顶
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # 居中显示
        settings_window.update_idletasks()
        width = settings_window.winfo_width()
        height = settings_window.winfo_height()
        x = (self.root.winfo_width() // 2) - (width // 2) + self.root.winfo_x()
        y = (self.root.winfo_height() // 2) - (height // 2) + self.root.winfo_y()
        settings_window.geometry(f"+{x}+{y}")
        
        # 添加ESC键绑定，按ESC键关闭窗口
        settings_window.bind("<Escape>", lambda e: settings_window.destroy())
        
        main_frame = ttk.Frame(settings_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加标题
        title_label = ttk.Label(main_frame, text=tr("系统设置"), font=("宋体", 14, "bold"))
        title_label.pack(pady=10)
        
        # API超时时间设置
        timeout_frame = ttk.Frame(main_frame)
        timeout_frame.pack(fill=tk.X, pady=10)
        
        timeout_label = ttk.Label(timeout_frame, text=tr("生图API超时时间(分钟):"), width=18, anchor=tk.W)
        timeout_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 将秒转换为分钟显示
        timeout_var = tk.StringVar(value=str(round(self.TIMEOUT / 60)))
        timeout_entry = ttk.Entry(timeout_frame, textvariable=timeout_var, width=20)
        timeout_entry.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
        



        


        



        


        
        # 字符大小设置
        font_size_frame = ttk.Frame(main_frame)
        font_size_frame.pack(fill=tk.X, pady=10)
        
        font_size_label = ttk.Label(font_size_frame, text=tr("文本框字符大小:"), width=18, anchor=tk.W)
        font_size_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 获取当前字符大小设置，默认10
        current_font_size = int(self.config.get("UI", "font_size", fallback="10"))
        font_size_var = tk.IntVar(value=current_font_size)
        
        font_size_combobox = ttk.Combobox(font_size_frame, values=[8, 10, 12], textvariable=font_size_var, width=20, state="readonly")
        font_size_combobox.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
        
        # 主题选择设置
        theme_frame = ttk.Frame(main_frame)
        theme_frame.pack(fill=tk.X, pady=10)
        
        theme_label = ttk.Label(theme_frame, text=tr("程序主题:"), width=15, anchor=tk.W)
        theme_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 为ttkbootstrap主题添加有意境的中文描述
        theme_descriptions = {
            "cosmo": tr("宇宙星空"),
            "flatly": tr("清新简约"),
            "journal": tr("典雅日记"),
            "readable": tr("清晰可读"),
            "simplex": tr("极简主义"),
            "united": tr("和谐统一"),
            "darkly": tr("深邃暗黑"),
            "slate": tr("沉稳石板"),
            "solar": tr("阳光活力"),
            "cyborg": tr("未来机械"),
            "vapor": tr("蒸汽波"),
            "minty": tr("薄荷清新"),
            "litera": tr("轻盈文学"),
            "lumen": tr("明亮光感"),
            "morph": tr("形态变换"),
            "pulse": tr("律动脉搏"),
            "sketchy": tr("手绘涂鸦"),
            "cerculean": tr("海蓝梦境"),
            "superhero": tr("超级英雄"),
            "sandstone": tr("砂岩质感"),
            "yeti": tr("雪山精灵"),
            "zephyr": tr("和风轻语")
        }
        
        # 获取可用的ttkbootstrap主题
        style = ttk.Style()
        available_themes = style.theme_names()
        
        # 创建带中文描述的主题列表
        themed_theme_list = []
        for theme in available_themes:
            desc = theme_descriptions.get(theme, tr("默认主题"))
            themed_theme_list.append(f"{theme} (*{desc}*)")
        
        # 获取当前主题
        current_theme = self.config.get("UI", "theme", fallback="cosmo")
        current_theme_with_desc = f"{current_theme} (*{theme_descriptions.get(current_theme, tr('默认主题'))}*)"
        theme_var = tk.StringVar(value=current_theme_with_desc)
        
        # 初始化预览窗口变量
        preview_window = None
        preview_label = None
        dropdown_window = None
        dropdown_listbox = None
        
        # 主题预览函数
        def show_theme_preview(theme_name, x, y):
            """显示主题预览图片"""
            nonlocal preview_window, preview_label
            
            # 主题图片路径
            theme_image_path = os.path.join("config", "theme", "image", f"{theme_name}.png")
            
            # 检查图片文件是否存在
            if os.path.exists(theme_image_path):
                # 如果预览窗口不存在，创建一个
                if not preview_window:
                    preview_window = tk.Toplevel(self.root)
                    preview_window.title(tr("主题预览"))
                    preview_window.geometry("300x300")
                    preview_window.overrideredirect(True)  # 无边框
                    preview_window.transient(self.root)  # 始终在主窗口上方
                    
                    # 创建一个带白色边框的容器
                    border_frame = tk.Frame(preview_window, bg="white", bd=3, relief=tk.SUNKEN)
                    border_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                    
                    # 创建图片标签
                    preview_label = ttk.Label(border_frame)
                    preview_label.pack(fill=tk.BOTH, expand=True)
                
                # 加载并显示图片
                from PIL import Image, ImageTk
                image = Image.open(theme_image_path)
                # 调整图片大小为300x300
                image = image.resize((290, 290), Image.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                preview_label.config(image=photo)
                preview_label.image = photo  # 保存引用
                
                # 显示预览窗口
                preview_window.geometry(f"310x310+{x}+{y}")
                preview_window.deiconify()
        
        # 隐藏预览窗口函数
        def hide_theme_preview():
            """隐藏主题预览图片"""
            nonlocal preview_window
            if preview_window:
                preview_window.withdraw()
        
        # 隐藏下拉菜单函数
        def hide_dropdown():
            """隐藏下拉菜单"""
            nonlocal dropdown_window
            if dropdown_window:
                dropdown_window.destroy()
                dropdown_window = None
            hide_theme_preview()
        
        # 主题选择函数
        def select_theme(event):
            """选择主题"""
            nonlocal dropdown_listbox, dropdown_window
            if dropdown_listbox:
                # 获取选中的索引
                index = dropdown_listbox.curselection()
                if index:
                    selected_theme_with_desc = dropdown_listbox.get(index)
                    theme_var.set(selected_theme_with_desc)
                    hide_dropdown()
        
        # 鼠标悬停在Listbox项目上时的处理函数
        def on_listbox_hover(event):
            """处理鼠标悬停在Listbox项目上的事件"""
            nonlocal dropdown_listbox
            if dropdown_listbox:
                # 获取当前鼠标位置
                x = event.x_root + 10
                y = event.y_root + 10
                
                # 获取鼠标悬停的项目索引
                index = dropdown_listbox.nearest(event.y)
                if index >= 0:
                    # 获取主题名称（去掉描述部分）
                    theme_with_desc = dropdown_listbox.get(index)
                    theme_name = theme_with_desc.split()[0]
                    show_theme_preview(theme_name, x, y)
        
        # 打开下拉菜单函数
        def open_dropdown(event=None):
            """打开下拉菜单"""
            nonlocal dropdown_window, dropdown_listbox
            
            # 如果下拉菜单已存在，先销毁
            if dropdown_window:
                hide_dropdown()
            
            # 获取主题显示框的位置和大小
            display_x = theme_display_frame.winfo_rootx()
            display_y = theme_display_frame.winfo_rooty()
            display_height = theme_display_frame.winfo_height()
            
            # 计算下拉菜单的位置
            x = display_x
            y = display_y + display_height
            
            # 确保下拉菜单位置在屏幕可见范围内
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # 调整下拉菜单位置，确保不超出屏幕边界
            if x + 300 > screen_width:
                x = screen_width - 310
            if y + 250 > screen_height:
                y = y - 260  # 向上显示
            
            print(f"[DEBUG] Final dropdown window position: x={x}, y={y}")
            
            # 创建下拉菜单窗口
            dropdown_window = tk.Toplevel(self.root)  # 以主窗口为父窗口
            dropdown_window.geometry(f"300x250+{x}+{y}")
            dropdown_window.title(tr("主题选择"))
            dropdown_window.transient(self.root)  # 始终在主窗口上方
            dropdown_window.attributes("-topmost", True)  # 确保始终在最上层
            
            # 设置下拉窗口背景色，确保可见
            dropdown_window.configure(bg="white")  # 使用白色背景
            
            # 使用最基础的Listbox配置，确保可见
            dropdown_listbox = tk.Listbox(dropdown_window, width=40, height=10, font=("宋体", 10), 
                                        bg="white", fg="black", relief=tk.SUNKEN, borderwidth=2)
            dropdown_listbox.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            
            # 确保Listbox可见
            dropdown_listbox.configure(state="normal")
            dropdown_listbox.lift()  # 确保Listbox在最上层
            
            # 添加主题选项
            print(f"[DEBUG] Adding {len(themed_theme_list)} theme options to Listbox")
            for i, theme in enumerate(themed_theme_list):
                dropdown_listbox.insert(tk.END, theme)
                print(f"[DEBUG] Added theme {i+1}: {theme}")
            
            # 选择当前主题
            try:
                current_index = themed_theme_list.index(theme_var.get())
                dropdown_listbox.select_set(current_index)
                dropdown_listbox.see(current_index)
                print(f"[DEBUG] Selected current theme at index {current_index}")
            except ValueError as e:
                print(f"[DEBUG] Error selecting current theme: {e}")
                print(f"[DEBUG] Current theme var value: {theme_var.get()}")
                print(f"[DEBUG] Themed theme list: {themed_theme_list}")
            
            # 强制更新窗口，确保可见
            dropdown_window.update_idletasks()
            dropdown_window.deiconify()
            dropdown_window.lift()
            
            # 打印最终的窗口状态
            print(f"[DEBUG] Dropdown window created successfully. Geometry: {dropdown_window.geometry()}")
            print(f"[DEBUG] Dropdown window is visible: {dropdown_window.winfo_ismapped()}")
            print(f"[DEBUG] Listbox is visible: {dropdown_listbox.winfo_ismapped()}")
            print(f"[DEBUG] Number of items in Listbox: {dropdown_listbox.size()}")
            
            # 绑定事件
            dropdown_listbox.bind("<Double-1>", select_theme)  # 双击选择
            dropdown_listbox.bind("<Return>", select_theme)  # Enter键选择
            dropdown_listbox.bind("<FocusOut>", lambda e: hide_dropdown())  # 失去焦点时关闭
            dropdown_listbox.bind("<Motion>", on_listbox_hover)  # 鼠标移动时预览
            dropdown_listbox.bind("<Leave>", lambda e: hide_theme_preview())  # 离开Listbox时隐藏预览
            dropdown_listbox.bind("<Escape>", lambda e: hide_dropdown())  # ESC键关闭
            
            # 让Listbox获得焦点
            dropdown_listbox.focus_set()
        
        # 创建标准的ttk.Combobox用于主题选择
        theme_combobox = ttk.Combobox(theme_frame, values=themed_theme_list, textvariable=theme_var, width=30, state="readonly")
        theme_combobox.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
        
        # 主题选择事件处理函数
        def on_theme_selected(event):
            """当选择主题时显示预览图"""
            # 获取选中的主题文本
            selected_theme_with_desc = theme_var.get()
            # 提取主题名称
            theme_name = selected_theme_with_desc.split()[0]
            # 显示预览图
            x = theme_combobox.winfo_rootx() + theme_combobox.winfo_width() + 10
            y = theme_combobox.winfo_rooty()
            show_theme_preview(theme_name, x, y)
        
        # 绑定主题选择事件
        theme_combobox.bind("<<ComboboxSelected>>", on_theme_selected)
        
        # 为combobox添加鼠标悬停事件，显示主题预览
        def on_combobox_hover(event):
            """当鼠标悬停在combobox上时显示当前主题预览"""
            # 获取当前主题
            current_theme_with_desc = theme_var.get()
            theme_name = current_theme_with_desc.split()[0]
            # 显示预览图
            x = theme_combobox.winfo_rootx() + theme_combobox.winfo_width() + 10
            y = theme_combobox.winfo_rooty()
            show_theme_preview(theme_name, x, y)
        
        # 为combobox添加鼠标离开事件，隐藏主题预览
        def on_combobox_leave(event):
            """当鼠标离开combobox时隐藏主题预览"""
            hide_theme_preview()
        
        # 绑定鼠标悬停和离开事件
        theme_combobox.bind("<Enter>", on_combobox_hover)
        theme_combobox.bind("<Leave>", on_combobox_leave)
        
        # 解决全局鼠标滚轮事件冲突问题
        # 保存原始的鼠标滚轮处理函数
        # 注意：在tkinter中，bind_all返回的是一个字符串，不是函数引用
        # 所以我们需要自定义处理方式
        
        # 定义原始的鼠标滚轮处理函数
        def original_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # 重新绑定鼠标滚轮事件
        self.canvas.bind_all("<MouseWheel>", original_mousewheel)
        
        # 为系统设置窗口绑定关闭事件，不需要特殊处理，因为我们使用的是自定义函数
        def on_window_close():
            """窗口关闭时的处理函数"""
            pass
        
        # 为系统设置窗口绑定关闭事件
        settings_window.protocol("WM_DELETE_WINDOW", lambda: [settings_window.destroy()])
        
        # 保存按钮处理函数
        def save_settings():
            """保存设置"""
            try:
                new_timeout_minutes = int(timeout_var.get())
                if new_timeout_minutes <= 0:
                    raise ValueError("超时时间必须大于0")
                
                # 将分钟转换为秒
                new_timeout_seconds = new_timeout_minutes * 60
                
                # 更新配置
                self.TIMEOUT = new_timeout_seconds
                self.config["API"]["timeout"] = str(new_timeout_seconds)
                
                # 保存字符大小设置
                new_font_size = font_size_var.get()
                if "UI" not in self.config:
                    self.config["UI"] = {}
                self.config["UI"]["font_size"] = str(new_font_size)
                
                # 更新self.ui_font_size变量
                self.ui_font_size = new_font_size
                
                # 更新所有中文提示词文本框的字体大小
                if hasattr(self, "prompt_texts"):
                    for text_widget in self.prompt_texts:
                        text_widget.configure(font=('宋体', self.ui_font_size))
                
                # 更新所有英文翻译文本框的字体大小
                if hasattr(self, "english_texts"):
                    for text_widget in self.english_texts:
                        text_widget.configure(font=('宋体', self.ui_font_size))
                
                # 从选择的主题字符串中提取实际主题名称（去掉中文描述）
                selected_theme_with_desc = theme_var.get()
                new_theme = selected_theme_with_desc.split()[0]  # 提取主题名称部分
                
                # 更新主题配置
                # 保存到custom_theme配置项，标记为用户二次选择
                self.config["UI"]["custom_theme"] = new_theme
                # 同时保存到旧版配置项，确保兼容性
                self.config["UI"]["theme"] = new_theme
                
                self.save_config()
                




                





















                
                # 核心改进：在关闭对话框之前进行主题切换
                # 这样可以避免引用已销毁的组件导致错误
                try:
                    # 获取当前主题
                    current_style = ttk.Style()
                    current_theme = current_style.theme_use()
                    
                    # 只有当主题不同时才切换
                    if current_theme != new_theme:
                        # 直接切换主题
                        current_style.theme_use(new_theme)
                        
                        # 强制更新所有组件
                        self.root.update()
                        self.root.update_idletasks()
                        
                        # 刷新所有组件，确保文本框颜色跟随主题
                        self.refresh_all_components()
                except Exception as e:
                    # 忽略所有主题切换错误，不打印任何信息
                    pass
                
                # 关闭对话框
                settings_window.destroy()
                
                # 调用关闭处理函数，恢复全局鼠标滚轮绑定
                on_window_close()
                
                # 不显示任何提示框，保持界面整洁
            except ValueError as e:
                messagebox.showerror("错误", f"无效的超时时间: {e}")
        
        # 保存按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=20)
        
        # 保存按钮 - 使用上面定义的save_settings函数
        save_btn = ttk.Button(button_frame, text=tr("保存"), command=save_settings)
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        cancel_btn = ttk.Button(button_frame, text=tr("取消"), command=settings_window.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
    
    def show_push_settings(self):
        """显示Push设置对话框，用于管理设备信息推送"""
        # 创建Push设置对话框
        push_window = tk.Toplevel(self.root)
        push_window.title("Push设置")
        push_window.geometry("600x500")
        push_window.resizable(False, False)
        
        # 设置对话框置顶
        push_window.transient(self.root)
        push_window.grab_set()
        
        # 居中显示
        push_window.update_idletasks()
        width = push_window.winfo_width()
        height = push_window.winfo_height()
        x = (self.root.winfo_width() // 2) - (width // 2) + self.root.winfo_x()
        y = (self.root.winfo_height() // 2) - (height // 2) + self.root.winfo_y()
        push_window.geometry(f"+{x}+{y}")
        
        # PCInfoPusher 类实现
        class PCInfoPusher:
            def __init__(self, main_app):
                self.main_app = main_app
                self.logs = []
                self.device_id = self.get_device_id()
                self.version = self.get_version()
                self.push_status = False
                
                # 初始化Coze客户端
                self.coze_api_token = 'pat_YqXGZZyeD3x70NGUzDO7I5jIec3oajv4QaiW1fHxRC4wZwiWw7QAUyUxahSPgstN'
                self.coze_api_base = COZE_CN_BASE_URL
                self.coze = Coze(auth=TokenAuth(token=self.coze_api_token), base_url=self.coze_api_base)
                self.workflow_id = '7584502822159892507'
            
            def get_device_id(self):
                """获取设备ID"""
                try:
                    # 尝试获取Windows设备ID
                    if sys.platform == 'win32':
                        # 使用wmic获取设备ID，添加完整路径尝试
                        wmic_paths = [
                            'wmic',
                            r'C:\Windows\System32\wbem\wmic.exe',
                            r'C:\Windows\SysWOW64\wbem\wmic.exe'
                        ]
                        
                        uuid_str = None
                        for wmic_path in wmic_paths:
                            try:
                                result = subprocess.run(
                                    [wmic_path, 'csproduct', 'get', 'UUID'],
                                    capture_output=True,
                                    text=True,
                                    check=True,
                                    timeout=5
                                )
                                output = result.stdout.strip()
                                if output:
                                    lines = output.split('\n')
                                    # 确保有足够的行并且UUID不是全F
                                    if len(lines) > 1:
                                        uuid_str = lines[1].strip()
                                        if uuid_str and uuid_str != 'FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF':
                                            break
                            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                                continue
                        
                        if uuid_str and uuid_str != 'FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF':
                            self.add_log(f"获取设备ID成功: {uuid_str}")
                            return uuid_str
                except Exception as e:
                    self.add_log(f"获取设备ID失败，使用随机UUID: {e}")
                
                # 如果获取失败，生成一个基于MAC地址和系统信息的UUID
                # 这里使用uuid4生成一个随机UUID作为备用
                fallback_uuid = str(uuid.uuid4()).upper()
                self.add_log(f"使用随机UUID: {fallback_uuid}")
                return fallback_uuid
            
            def add_log(self, message):
                """添加日志信息"""
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                log_entry = f"[{timestamp}] {message}"
                self.logs.append(log_entry)
                # 限制日志数量，最多保存100条
                if len(self.logs) > 100:
                    self.logs = self.logs[-100:]
            
            def get_version(self):
                """从setting.ini获取版本号，使用相对路径"""
                try:
                    # 使用相对路径获取setting.ini
                    config_path = os.path.abspath(self.main_app.config_file)
                    self.add_log(f"读取配置文件: {config_path}")
                    config = configparser.ConfigParser()
                    config.read(config_path, encoding='utf-8')
                    # 检查version配置
                    if 'version' in config:
                        if 'version' in config['version']:
                            version = config['version']['version']
                            self.add_log(f"获取版本号成功: {version}")
                            return version
                        else:
                            self.add_log("version配置项不存在，使用默认值")
                    else:
                        self.add_log("version配置组不存在，使用默认值")
                except Exception as e:
                    self.add_log(f"获取版本号失败，使用默认值: {e}")
                return '1.0.0'
            
            # 处理工作流事件迭代器
            def handle_workflow_iterator(self, stream: Stream[WorkflowEvent]):
                for event in stream:
                    if event.event == WorkflowEventType.MESSAGE:
                        self.add_log(f"获取到消息: {event.message}")
                    elif event.event == WorkflowEventType.ERROR:
                        self.add_log(f"获取到错误: {event.error}")
                    elif event.event == WorkflowEventType.INTERRUPT:
                        self.add_log(f"获取到中断事件，尝试恢复")
                        try:
                            self.handle_workflow_iterator(
                                self.coze.workflows.runs.resume(
                                    workflow_id=self.workflow_id,
                                    event_id=event.interrupt.interrupt_data.event_id,
                                    resume_data="hey",
                                    interrupt_type=event.interrupt.interrupt_data.type,
                                )
                            )
                        except Exception as e:
                            self.add_log(f"恢复工作流失败: {e}")
            
            def push_info(self):
                """推送信息到Coze API"""
                self.push_status = False
                self.add_log("开始推送设备信息...")
                self.add_log(f"推送参数: DvID={self.device_id}, SoV={self.version}")
                
                try:
                    # 使用Coze SDK调用工作流（使用create方法而非stream方法）
                    workflow = self.coze.workflows.runs.create(
                        workflow_id=self.workflow_id,
                        parameters={
                            "DvID": self.device_id,
                            "SoV": self.version
                        }
                    )
                    
                    self.add_log(f"推送成功: {workflow.data}")
                    self.push_status = True
                except Exception as e:
                    # 处理认证失败等错误
                    self.add_log(f"推送过程中出错: {e}")
                    self.add_log(f"错误类型: {type(e).__name__}")
                    # 即使推送失败，也设置状态为True，避免持续尝试
                    self.push_status = True
            
            def start_push_thread(self):
                """在后台线程中启动推送"""
                thread = threading.Thread(target=self.push_info, daemon=True)
                thread.start()
        
        # 创建PCInfoPusher实例
        pusher = PCInfoPusher(self)
        
        # 创建主框架
        main_frame = ttk.Frame(push_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部状态和按钮区域
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)
        
        # 推送状态显示
        status_var = tk.StringVar(value="推送状态: 初始化中...")
        status_label = ttk.Label(top_frame, textvariable=status_var, font=('宋体', 10, 'bold'))
        status_label.pack(side=tk.LEFT, padx=5)
        
        # 手动推送按钮
        push_btn = ttk.Button(top_frame, text="手动推送", command=pusher.start_push_thread)
        push_btn.pack(side=tk.RIGHT, padx=5)
        
        # 设备信息显示
        info_frame = ttk.Labelframe(main_frame, text="设备信息")
        info_frame.pack(fill=tk.X, pady=5)
        
        # 设备ID
        device_id_label = ttk.Label(info_frame, text=f"设备ID: {pusher.device_id}", anchor="w")
        device_id_label.pack(padx=10, pady=2, fill=tk.X)
        
        # 软件版本
        version_label = ttk.Label(info_frame, text=f"软件版本: {pusher.version}", anchor="w")
        version_label.pack(padx=10, pady=2, fill=tk.X)
        
        # 日志显示区域
        log_frame = ttk.Labelframe(main_frame, text="推送日志")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 日志文本框和滚动条
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(log_text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 文本框
        log_text = tk.Text(
            log_text_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            font=('Consolas', 9),
            state=tk.DISABLED
        )
        log_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # 关联滚动条
        scrollbar.config(command=log_text.yview)
        
        # 启动推送线程
        pusher.start_push_thread()
        
        # 更新状态和日志
        def update_ui():
            # 更新状态
            if pusher.push_status:
                status_var.set("推送状态: 已推送")
            else:
                status_var.set("推送状态: 推送中...")
            
            # 更新日志
            log_text.config(state=tk.NORMAL)
            log_text.delete(1.0, tk.END)
            log_text.insert(tk.END, "\n".join(pusher.logs))
            log_text.see(tk.END)  # 滚动到最新日志
            log_text.config(state=tk.DISABLED)
            
            # 每秒更新一次
            push_window.after(1000, update_ui)
        
        # 开始更新UI
        update_ui()
        
        # 关闭按钮
        def on_close():
            push_window.destroy()
        
        # 绑定关闭事件
        push_window.protocol("WM_DELETE_WINDOW", on_close)
    
    def show_config_dialog(self, title, section, config_items):
        """显示配置对话框
        
        Args:
            title: 对话框标题
            section: 配置文件中的节名
            config_items: 配置项列表，每个配置项为元组(标签文本, 配置键名, 默认值, 是否需要目录选择按钮)
        """
        config_window = tk.Toplevel(self.root)
        config_window.title(title)
        config_window.geometry("500x650")
        config_window.resizable(False, False)
        
        # 设置对话框置顶
        config_window.transient(self.root)
        config_window.grab_set()
        
        # 居中显示
        config_window.update_idletasks()
        width = config_window.winfo_width()
        height = config_window.winfo_height()
        x = (self.root.winfo_width() // 2) - (width // 2) + self.root.winfo_x()
        y = (self.root.winfo_height() // 2) - (height // 2) + self.root.winfo_y()
        config_window.geometry(f"+{x}+{y}")
        
        # 添加ESC键绑定，按ESC键关闭窗口
        config_window.bind("<Escape>", lambda e: config_window.destroy())
        
        # 使用简单的框架布局
        main_frame = ttk.Frame(config_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加标题
        title_label = ttk.Label(main_frame, text=title, font=("宋体", 14, "bold"))
        title_label.pack(pady=10)
        
        # 配置项框架
        config_frame = ttk.Frame(main_frame)
        config_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 创建变量字典
        var_dict = {}
        
        # 创建配置项
        for i, (label_text, var_name, default_value, need_dir_btn) in enumerate(config_items):
            frame = ttk.Frame(config_frame)
            frame.pack(fill=tk.X, pady=8)
            
            label = ttk.Label(frame, text=label_text, width=15, anchor=tk.W)
            label.pack(side=tk.LEFT, padx=5, pady=5)
            
            current_value = self.config.get(section, var_name, fallback=default_value)
            # 移除注释部分
            if isinstance(current_value, str):
                current_value = current_value.split()[0] if current_value.split() else current_value
            var_dict[var_name] = tk.StringVar(value=current_value)
            entry = ttk.Entry(frame, textvariable=var_dict[var_name], width=30)
            entry.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
            
            if need_dir_btn:
                def select_dir(var, lt=label_text, vn=var_name):
                    if vn == "workflow_path":
                        file_path = filedialog.askopenfilename(
                            title=f"选择{lt}",
                            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
                        )
                        if file_path:
                            var.set(os.path.relpath(file_path))
                    else:
                        dir_path = filedialog.askdirectory(title=f"选择{lt}")
                        if dir_path:
                            var.set(os.path.relpath(dir_path))
                
                dir_btn = ttk.Button(frame, text="浏览", command=lambda v=var_dict[var_name], lt=label_text, vn=var_name: select_dir(v, lt, vn))
                dir_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 在指定位置添加测试结果显示区域
        test_result_var = tk.StringVar(value="")
        test_result_label = ttk.Label(config_frame, textvariable=test_result_var, foreground="green", font=("宋体", 10), anchor=tk.CENTER)
        
        # 根据不同API类型放置测试结果
        if section == "ollama":
            # Ollama API - 放置在"响应超时时间"下方
            test_result_label.pack(fill=tk.X, pady=8)
        elif section == "tencent_translate":
            # 腾讯翻译API - 放置在"API区域"下方
            test_result_label.pack(fill=tk.X, pady=8)
        
        # 保存按钮
        def save_config():
            """保存配置"""
            if section not in self.config:
                self.config[section] = {}
            
            for var_name, var in var_dict.items():
                self.config[section][var_name] = var.get()
            
            self.save_config()
            config_window.destroy()
            messagebox.showinfo("提示", "配置保存成功")
        
        # 测试按钮功能
        def test_api():
            """测试API连接"""
            import threading
            import requests
            import time
            
            # 更新结果为测试中
            test_result_var.set(tr("API测试中..."))
            test_result_label.configure(foreground="#ff9900")
            
            # 从当前窗口输入框读取参数进行测试
            test_config = {}
            for var_name, var in var_dict.items():
                # 直接从输入框获取当前值
                test_config[var_name] = var.get()
            
            def test_thread():
                """测试线程"""
                try:
                    if section == "ollama":
                        # 测试Ollama API
                        url = test_config.get("url", "http://localhost:11434")
                        model = test_config.get("model", "")
                        timeout = int(test_config.get("timeout", "10"))
                        
                        # 初始化结果字符串
                        result_lines = []
                        result_color = "red"
                        
                        try:
                            # 测试1: URL连通性测试
                            response = requests.get(f"{url}/api/tags", timeout=timeout)
                            if response.status_code == 200:
                                result_lines.append(tr("ollama启动正常"))
                            else:
                                result_lines.append(tr("ollama启动失败"))
                                test_result_var.set("\n".join(result_lines))
                                test_result_label.configure(foreground="red")
                                self.logger.info(f"Ollama连通性测试: {result_lines[0]}")
                                return
                            
                            # 测试2: 翻译功能测试
                            if model:
                                # 构建翻译请求
                                translate_payload = {
                                    "model": model,
                                    "prompt": "将'你好'翻译成英文，仅输出翻译结果",
                                    "stream": False
                                }
                                
                                # 发送翻译请求
                                translate_response = requests.post(f"{url}/api/generate", json=translate_payload, timeout=timeout)
                                if translate_response.status_code == 200:
                                    translate_result = translate_response.json()
                                    generated_text = translate_result.get("response", "").strip()
                                    
                                    if generated_text.lower() == "hello":
                                        result_lines.append(tr("Hello翻译成功"))
                                        result_color = "green"
                                    else:
                                        result_lines.append(tr("翻译失败!请修改或检查模型名称再试!"))
                                        self.logger.error(f"Ollama翻译测试失败: 期望'Hello', 得到'{generated_text}'")
                                else:
                                    result_lines.append(tr("翻译失败!请修改或检查模型名称再试!"))
                                    self.logger.error(f"Ollama翻译请求失败: 状态码 {translate_response.status_code}")
                            else:
                                result_lines.append(tr("请填写模型名称"))
                                self.logger.error("Ollama模型名称为空")
                        except Exception as e:
                            if len(result_lines) == 0:
                                result_lines.append(tr("ollama启动失败"))
                            result_lines.append(tr("翻译失败!请修改或检查模型名称再试!"))
                            self.logger.error(f"Ollama测试异常: {type(e).__name__}: {str(e)}")
                        
                        # 设置结果
                        test_result_var.set("\n".join(result_lines))
                        test_result_label.configure(foreground=result_color)
                        self.logger.info(f"Ollama测试结果: {'; '.join(result_lines)}")
                    elif section == "tencent_translate":
                        # 测试腾讯翻译API
                        appid = test_config.get("appid", "")
                        secret_id = test_config.get("secret_id", "")
                        secret_key = test_config.get("secret_key", "")
                        region = test_config.get("region", "ap-guangzhou")
                        host = test_config.get("host", "tmt.tencentcloudapi.com")
                        action = test_config.get("action", "TextTranslate")
                        version = test_config.get("version", "2018-03-21")
                        
                        # 记录测试开始日志
                        self.logger.info("=== 开始测试腾讯翻译API ===")
                        self.logger.info(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                        self.logger.info(f"API主机: {host}")
                        self.logger.info(f"API区域: {region}")
                        self.logger.info(f"API动作: {action}")
                        self.logger.info(f"API版本: {version}")
                        self.logger.info(f"APPID: {appid}")
                        self.logger.info(f"Secret ID: {secret_id}")
                        self.logger.info(f"Secret Key: {secret_key}")
                        
                        if not appid or not secret_id or not secret_key:
                            error_msg = tr("腾讯翻译API配置不完整，缺少必要参数")
                            test_result_var.set(error_msg)
                            test_result_label.configure(foreground="red")
                            self.logger.error(error_msg)
                            self.logger.info("=== 腾讯翻译API测试结束 ===")
                            return
                        
                        # 测试腾讯翻译API的实际翻译功能
                        try:
                            # 构造测试URL
                            test_url = f"https://{host}/"
                            # 发送简单的HEAD请求测试连接性
                            response = requests.head(test_url, timeout=5)
                            self.logger.info(f"请求URL: {test_url}")
                            self.logger.info(f"响应状态码: {response.status_code}")
                            self.logger.info(f"响应头: {dict(response.headers)}")
                            
                            if response.status_code in [200, 301, 302, 403]:
                                # 连接成功，返回403是正常的，因为没有完整的请求参数
                                result_lines = [tr("腾讯翻译API连接成功")]
                                test_result_var.set("\n".join(result_lines))
                                test_result_label.configure(foreground="green")
                                self.logger.info("腾讯翻译API连接成功")
                                
                                # 测试2: 实际翻译测试
                                try:
                                    # 导入所需模块生成签名
                                    import hashlib
                                    import hmac
                                    import base64
                                    import urllib.parse
                                    
                                    # 准备请求参数
                                    timestamp = str(int(time.time()))
                                    nonce = str(int(time.time()))
                                    
                                    # 构建翻译请求参数
                                    translate_params = {
                                        "Action": action,
                                        "Version": version,
                                        "Region": region,
                                        "SecretId": secret_id,
                                        "Timestamp": timestamp,
                                        "Nonce": nonce,
                                        "ProjectId": 0,
                                        "SourceText": "你好",
                                        "Source": "zh",
                                        "Target": "en"
                                    }
                                    
                                    # 生成签名
                                    def generate_signature(method, host, params, secret_key):
                                        # 腾讯云API签名生成要求的格式：使用换行符分隔
                                        # 1. 排序参数
                                        sorted_params = sorted(params.items(), key=lambda x: x[0])
                                        # 2. 构建请求字符串（不进行URL编码，直接使用原始参数）
                                        request_str = method  # GET
                                        request_str += host  # tmt.tencentcloudapi.com
                                        request_str += "/?"
                                        request_str += "&" .join([f"{k}={v}" for k, v in sorted_params])
                                        # 4. 生成HMAC-SHA1签名
                                        h = hmac.new(secret_key.encode(), request_str.encode(), hashlib.sha1)
                                        signature = base64.b64encode(h.digest()).decode()
                                        return signature
                                    
                                    # 生成签名并添加到参数中
                                    signature = generate_signature("GET", host, translate_params, secret_key)
                                    translate_params["Signature"] = signature
                                    
                                    # 发送翻译请求
                                    full_url = f"https://{host}/"
                                    response = requests.get(full_url, params=translate_params, timeout=10)
                                    
                                    self.logger.info(f"翻译请求URL: {full_url}")
                                    self.logger.info(f"翻译请求参数: {translate_params}")
                                    self.logger.info(f"翻译响应状态码: {response.status_code}")
                                    self.logger.info(f"翻译响应内容: {response.text}")
                                    
                                    # 解析响应
                                    result = response.json()
                                    
                                    if response.status_code == 200:
                                        if "Response" in result:
                                            response_data = result["Response"]
                                            if "Error" in response_data:
                                                # API调用失败
                                                error = response_data["Error"]
                                                result_lines.append("翻译失败!请修改参数或腾讯API密钥再试!")
                                                self.logger.error(f"腾讯翻译API调用失败: {error['Code']} - {error['Message']}")
                                            else:
                                                # 检查翻译结果
                                                translated_text = response_data.get("TargetText", "").strip()
                                                self.logger.info(f"翻译结果: '{translated_text}'")
                                                
                                                if translated_text.lower() == "hello":
                                                    result_lines.append("Hello翻译成功")
                                                    result_color = "green"
                                                else:
                                                    result_lines.append("翻译失败!请修改参数或腾讯API密钥再试!")
                                        else:
                                            result_lines.append("翻译失败!请修改参数或腾讯API密钥再试!")
                                            self.logger.error(f"腾讯翻译API测试失败: 响应格式错误 - {response.text}")
                                    else:
                                        result_lines.append("翻译失败!请修改参数或腾讯API密钥再试!")
                                        self.logger.error(f"腾讯翻译API测试失败: HTTP错误 {response.status_code}")
                                except Exception as e:
                                    result_lines.append("翻译失败!请修改参数或腾讯API密钥再试!")
                                    self.logger.error(f"腾讯翻译API测试失败: {type(e).__name__}: {str(e)}")
                                    import traceback
                                    self.logger.error(f"异常详情: {traceback.format_exc()}")
                                finally:
                                    # 更新结果显示
                                    test_result_var.set("\n".join(result_lines))
                            else:
                                error_msg = f"腾讯翻译API连接失败: 状态码 {response.status_code}"
                                test_result_var.set(error_msg)
                                test_result_label.configure(foreground="red")
                                self.logger.error(error_msg)
                        except Exception as e:
                            error_msg = f"腾讯翻译API测试失败: {str(e)}"
                            test_result_var.set(error_msg)
                            test_result_label.configure(foreground="red")
                            self.logger.error(f"API测试异常: {type(e).__name__}: {str(e)}")
                            import traceback
                            self.logger.error(f"异常详情: {traceback.format_exc()}")
                        finally:
                            self.logger.info("=== 腾讯翻译API测试结束 ===")
                    else:
                        test_result_var.set("不支持的API类型测试")
                        test_result_label.configure(foreground="blue")
                except Exception as e:
                    error_msg = f"API测试失败: {str(e)}"
                    test_result_var.set(error_msg)
                    test_result_label.configure(foreground="red")
            
            # 启动测试线程
            threading.Thread(target=test_thread, daemon=True).start()
        
        # 底部框架，用于存放所有按钮和结果
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=20)
        
        # 测试按钮和结果框架 - 确保所有元素垂直居中
        test_result_frame = ttk.Frame(bottom_frame)
        test_result_frame.pack(side=tk.LEFT, pady=5, anchor=tk.CENTER)
        
        # 添加测试按钮
        test_btn = ttk.Button(test_result_frame, text=tr("测试API"), command=test_api, style="danger.TButton")
        test_btn.pack(side=tk.LEFT, padx=5, pady=5, anchor=tk.CENTER)
        
        # 保存和取消按钮框架，右对齐，确保与测试按钮在同一水平线上
        save_cancel_frame = ttk.Frame(bottom_frame)
        save_cancel_frame.pack(side=tk.RIGHT, pady=5, anchor=tk.CENTER)
        
        # 取消按钮放在左边，保存按钮放在右边，确保垂直居中且间距一致
        cancel_btn = ttk.Button(save_cancel_frame, text=tr("取消"), command=config_window.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5, pady=5, anchor=tk.CENTER)
        
        save_btn = ttk.Button(save_cancel_frame, text=tr("保存"), command=save_config)
        save_btn.pack(side=tk.RIGHT, padx=5, pady=5, anchor=tk.CENTER)
    
    def show_project_manager(self):
        """显示项目管理对话框"""
        # 创建项目管理对话框
        project_window = tk.Toplevel(self.root)
        project_window.title("读取项目")
        project_window.geometry("700x600")
        project_window.resizable(False, False)
        
        # 设置对话框置顶
        project_window.transient(self.root)
        project_window.grab_set()
        
        # 居中显示
        project_window.update_idletasks()
        width = project_window.winfo_width()
        height = project_window.winfo_height()
        x = (self.root.winfo_width() // 2) - (width // 2) + self.root.winfo_x()
        y = (self.root.winfo_height() // 2) - (height // 2) + self.root.winfo_y()
        project_window.geometry(f"+{x}+{y}")
        
        # 添加ESC键绑定，按ESC键关闭窗口
        project_window.bind("<Escape>", lambda e: project_window.destroy())
        
        main_frame = tk.Frame(project_window, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加标题
        title_label = tk.Label(main_frame, text="读取项目", font=('宋体', 14, 'bold'))
        title_label.pack(pady=10)
        
        # 现有项目名称展示栏
        project_frame = tk.LabelFrame(main_frame, text="现有项目")
        project_frame.pack(fill=tk.BOTH, pady=10, expand=True)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(project_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建Treeview表格，显示序号和文件名
        project_list = ttk.Treeview(project_frame, columns=("index", "name"), show="headings", yscrollcommand=scrollbar.set)
        project_list.pack(fill=tk.BOTH, padx=10, pady=10, expand=True, side=tk.LEFT)
        scrollbar.configure(command=project_list.yview)
        
        # 设置列宽和标题
        project_list.heading("index", text="序号", anchor=tk.CENTER)
        project_list.column("index", width=50, anchor=tk.CENTER, stretch=tk.NO)
        project_list.heading("name", text="文件名", anchor=tk.W)
        project_list.column("name", width=500, anchor=tk.W)
        
        # 双击事件处理函数
        def on_double_click(event):
            """双击事件处理，询问用户是否读取项目"""
            # 获取选中的项目
            selected_items = project_list.selection()
            if not selected_items:
                return
            
            selected_item = selected_items[0]
            selected_project = project_list.item(selected_item, "values")[1]
            
            # 弹出提示框，询问用户是否读取项目
            response = self.custom_messagebox(project_window, "确认", f"确定要读取项目 '{selected_project}' 吗？", ask_yes_no=True)
            
            if response:
                # 用户选择确定，执行读取项目逻辑
                load_project()
                return
            
            # 用户选择取消，不执行任何操作
        
        # 绑定双击事件
        project_list.bind("<Double-1>", on_double_click)
        
        # 右键菜单功能
        def show_context_menu(event):
            """显示右键菜单"""
            # 获取当前点击位置的项目
            item = project_list.identify_row(event.y)
            if item:
                # 选择点击的项目
                project_list.selection_set(item)
                # 创建右键菜单
                context_menu = tk.Menu(project_window, tearoff=0)
                # 添加重命名菜单项
                context_menu.add_command(label="修改文件名", command=rename_project)
                # 在鼠标位置显示菜单
                context_menu.post(event.x_root, event.y_root)
        
        # 绑定右键菜单事件
        project_list.bind("<Button-3>", show_context_menu)
        
        # 当前打开的项目名称
        current_project_var = tk.StringVar(value="")
        current_project_label = tk.Label(main_frame, textvariable=current_project_var, font=("宋体", 10), fg="blue")
        current_project_label.pack(pady=5)
        
        # 功能按钮组 - 第一行
        button_frame1 = tk.Frame(main_frame)
        button_frame1.pack(fill=tk.X, pady=10)
        
        # 新增项目按钮
        def new_project():
            """新增项目"""
            project_dir = self.config.get("System", "project_dir").split()[0]
            
            # 确保项目目录存在
            if not os.path.exists(project_dir):
                os.makedirs(project_dir)
            
            # 生成新的项目文件名
            base_name = "新建项目"
            extension = ".json"
            new_project_name = base_name + extension
            counter = 1
            
            # 检查文件名是否存在，如存在则递增编号
            while os.path.exists(os.path.join(project_dir, new_project_name)):
                new_project_name = f"{base_name}{counter:02d}{extension}"
                counter += 1
            
            # 创建新的空白项目文件
            project_file = os.path.join(project_dir, new_project_name)
            
            # 初始化项目数据
            project_data = {
                "version": "1.0",
                "config": {
                    "ollama": dict(self.config["ollama"]),
                    "tencent_translate": dict(self.config["tencent_translate"]),
                    "comfyui_status": dict(self.config["comfyui_status"]),
                    "comfyui_gen": dict(self.config["comfyui_gen"]),
                    "system": dict(self.config["system"])
                },
                "project_content": [],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "current_project": new_project_name
            }
            
            try:
                with open(project_file, "w", encoding="utf-8") as f:
                    json.dump(project_data, f, indent=2, ensure_ascii=False)
                
                # 自定义消息框，相对于项目管理窗口居中
                def show_custom_message(title, message, type="info"):
                    msg_window = tk.Toplevel(project_window)
                    msg_window.title(title)
                    msg_window.geometry("300x150")
                    msg_window.resizable(False, False)
                    
                    # 设置对话框置顶
                    msg_window.transient(project_window)
                    msg_window.grab_set()
                    
                    # 居中显示在项目管理窗口上
                    msg_window.update_idletasks()
                    width = msg_window.winfo_width()
                    height = msg_window.winfo_height()
                    x = (project_window.winfo_width() // 2) - (width // 2) + project_window.winfo_x()
                    y = (project_window.winfo_height() // 2) - (height // 2) + project_window.winfo_y()
                    msg_window.geometry(f"+{x}+{y}")
                    
                    # 添加ESC键绑定
                    msg_window.bind("<Escape>", lambda e: msg_window.destroy())
                    
                    # 主框架
                    main_frame = ttk.Frame(msg_window, padding="20")
                    main_frame.pack(fill=tk.BOTH, expand=True)
                    
                    # 消息文本
                    msg_label = ttk.Label(main_frame, text=message, wraplength=250, justify=tk.CENTER)
                    msg_label.pack(pady=20)
                    
                    # 确定按钮
                    def on_ok():
                        msg_window.destroy()
                    
                    ok_btn = ttk.Button(main_frame, text="确定", command=on_ok)
                    ok_btn.pack(pady=10)
                    
                self.custom_messagebox(project_window, "提示", f"新项目 '{new_project_name}' 创建成功")
                load_project_list()
            except Exception as e:
                # 使用自定义消息框显示错误
                def show_custom_error(title, message):
                    msg_window = tk.Toplevel(project_window)
                    msg_window.title(title)
                    msg_window.geometry("350x180")
                    msg_window.resizable(False, False)
                    
                    # 设置对话框置顶
                    msg_window.transient(project_window)
                    msg_window.grab_set()
                    
                    # 居中显示在项目管理窗口上
                    msg_window.update_idletasks()
                    width = msg_window.winfo_width()
                    height = msg_window.winfo_height()
                    x = (project_window.winfo_width() // 2) - (width // 2) + project_window.winfo_x()
                    y = (project_window.winfo_height() // 2) - (height // 2) + project_window.winfo_y()
                    msg_window.geometry(f"+{x}+{y}")
                    
                    # 添加ESC键绑定
                    msg_window.bind("<Escape>", lambda e: msg_window.destroy())
                    
                    # 主框架
                    main_frame = ttk.Frame(msg_window, padding="20")
                    main_frame.pack(fill=tk.BOTH, expand=True)
                    
                    # 错误文本
                    msg_label = ttk.Label(main_frame, text=message, wraplength=300, justify=tk.CENTER, foreground="red")
                    msg_label.pack(pady=20)
                    
                    # 确定按钮
                    def on_ok():
                        msg_window.destroy()
                    
                    ok_btn = ttk.Button(main_frame, text="确定", command=on_ok)
                    ok_btn.pack(pady=10)
                
                self.custom_messagebox(project_window, "错误", f"创建新项目失败：{e}", msg_type="error")
        
        # 保存项目按钮
        def save_project():
            """保存项目"""
            selected_items = project_list.selection()
            if not selected_items:
                self.custom_messagebox(project_window, "警告", "请先选择一个项目", msg_type="warning")
                return
            
            selected_item = selected_items[0]
            selected_project = project_list.item(selected_item, "values")[1]
            project_dir = self.config.get("System", "project_dir").split()[0]
            project_file = os.path.join(project_dir, selected_project)
            
            # 调用类的保存项目方法
            self.save_project(selected_project, project_file, project_window)
        
        # 新增项目按钮
        new_btn = tk.Button(button_frame1, text="新增项目", command=new_project, width=12, height=2)
        new_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        # 直接进入重命名模式的函数
        def rename_project_direct():
            """直接进入文件名修改状态"""
            selected_items = project_list.selection()
            if not selected_items:
                self.custom_messagebox(project_window, "提示", "还未选择项目", msg_type="info")
                return
            
            selected_item = selected_items[0]
            selected_project = project_list.item(selected_item, "values")[1]
            original_name = selected_project
            
            # 创建一个Entry组件来修改文件名
            entry = tk.Entry(project_frame, width=len(os.path.splitext(selected_project)[0]))
            entry.insert(0, os.path.splitext(selected_project)[0])
            
            # 获取Treeview中单元格的坐标
            bbox = project_list.bbox(selected_item, "name")
            if bbox:
                x, y, width, height = bbox
                # 放置Entry组件在列表框项的位置，确保完全覆盖单元格
                entry.place(x=x, y=y, width=width, height=height)
                entry.focus_set()
                entry.select_range(0, tk.END)
                
                def on_focus_out(event):
                    """失去焦点时处理"""
                    new_name = entry.get().strip()
                    if new_name and new_name != os.path.splitext(original_name)[0]:
                        # 确保文件名有效
                        if new_name and new_name.isprintable():
                            # 生成新的文件名
                            new_project_name = new_name + ".json"
                            project_dir = self.config.get("System", "project_dir").split()[0]
                            old_file = os.path.join(project_dir, original_name)
                            new_file = os.path.join(project_dir, new_project_name)
                            
                            # 检查新文件名是否已存在
                            if not os.path.exists(new_file):
                                try:
                                    # 重命名文件
                                    os.rename(old_file, new_file)
                                    # 更新Treeview，重新加载列表
                                    load_project_list()
                                except Exception as e:
                                    messagebox.showerror("错误", f"重命名失败：{e}")
                            else:
                                messagebox.showerror("错误", f"文件名 '{new_project_name}' 已存在")
                    entry.destroy()
                
                def on_return_key(event):
                    """按下回车键时处理"""
                    on_focus_out(event)
                
                # 绑定事件
                entry.bind("<FocusOut>", on_focus_out)
                entry.bind("<Return>", on_return_key)
                entry.bind("<Escape>", lambda e: entry.destroy())
        
        # 新增更名项目按钮
        def rename_project():
            """更名项目"""
            rename_project_direct()
        
        rename_btn = tk.Button(button_frame1, text="更名项目", command=rename_project, width=12, height=2)
        rename_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        # 保存项目按钮
        save_btn = tk.Button(button_frame1, text="保存项目", command=save_project, width=12, height=2)
        save_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        # 读取项目按钮
        def load_project():
            """读取项目，将配置加载到主页面"""
            selected_items = project_list.selection()
            if not selected_items:
                self.custom_messagebox(project_window, "警告", "请先选择一个项目", msg_type="warning")
                return
            
            selected_item = selected_items[0]
            selected_project = project_list.item(selected_item, "values")[1]
            project_dir = self.config.get("System", "project_dir").split()[0]
            project_file = os.path.join(project_dir, selected_project)
            
            try:
                with open(project_file, "r", encoding="utf-8") as f:
                    project_data = json.load(f)
                
                # 更新配置
                if "config" in project_data:
                    for section, values in project_data["config"].items():
                        if section not in self.config:
                            self.config[section] = {}
                        for key, value in values.items():
                            self.config[section][key] = value
                
                # 加载项目内容数据
                if "project_content" in project_data:
                    # 清空当前内容
                    self.clear_all_content()
                    
                    # 重新创建所需数量的行
                    if "system" in project_data["config"] and "content_rows" in project_data["config"]["system"]:
                        target_rows = int(project_data["config"]["system"]["content_rows"])
                        if target_rows != self.content_rows:
                            # 调整行数
                            self.content_rows = target_rows
                            self.root.after(0, self.after_resize)
                    
                    # 等待布局更新后再加载内容
                    def load_content():
                        project_content = project_data["project_content"]
                        for row_data in project_content:
                            row_index = row_data["row_index"]
                            
                            # 加载图片
                            image_path = row_data.get("image_path", "")
                            if image_path and os.path.exists(image_path):
                                self.load_image(image_path, row_index)
                            
                            # 加载中文提示词
                            cn_prompt = row_data.get("cn_prompt", "")
                            if hasattr(self, "prompt_texts") and row_index < len(self.prompt_texts):
                                text_widget = self.prompt_texts[row_index]
                                # 临时禁用编辑状态更新
                                text_widget.edit_modified(False)
                                text_widget.delete("1.0", tk.END)
                                if cn_prompt:
                                    text_widget.insert("1.0", cn_prompt)
                                # 插入完成后再次重置修改标志
                                text_widget.edit_modified(False)
                            
                            # 加载英文提示词
                            en_prompt = row_data.get("en_prompt", "")
                            if hasattr(self, "english_texts") and row_index < len(self.english_texts):
                                text_widget = self.english_texts[row_index]
                                # 临时禁用编辑状态更新
                                text_widget.edit_modified(False)
                                text_widget.delete("1.0", tk.END)
                                if en_prompt:
                                    text_widget.insert("1.0", en_prompt)
                                # 插入完成后再次重置修改标志
                                text_widget.edit_modified(False)
                            
                            # 加载图片参数
                            image_params = row_data.get("image_params", {})
                            
                            # K采样器步数
                            if hasattr(self, "k_sampler_steps_list") and row_index < len(self.k_sampler_steps_list):
                                k_sampler_steps = image_params.get("k_sampler_steps", "8")
                                self.k_sampler_steps_list[row_index].set(k_sampler_steps)
                            
                            # 图片高度
                            if hasattr(self, "image_height_list") and row_index < len(self.image_height_list):
                                image_height = image_params.get("image_height", "480")
                                self.image_height_list[row_index].set(image_height)
                            
                            # 图片宽度
                            if hasattr(self, "image_width_list") and row_index < len(self.image_width_list):
                                image_width = image_params.get("image_width", "832")
                                self.image_width_list[row_index].set(image_width)
                            
                            # 图片方向
                            if hasattr(self, "image_orientation_list") and row_index < len(self.image_orientation_list):
                                image_orientation = image_params.get("image_orientation", "landscape")
                                self.image_orientation_list[row_index].set(image_orientation)
                            
                            # 更新图片尺寸显示
                            if hasattr(self, "update_image_size_display"):
                                self.update_image_size_display(row_index)
                        
                        # 所有内容加载完成后，设置状态为已保存
                        self.is_edited = False
                        status = "已保存"
                        self.root.title(f"ComfyUI批量处理伴侣 - {self.current_filename} - (状态:{status})")
                        # 刷新所有组件确保颜色正确
                        self.refresh_all_components()
                    
                    # 延迟加载内容，确保界面已更新
                    self.root.after(1000, load_content)
                
                self.save_config()
                self.current_filename = selected_project  # 更新窗口标题使用的文件名变量
                current_project_var.set(f"当前打开项目：{selected_project}")
                self.custom_messagebox(project_window, "提示", f"项目 '{selected_project}' 读取成功")
            except Exception as e:
                    self.custom_messagebox(project_window, "错误", f"读取项目失败：{e}", msg_type="error")
        
        # 创建读取项目按钮
        load_btn = tk.Button(button_frame1, text="读取项目", command=load_project, width=12, height=2)
        load_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        # 删除项目按钮
        def delete_project():
            """删除项目"""
            selected_items = project_list.selection()
            if not selected_items:
                self.custom_messagebox(project_window, "警告", "请先选择一个项目", msg_type="warning")
                return
            
            selected_item = selected_items[0]
            selected_project = project_list.item(selected_item, "values")[1]
            project_file = os.path.join(self.config.get("System", "project_dir").split()[0], selected_project)
            
            if self.custom_messagebox(project_window, "确认", f"确定要删除项目 '{selected_project}' 吗？", ask_yes_no=True):
                try:
                    os.remove(project_file)
                    load_project_list()
                    if current_project_var.get() and selected_project in current_project_var.get():
                        current_project_var.set("")
                    self.custom_messagebox(project_window, "提示", "项目删除成功")
                except Exception as e:
                    self.custom_messagebox(project_window, "错误", f"项目删除失败：{e}", msg_type="error")
        
        delete_btn = tk.Button(button_frame1, text="删除项目", command=delete_project, width=12, height=2)
        delete_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        # 功能按钮组 - 第二行
        button_frame2 = tk.Frame(main_frame)
        button_frame2.pack(fill=tk.X, pady=10)
        
        # 导入项目按钮
        def import_project():
            """导入项目"""
            # 弹出系统路径提示窗口，让用户选择文件
            import_file = filedialog.askopenfilename(
                title="选择要导入的项目文件",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
            )
            
            if not import_file:
                return  # 用户取消了选择
            
            # 弹出确认导入窗口
            if messagebox.askyesno("确认导入", f"确定要导入项目文件 '{os.path.basename(import_file)}' 吗？"):
                try:
                    with open(import_file, "r", encoding="utf-8") as f:
                        project_data = json.load(f)
                    
                    # 更新配置
                    if "config" in project_data:
                        for section, values in project_data["config"].items():
                            if section not in self.config:
                                self.config[section] = {}
                            for key, value in values.items():
                                self.config[section][key] = value
                    
                    # 加载项目内容数据
                    if "project_content" in project_data:
                        # 清空当前内容
                        self.clear_all_content()
                        
                        # 重新创建所需数量的行
                        if "system" in project_data["config"] and "content_rows" in project_data["config"]["system"]:
                            target_rows = int(project_data["config"]["system"]["content_rows"])
                            if target_rows != self.content_rows:
                                # 调整行数
                                self.content_rows = target_rows
                                self.root.after(0, self.after_resize)
                        
                        # 等待布局更新后再加载内容
                        def load_content():
                            project_content = project_data["project_content"]
                            for row_data in project_content:
                                row_index = row_data["row_index"]
                                
                                # 加载图片
                                image_path = row_data.get("image_path", "")
                                if image_path and os.path.exists(image_path):
                                    self.load_image(image_path, row_index)
                                
                                # 加载中文提示词
                                cn_prompt = row_data.get("cn_prompt", "")
                                if hasattr(self, "prompt_texts") and row_index < len(self.prompt_texts):
                                    text_widget = self.prompt_texts[row_index]
                                    text_widget.delete("1.0", tk.END)
                                    if cn_prompt:
                                        text_widget.insert("1.0", cn_prompt)
                                        text_widget.config(fg="black")
                                    else:
                                        text_widget.insert("1.0", "中文提示词")
                                        text_widget.config(fg="gray")
                                
                                # 加载英文提示词
                                en_prompt = row_data.get("en_prompt", "")
                                if hasattr(self, "english_texts") and row_index < len(self.english_texts):
                                    text_widget = self.english_texts[row_index]
                                    text_widget.delete("1.0", tk.END)
                                    if en_prompt:
                                        text_widget.insert("1.0", en_prompt)
                                        text_widget.config(fg="black")
                                    else:
                                        text_widget.insert("1.0", "英文翻译")
                                        text_widget.config(fg="gray")
                                
                                # 加载图片参数
                                image_params = row_data.get("image_params", {})
                                
                                # K采样器步数
                                if hasattr(self, "k_sampler_steps_list") and row_index < len(self.k_sampler_steps_list):
                                    k_sampler_steps = image_params.get("k_sampler_steps", "8")
                                    self.k_sampler_steps_list[row_index].set(k_sampler_steps)
                                
                                # 图片高度
                                if hasattr(self, "image_height_list") and row_index < len(self.image_height_list):
                                    image_height = image_params.get("image_height", "480")
                                    self.image_height_list[row_index].set(image_height)
                                
                                # 图片宽度
                                if hasattr(self, "image_width_list") and row_index < len(self.image_width_list):
                                    image_width = image_params.get("image_width", "832")
                                    self.image_width_list[row_index].set(image_width)
                                
                                # 图片方向
                                if hasattr(self, "image_orientation_list") and row_index < len(self.image_orientation_list):
                                    image_orientation = image_params.get("image_orientation", "landscape")
                                    self.image_orientation_list[row_index].set(image_orientation)
                                
                                # 更新图片尺寸显示
                                if hasattr(self, "update_image_size_display"):
                                    self.update_image_size_display(row_index)
                        
                        # 延迟加载内容，确保界面已更新
                        self.root.after(1000, load_content)
                    
                    self.save_config()
                    current_project_var.set(f"当前打开项目：{os.path.basename(import_file)}")
                    self.custom_messagebox(project_window, "提示", "项目导入成功")
                    load_project_list()
                except Exception as e:
                    self.custom_messagebox(project_window, "错误", f"项目导入失败：{e}", msg_type="error")
        
        import_btn = tk.Button(button_frame2, text="从外部导入项目", command=import_project, width=14, height=2)
        import_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        # 导出项目按钮
        def export_project():
            """导出项目"""
            selected_items = project_list.selection()
            if not selected_items:
                self.custom_messagebox(project_window, "警告", "请先选择一个项目", msg_type="warning")
                return
            
            selected_item = selected_items[0]
            selected_project = project_list.item(selected_item, "values")[1]
            project_file = os.path.join(self.config.get("System", "project_dir").split()[0], selected_project)
            
            export_path = filedialog.asksaveasfilename(
                title="导出项目",
                defaultextension=".json",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
                initialfile=selected_project
            )
            
            if export_path:
                try:
                    shutil.copy2(project_file, export_path)
                    self.custom_messagebox(project_window, "提示", "项目导出成功")
                except Exception as e:
                    self.custom_messagebox(project_window, "错误", f"项目导出失败：{e}", msg_type="error")
        
        export_btn = tk.Button(button_frame2, text="导出项目", command=export_project, width=12, height=2)
        export_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        # 读取项目按钮
        def load_project():
            """读取项目，将配置加载到主页面"""
            selected_items = project_list.selection()
            if not selected_items:
                self.custom_messagebox(project_window, "警告", "请先选择一个项目", msg_type="warning")
                return
            
            selected_item = selected_items[0]
            selected_project = project_list.item(selected_item, "values")[1]
            project_dir = self.config.get("System", "project_dir").split()[0]
            project_file = os.path.join(project_dir, selected_project)
            
            try:
                with open(project_file, "r", encoding="utf-8") as f:
                    project_data = json.load(f)
                
                # 更新配置
                if "config" in project_data:
                    for section, values in project_data["config"].items():
                        if section not in self.config:
                            self.config[section] = {}
                        for key, value in values.items():
                            self.config[section][key] = value
                
                # 加载项目内容数据
                if "project_content" in project_data:
                    # 清空当前内容
                    self.clear_all_content()
                    
                    # 重新创建所需数量的行
                    if "system" in project_data["config"] and "content_rows" in project_data["config"]["system"]:
                        target_rows = int(project_data["config"]["system"]["content_rows"])
                        if target_rows != self.content_rows:
                            # 调整行数
                            self.content_rows = target_rows
                            self.root.after(0, self.after_resize)
                    
                    # 等待布局更新后再加载内容
                    def load_content():
                        project_content = project_data["project_content"]
                        for row_data in project_content:
                            row_index = row_data["row_index"]
                            
                            # 加载图片
                            image_path = row_data.get("image_path", "")
                            if image_path and os.path.exists(image_path):
                                self.load_image(image_path, row_index)
                            
                            # 加载中文提示词
                            cn_prompt = row_data.get("cn_prompt", "")
                            if hasattr(self, "prompt_texts") and row_index < len(self.prompt_texts):
                                text_widget = self.prompt_texts[row_index]
                                # 临时禁用编辑状态更新
                                text_widget.edit_modified(False)
                                text_widget.delete("1.0", tk.END)
                                if cn_prompt:
                                    text_widget.insert("1.0", cn_prompt)
                                    # 根据主题设置正确的颜色
                                    try:
                                        special_themes_str = self.config.get("UI", "special_themes", fallback="darkly,superhero,cyborg,vapor,solar")
                                        special_themes = [theme.strip() for theme in special_themes_str.split(",")]
                                        if self.style.theme_use() in special_themes:
                                            text_widget.config(fg="#ffffff")
                                        else:
                                            text_widget.config(fg="black")
                                    except:
                                        text_widget.config(fg="black")
                                else:
                                    text_widget.insert("1.0", "中文提示词")
                                    text_widget.config(fg="gray")
                            
                            # 加载英文提示词
                            en_prompt = row_data.get("en_prompt", "")
                            if hasattr(self, "english_texts") and row_index < len(self.english_texts):
                                text_widget = self.english_texts[row_index]
                                # 临时禁用编辑状态更新
                                text_widget.edit_modified(False)
                                text_widget.delete("1.0", tk.END)
                                if en_prompt:
                                    text_widget.insert("1.0", en_prompt)
                                    # 根据主题设置正确的颜色
                                    try:
                                        special_themes_str = self.config.get("UI", "special_themes", fallback="darkly,superhero,cyborg,vapor,solar")
                                        special_themes = [theme.strip() for theme in special_themes_str.split(",")]
                                        if self.style.theme_use() in special_themes:
                                            text_widget.config(fg="#ffffff")
                                        else:
                                            text_widget.config(fg="black")
                                    except:
                                        text_widget.config(fg="black")
                                else:
                                    text_widget.insert("1.0", "英文翻译")
                                    text_widget.config(fg="gray")
                            
                            # 加载图片参数
                            image_params = row_data.get("image_params", {})
                            
                            # K采样器步数
                            if hasattr(self, "k_sampler_steps_list") and row_index < len(self.k_sampler_steps_list):
                                k_sampler_steps = image_params.get("k_sampler_steps", "8")
                                self.k_sampler_steps_list[row_index].set(k_sampler_steps)
                            
                            # 图片高度
                            if hasattr(self, "image_height_list") and row_index < len(self.image_height_list):
                                image_height = image_params.get("image_height", "480")
                                self.image_height_list[row_index].set(image_height)
                            
                            # 图片宽度
                            if hasattr(self, "image_width_list") and row_index < len(self.image_width_list):
                                image_width = image_params.get("image_width", "832")
                                self.image_width_list[row_index].set(image_width)
                            
                            # 图片方向
                            if hasattr(self, "image_orientation_list") and row_index < len(self.image_orientation_list):
                                image_orientation = image_params.get("image_orientation", "landscape")
                                self.image_orientation_list[row_index].set(image_orientation)
                            
                            # 更新图片尺寸显示
                            if hasattr(self, "update_image_size_display"):
                                self.update_image_size_display(row_index)
                    
                    # 延迟加载内容，确保界面已更新
                    self.root.after(1000, load_content)
                
                self.save_config()
                self.current_filename = selected_project  # 更新窗口标题使用的文件名变量
                status = "已保存"  # 读取的项目默认状态为已保存
                self.root.title(f"ComfyUI批量处理伴侣 - {self.current_filename} - (状态:{status})")  # 更新窗口标题
                current_project_var.set(f"当前打开项目：{selected_project}")
                self.custom_messagebox(project_window, "提示", f"项目 '{selected_project}' 读取成功")
            except Exception as e:
                self.custom_messagebox(project_window, "错误", f"读取项目失败：{e}", msg_type="error")
        

        
        # 删除项目按钮
        def delete_project():
            """删除项目"""
            selected_items = project_list.selection()
            if not selected_items:
                self.custom_messagebox(project_window, "警告", "请先选择一个项目", msg_type="warning")
                return
            
            selected_item = selected_items[0]
            selected_project = project_list.item(selected_item, "values")[1]
            project_file = os.path.join(self.config.get("System", "project_dir").split()[0], selected_project)
            
            if self.custom_messagebox(project_window, "确认", f"确定要删除项目 '{selected_project}' 吗？", ask_yes_no=True):
                try:
                    os.remove(project_file)
                    load_project_list()
                    if current_project_var.get() and selected_project in current_project_var.get():
                        current_project_var.set("")
                    self.custom_messagebox(project_window, "提示", "项目删除成功")
                except Exception as e:
                    self.custom_messagebox(project_window, "错误", f"项目删除失败：{e}", msg_type="error")
        
        def load_project_list():
            """加载项目列表"""
            # 清空Treeview
            for item in project_list.get_children():
                project_list.delete(item)
            
            project_dir = self.config.get("System", "project_dir").split()[0]
            
            if not os.path.exists(project_dir):
                os.makedirs(project_dir)
            
            project_files = [f for f in os.listdir(project_dir) if f.endswith(".json")]
            for i, project_file in enumerate(project_files, 1):
                project_list.insert("", tk.END, values=(i, project_file))
            
            # 默认不选择任何项目，避免用户误操作
            project_list.selection_clear()
        
        load_project_list()

# 添加JsonToIniDebugWindow类，用于INI文件编辑
class JsonToIniDebugWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title(tr("JSON转INI调试工具"))
        self.geometry("1700x1100")
        self.resizable(True, True)
        
        # 设置窗口属性，避免遮挡主窗口
        self.transient(parent)  # 设置为父窗口的临时窗口
        self.master = parent    # 明确指定主窗口
        self.attributes('-topmost', False)  # 不总是显示在顶部
        self.lift()  # 提升窗口层级，使其可见
        parent.lift()  # 确保主窗口仍在顶部
        
        # 导入configparser用于读取配置
        import configparser
        import os
        
        # 配置文件路径
        self.setting_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setting.ini")
        
        # API接口目录 - 默认为当前目录
        self.api_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 从setting.ini读取配置
        self.load_config()
        
        # 变量存储
        self.variables = []
        
        # 复制到变量按钮列表
        self.copy_buttons = []
        
        # 跟踪检测结果弹窗状态
        self.result_window = None
        self.result_window_open = False
        
        # 记录当前打开的JSON文件
        self.current_json_file = ""
        self.current_json_content = ""
        
        # 居中显示窗口
        self.update_idletasks()  # 确保获取正确的窗口尺寸
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        x = self.parent.winfo_x() + (parent_width - self.winfo_width()) // 2
        y = self.parent.winfo_y() + (parent_height - self.winfo_height()) // 2
        self.geometry(f"{self.winfo_width()}x{self.winfo_height()}+{x}+{y}")
        
        # 目录导航历史记录
        self.dir_history = []
        # 记录当前目录深度，用于显示层级结构
        self.current_dir_depth = 0
        
        # 创建界面
        self.create_widgets()
        
        # 加载JSON文件列表
        self.load_json_files()
    
    def load_config(self):
        """从setting.ini文件加载配置"""
        import configparser
        import os
        
        # 创建配置解析器
        config = configparser.ConfigParser()
        
        # 如果配置文件存在，读取配置
        if os.path.exists(self.setting_file):
            try:
                config.read(self.setting_file, encoding='utf-8')
                
                # 读取API目录
                if 'ComfyUI_tool_API' in config and 'api_tool_dir' in config['ComfyUI_tool_API']:
                    # 获取相对路径
                    rel_path = config['ComfyUI_tool_API']['api_tool_dir']
                    # 转换为绝对路径
                    self.api_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), rel_path))
                
                # 读取变量绑定选项（根据当前语言选择对应配置）
                self.binding_options = []
                self.bindings_default = "无"  # 默认值
                
                # 获取当前语言
                current_lang = LanguageManager.get_language()
                
                if 'VariableBindings' in config:
                    # 根据语言选择对应的配置键
                    if current_lang == "en_US":
                        bindings_key = 'bindings_eng'
                        default_key = 'bindings_default_eng'
                    else:
                        bindings_key = 'bindings_cn'
                        default_key = 'bindings_default_cn'
                    
                    # 读取绑定选项
                    if bindings_key in config['VariableBindings']:
                        bindings_str = config['VariableBindings'][bindings_key]
                        self.binding_options = [binding.strip() for binding in bindings_str.split(',') if binding.strip()]
                    elif 'bindings_cn' in config['VariableBindings']:
                        # 回退到中文配置
                        bindings_str = config['VariableBindings']['bindings_cn']
                        self.binding_options = [binding.strip() for binding in bindings_str.split(',') if binding.strip()]
                    
                    # 读取默认绑定值
                    if default_key in config['VariableBindings']:
                        self.bindings_default = config['VariableBindings'][default_key].strip('"')
                    elif 'bindings_default_cn' in config['VariableBindings']:
                        # 回退到中文配置
                        self.bindings_default = config['VariableBindings']['bindings_default_cn'].strip('"')
                
                # 确保默认值选项存在于binding_options中，并且置顶显示
                if self.bindings_default in self.binding_options:
                    self.binding_options.remove(self.bindings_default)
                self.binding_options.insert(0, self.bindings_default)
            except Exception as e:
                print(f"读取配置文件失败: {e}")
        
        # 如果binding_options为空（配置文件不存在或缺少配置），创建默认配置
        if not self.binding_options:
            # 创建默认的变量绑定选项
            default_bindings = [
                "图片载入",
                "正向提示词",
                "负面提示词",
                "K采样步值",
                "视频尺寸高度",
                "视频尺寸宽度",
                "图片尺寸高度",
                "图片尺寸宽度"
            ]
            
            # 英文默认绑定选项
            default_bindings_eng = [
                "Image Load",
                "Positive Prompt",
                "Negative Prompt",
                "K Sampler Steps",
                "Image Width",
                "Image Height",
                "Image Output",
                "Wideo Width",
                "Video Height",
                "Video Output"
            ]
            
            # 确保配置文件存在并包含必要的配置
            if not os.path.exists(self.setting_file) or 'ComfyUI_tool_API' not in config:
                config['ComfyUI_tool_API'] = {
                    'api_tool_dir': self.get_relative_api_dir()
                }
            
            # 添加或更新VariableBindings部分
            if 'VariableBindings' not in config:
                config['VariableBindings'] = {
                    'bindings_cn': ','.join(default_bindings),
                    'bindings_default_cn': '"无"',
                    'bindings_eng': ','.join(default_bindings_eng),
                    'bindings_default_eng': '"None"'
                }
            else:
                # 只更新必要的选项，保留原有配置
                if 'bindings_cn' not in config['VariableBindings']:
                    config['VariableBindings']['bindings_cn'] = ','.join(default_bindings)
                if 'bindings_default_cn' not in config['VariableBindings']:
                    config['VariableBindings']['bindings_default_cn'] = '"无"'
                if 'bindings_eng' not in config['VariableBindings']:
                    config['VariableBindings']['bindings_eng'] = ','.join(default_bindings_eng)
                if 'bindings_default_eng' not in config['VariableBindings']:
                    config['VariableBindings']['bindings_default_eng'] = '"None"'
            
            # 保存配置到文件
            try:
                with open(self.setting_file, 'w', encoding='utf-8') as f:
                    config.write(f)
                print(f"已创建默认配置文件: {self.setting_file}")
            except Exception as e:
                print(f"保存默认配置文件失败: {e}")
            
            # 使用默认绑定选项（根据当前语言）
            if current_lang == "en_US":
                self.binding_options = default_bindings_eng.copy()
                default_option = "None"
            else:
                self.binding_options = default_bindings.copy()
                default_option = "无"
            
            # 确保默认选项存在于binding_options中，并且置顶显示
            if default_option in self.binding_options:
                self.binding_options.remove(default_option)
            self.binding_options.insert(0, default_option)
    
    def reload_binding_options(self):
        """重新加载变量绑定选项（根据当前语言）
        
        在语言切换时调用，从setting.ini重新读取对应语言的绑定选项
        """
        import configparser
        
        if not hasattr(self, 'setting_file') or not os.path.exists(self.setting_file):
            return
        
        try:
            config = configparser.ConfigParser()
            config.read(self.setting_file, encoding='utf-8')
            
            if 'VariableBindings' not in config:
                return
            
            # 获取当前语言
            current_lang = LanguageManager.get_language()
            
            # 根据语言选择对应的配置键
            if current_lang == "en_US":
                bindings_key = 'bindings_eng'
                default_key = 'bindings_default_eng'
            else:
                bindings_key = 'bindings_cn'
                default_key = 'bindings_default_cn'
            
            # 读取绑定选项
            if bindings_key in config['VariableBindings']:
                bindings_str = config['VariableBindings'][bindings_key]
                self.binding_options = [binding.strip() for binding in bindings_str.split(',') if binding.strip()]
            elif 'bindings_cn' in config['VariableBindings']:
                # 回退到中文配置
                bindings_str = config['VariableBindings']['bindings_cn']
                self.binding_options = [binding.strip() for binding in bindings_str.split(',') if binding.strip()]
            
            # 读取默认绑定值
            if default_key in config['VariableBindings']:
                self.bindings_default = config['VariableBindings'][default_key].strip('"')
            elif 'bindings_default_cn' in config['VariableBindings']:
                # 回退到中文配置
                self.bindings_default = config['VariableBindings']['bindings_default_cn'].strip('"')
            
            # 确保默认值选项存在于binding_options中，并且置顶显示
            if self.bindings_default in self.binding_options:
                self.binding_options.remove(self.bindings_default)
            self.binding_options.insert(0, self.bindings_default)
            
            # 更新所有变量绑定下拉菜单（如果存在）
            if hasattr(self, 'variables'):
                for var_data in self.variables:
                    if 'binding_combobox' in var_data:
                        # 保存当前选中的值
                        current_value = var_data["binding_var"].get()
                        # 更新下拉菜单选项
                        var_data["binding_combobox"].configure(values=self.binding_options)
                        # 如果当前值是默认值，更新为新语言的默认值
                        if current_value in ["无", "None", ""]:
                            var_data["binding_var"].set(self.bindings_default)
            
            print(f"已重新加载变量绑定选项: {self.binding_options}, 默认值: {self.bindings_default}")
            
        except Exception as e:
            print(f"重新加载变量绑定选项失败: {e}")
    
    def save_api_dir_to_config(self):
        """将API接口目录和变量绑定选项保存到setting.ini文件"""
        import configparser
        import os
        from src.utils.language import LanguageManager
        
        # 创建配置解析器
        config = configparser.ConfigParser()
        
        # 先读取现有的配置文件内容，保留原有配置
        if os.path.exists(self.setting_file):
            config.read(self.setting_file, encoding='utf-8')
        
        # 更新API配置节
        if 'ComfyUI_tool_API' not in config:
            config['ComfyUI_tool_API'] = {}
        config['ComfyUI_tool_API']['api_tool_dir'] = self.get_relative_api_dir()
        
        # 获取当前语言
        current_lang = LanguageManager.get_language()
        
        # 根据语言选择对应的配置键
        if current_lang == "en_US":
            bindings_key = 'bindings_eng'
            default_key = 'bindings_default_eng'
            default_value = "None"
        else:
            bindings_key = 'bindings_cn'
            default_key = 'bindings_default_cn'
            default_value = "无"
        
        # 更新变量绑定配置节，排除默认选项
        bindings_to_save = [binding for binding in self.binding_options if binding not in ["无", "None"]]
        if 'VariableBindings' not in config:
            config['VariableBindings'] = {}
        
        # 保存到对应语言的配置键
        config['VariableBindings'][bindings_key] = ','.join(bindings_to_save)
        config['VariableBindings'][default_key] = f'"{self.bindings_default}"'
        
        # 保存到文件
        try:
            with open(self.setting_file, 'w', encoding='utf-8') as f:
                config.write(f)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get_relative_api_dir(self):
        """获取API目录相对于工具目录的相对路径"""
        import os
        
        # 获取工具目录
        tool_dir = os.path.dirname(os.path.abspath(__file__))
        # 计算相对路径
        rel_path = os.path.relpath(self.api_dir, tool_dir)
        # 使用Unix风格的路径分隔符
        rel_path = rel_path.replace(os.sep, '/')
        return rel_path
    
    def select_api_dir(self):
        """选择API接口目录并保存到配置文件"""
        from tkinter import filedialog
        import os
        
        # 让用户选择目录
        selected_dir = filedialog.askdirectory(title="选择API JSON文件目录", initialdir=self.api_dir)
        
        if selected_dir:
            # 更新API目录
            self.api_dir = selected_dir
            # 保存到配置文件
            self.save_api_dir_to_config()
            # 重新加载JSON文件列表
            self.load_json_files()
    
    def create_widgets(self):
        # 主框架 - 允许填充整个窗口
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：文件列表区域 - 宽度固定
        file_frame = ttk.Labelframe(main_frame, text=tr("JSON文件列表"), padding="10")
        file_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5)
        file_frame.configure(width=300)
        
        # 读取目录和刷新按钮容器
        button_container = ttk.Frame(file_frame)
        button_container.pack(padx=5, pady=5, anchor=tk.W, fill=tk.X)
        
        # 读取目录按钮
        dir_button = ttk.Button(button_container, text=tr("读取目录"), command=self.select_api_dir, width=15)
        dir_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 刷新按钮
        refresh_button = ttk.Button(button_container, text=tr("刷新"), command=self.load_json_files, width=10)
        refresh_button.pack(side=tk.LEFT)
        
        # 文件列表框
        self.file_listbox = tk.Listbox(file_frame, width=45, height=20)
        self.file_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        # 移除单击事件绑定，改为双击打开
        # self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        # 添加双击事件绑定
        self.file_listbox.bind("<Double-1>", self.on_file_double_click)
        
        # JSON内容显示区域 - 宽度固定
        # 初始标题包含文件名显示
        self.json_frame_title = tr("JSON内容") + " - " + tr("当前打开文件:") + " " + tr("无")
        json_frame = ttk.Labelframe(main_frame, text=self.json_frame_title, padding="10")
        json_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5)
        json_frame.configure(width=800)
        # 保存frame引用，用于更新标题
        self.json_frame = json_frame
        # 记录当前打开的文件名
        self.current_opened_file = "无"
        
        # 添加查找功能 - 简化设计，始终显示
        self.search_frame = ttk.Frame(json_frame)
        self.search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 查找输入框 - 简化设计，移除标签
        self.search_entry = ttk.Entry(self.search_frame, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<Return>", self.find_next)
        self.search_entry.bind("<Escape>", lambda e: self.search_entry.delete(0, tk.END))
        
        # 查找按钮 - 使用ttk样式确保显示正常
        ttk.Button(self.search_frame, text=tr("下一个"), command=self.find_next).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.search_frame, text=tr("上一个"), command=self.find_previous).pack(side=tk.LEFT, padx=5)
        
        # JSON内容文本框
        self.json_text = tk.Text(json_frame, wrap=tk.NONE)
        self.json_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 绑定Ctrl+F快捷键聚焦到搜索框
        self.bind_all("<Control-f>", lambda e: self.search_entry.focus())
        self.bind_all("<Control-F>", lambda e: self.search_entry.focus())
        
        # 添加滚动条 - 使用pack布局
        # 垂直滚动条
        json_scrollbar_v = ttk.Scrollbar(json_frame, orient=tk.VERTICAL, command=self.json_text.yview)
        json_scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        # 水平滚动条
        json_scrollbar_h = ttk.Scrollbar(json_frame, orient=tk.HORIZONTAL, command=self.json_text.xview)
        json_scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))
        # 配置文本框的滚动条命令
        self.json_text.configure(yscrollcommand=json_scrollbar_v.set, xscrollcommand=json_scrollbar_h.set)
        
        # 添加鼠标释放事件监听
        self.json_text.bind("<ButtonRelease-1>", self.on_text_selected)
        
        # 右侧：变量配置区域 - 宽度固定，允许填充剩余空间
        variables_frame = ttk.Labelframe(main_frame, text=tr("变量配置"), padding="10")
        variables_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        variables_frame.configure(width=500)
        
        # 创建带滚动条的变量配置区域
        scrollable_frame = ttk.Frame(variables_frame)
        scrollable_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加导出ini配置功能
        export_ini_frame = ttk.Frame(scrollable_frame)
        export_ini_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(export_ini_frame, text=tr("导出ini配置")).grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Button(export_ini_frame, text=tr("导出"), command=self.export_ini_config).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(export_ini_frame, text=tr("导入"), command=self.import_ini_config).grid(row=0, column=2, padx=5, pady=2)
        ttk.Button(export_ini_frame, text=tr("清除所有内容"), command=self.clear_all_variables).grid(row=0, column=3, padx=5, pady=2)
        
        # 添加帮助按钮 - 绿色样式
        ttk.Button(export_ini_frame, text=tr("帮助(help)"), command=self.open_help_window, style="success.TButton").grid(row=0, column=4, padx=5, pady=2)
        
        # 添加复制到变量按钮组
        copy_buttons_frame = ttk.Frame(scrollable_frame)
        copy_buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 复制到变量标签
        ttk.Label(copy_buttons_frame, text=tr("复制到变量")).grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        
        # 复制到变量1-10按钮
        for i in range(10):
            button = ttk.Button(copy_buttons_frame, text=f"{i+1}", width=3,
                               command=lambda idx=i: self.copy_selected_to_variable(idx))
            button.grid(row=0, column=i+1, padx=2, pady=2)
            # 将按钮添加到列表中
            self.copy_buttons.append(button)
        
        canvas = tk.Canvas(scrollable_frame)
        scrollbar = ttk.Scrollbar(scrollable_frame, orient="vertical", command=canvas.yview)
        scrollable_vars_frame = ttk.Frame(canvas)
        
        scrollable_vars_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_vars_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 添加鼠标滚轮事件绑定
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件（只在当前canvas上生效，避免与其他区域联动）
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # 创建10个变量配置框
        for i in range(10):
            self.create_variable_frame(scrollable_vars_frame, i)
        
        # 初始化按钮颜色
        self.update_button_colors()
    
    def on_text_selected(self, event):
        # 当用户选中文本时的处理 - 现在只需要记录选中状态，不再弹出窗口
        pass
    
    def copy_to_variable(self, index, selected_text):
        # 检查索引是否有效
        if 0 <= index < len(self.variables):
            var_data = self.variables[index]
            
            code_entry = var_data["code_entry"]
            code_entry.delete("1.0", tk.END)
            code_entry.insert("1.0", selected_text)
            
            # 立即刷新界面，确保文本框内容被正确更新
            self.update_idletasks()
            
            # 直接更新对应按钮的颜色，确保实时生效
            var_data = self.variables[index]
            binding_value = var_data["binding_var"].get()
            name_content = var_data["name_entry"].get().strip()
            code_content = var_data["code_entry"].get("1.0", tk.END).strip()
            detail_content = var_data["detail_entry"].get().strip()
            
            should_be_red = (binding_value != self.bindings_default) or bool(name_content) or bool(code_content) or bool(detail_content)
            if should_be_red:
                self.copy_buttons[index].configure(bootstyle="danger")  # 红色
            else:
                self.copy_buttons[index].configure(bootstyle="default")  # 默认颜色
    
    def copy_selected_to_variable(self, index):
        # 获取选中的文本
        try:
            selected_text = self.json_text.get("sel.first", "sel.last")
            if selected_text:
                self.copy_to_variable(index, selected_text)
                
                # 更新按钮颜色
                self.update_button_colors()
                
                # 滚动到对应的变量行
                try:
                    # 获取canvas对象
                    var_data = self.variables[index]
                    scrollable_frame = var_data["frame"].master
                    canvas = scrollable_frame.master
                    
                    # 计算滚动位置
                    var_frame_y = var_data["frame"].winfo_y()
                    canvas_height = canvas.winfo_height()
                    scrollable_height = scrollable_frame.winfo_height()
                    
                    # 确保不超出边界
                    scroll_pos = max(min(var_frame_y / scrollable_height, 1), 0)
                    
                    # 滚动到变量行可见
                    canvas.yview_moveto(scroll_pos)
                except Exception as e:
                    # 如果滚动失败，至少确保文本已复制
                    pass
        except tk.TclError:
            # 没有选中文本
            pass
    
    def export_ini_config(self):
        # 导出ini配置文件
        import configparser
        import os
        import re
        
        # 定义支持重复section的ConfigParser子类
        class MultiConfigParser(configparser.ConfigParser):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._sections = []
                self._section_data = []
            
            def add_section(self, section):
                """添加section"""
                self._sections.append(section)
                self._section_data.append({})
            
            def set(self, section, option, value):
                """设置键值对"""
                if section not in self._sections:
                    self.add_section(section)
                # 找到最后一个匹配的section
                for i in range(len(self._sections)-1, -1, -1):
                    if self._sections[i] == section:
                        self._section_data[i][option] = value
                        break
            
            def write(self, fp, space_around_delimiters=True):
                """写入INI文件，使用UTF-8带BOM格式"""
                # 确保写入的是UTF-8带BOM格式
                if isinstance(fp, str):
                    # 如果fp是文件路径，直接以UTF-8带BOM格式打开并写入
                    with open(fp, 'w', encoding='utf-8-sig', newline='') as f:
                        for i in range(len(self._sections)):
                            section = self._sections[i]
                            section_data = self._section_data[i]
                            f.write(f"[{section}]\n")
                            for key, value in section_data.items():
                                f.write(f"{key} = {value}\n")
                            f.write("\n")
                else:
                    # 如果fp是文件对象，直接写入
                    for i in range(len(self._sections)):
                        section = self._sections[i]
                        section_data = self._section_data[i]
                        fp.write(f"[{section}]\n")
                        for key, value in section_data.items():
                            fp.write(f"{key} = {value}\n")
                        fp.write("\n")
        
        # 创建支持重复section的配置解析器
        config = MultiConfigParser()
        
        # 收集有效的变量配置
        for i, var_data in enumerate(self.variables):
            binding_value = var_data["binding_var"].get().strip()
            name_value = var_data["name_entry"].get().strip()
            code_value = var_data["code_entry"].get("1.0", tk.END).strip()
            detail_value = var_data["detail_entry"].get().strip()
            
            # 规则1：变量绑定值为默认值或为空时不导出
            if not binding_value or binding_value == self.bindings_default:
                continue
            
            # 规则2：检查其他三项是否都为空
            is_all_other_empty = not (name_value or code_value or detail_value)
            
            # 直接使用变量绑定值作为section名称，不添加_1、_2等后缀
            section_name = binding_value
            
            # 添加section
            if section_name not in config._sections:
                config.add_section(section_name)
            else:
                # 直接添加新的section
                config._sections.append(section_name)
                config._section_data.append({})
            
            # 获取当前section的索引
            section_index = len(config._sections) - 1
            
            # 规则2：其他三项都为空时，只导出section名称，不添加任何键值对
            if is_all_other_empty:
                continue
            
            # 其他三项不全为空，正常处理
            # 从变量明细中提取参数键名、参数值和数据节点路径
            param_key = ""
            param_value = ""
            data_node_path = detail_value.strip()
            
            # 匹配格式：data["84"]["inputs"]["clip_name"] = "wan2.1\umt5_xxl_fp8_e4m3fn_scaled.safetensors"
            detail_pattern = re.compile(r'(data\["[^"]+"\]\["inputs"\]\["([^"]+)"\])\s*=\s*"?([^"]+)"?')
            detail_match = detail_pattern.match(data_node_path)
            
            if detail_match:
                data_node_path = detail_match.group(1)  # 只保留数据节点路径，不包含= "值"
                param_key = detail_match.group(2)
                param_value = detail_match.group(3)
            
            # 添加配置项到当前section
            config._section_data[section_index][f'变量序号'] = str(i+1)
            config._section_data[section_index][f'变量名称'] = name_value
            config._section_data[section_index][f'参数键名'] = param_key
            config._section_data[section_index][f'参数值'] = param_value
            config._section_data[section_index][f'数据节点路径'] = data_node_path
            config._section_data[section_index][f'变量代码'] = code_value
            config._section_data[section_index][f'变量绑定'] = binding_value
        
        # 确定保存文件名
        import datetime
        if self.current_json_file:
            # 使用当前打开的JSON文件名作为INI文件名
            ini_filename = os.path.splitext(self.current_json_file)[0] + ".ini"
        else:
            # 使用当前日期时间作为文件名
            ini_filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".ini"
        
        # 保存配置文件
        file_path = filedialog.asksaveasfilename(
            defaultextension=".ini",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
            initialfile=ini_filename
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8-sig') as configfile:
                    config.write(configfile)
                messagebox.showinfo("成功", f"INI配置文件已导出到: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出INI配置文件失败: {e}")
    
    def import_ini_config(self):
        # 导入ini配置文件
        import configparser
        import os
        import re
        from src.utils.language import LanguageManager
        
        # 获取当前语言状态
        current_language = LanguageManager.get_language()
        print(f"当前语言状态: {current_language}")
        
        # 英文到中文的索引名映射
        eng_to_chs_mapping = {
            'None': '无',
            'Image Load': '图片载入',
            'Positive Prompt': '正向提示词',
            'Negative Prompt': '负面提示词',
            'K Sampler Steps': 'K采样步值',
            'Image Width': '图片尺寸宽度',
            'Image Height': '图片尺寸高度',
            'Image Output': '图片输出',
            'Wideo Width': '视频尺寸宽度',
            'Video Height': '视频尺寸高度',
            'Video Output': '视频输出',
        }
        
        # 中文到英文的索引名映射（反向映射）
        chs_to_eng_mapping = {v: k for k, v in eng_to_chs_mapping.items()}
        
        def is_english_section(section_name):
            """判断section名称是否为英文"""
            base_name = section_name
            if '_' in section_name:
                parts = section_name.rsplit('_', 1)
                if parts[1].isdigit():
                    base_name = parts[0]
            return base_name in eng_to_chs_mapping
        
        def is_chinese_section(section_name):
            """判断section名称是否为中文"""
            base_name = section_name
            if '_' in section_name:
                parts = section_name.rsplit('_', 1)
                if parts[1].isdigit():
                    base_name = parts[0]
            return base_name in chs_to_eng_mapping
        
        def translate_section_name(section_name):
            """根据当前语言状态转换section名称
            
            情况1: zh_CN + 英文索引 -> 转换为中文
            情况2: en_US + 中文索引 -> 转换为英文
            情况3: zh_CN + 中文索引 -> 不转换
            情况4: en_US + 英文索引 -> 不转换
            """
            # 检查是否有带后缀的section名（如 "Image Load_2"）
            base_name = section_name
            suffix = ""
            if '_' in section_name:
                parts = section_name.rsplit('_', 1)
                if parts[1].isdigit():
                    base_name = parts[0]
                    suffix = '_' + parts[1]
            
            # 情况1: 中文语言状态 + 英文索引名 -> 转换为中文
            if current_language == "zh_CN" and base_name in eng_to_chs_mapping:
                result = eng_to_chs_mapping[base_name] + suffix
                print(f"转换(英->中): [{section_name}] -> [{result}]")
                return result
            
            # 情况2: 英文语言状态 + 中文索引名 -> 转换为英文
            if current_language == "en_US" and base_name in chs_to_eng_mapping:
                result = chs_to_eng_mapping[base_name] + suffix
                print(f"转换(中->英): [{section_name}] -> [{result}]")
                return result
            
            # 情况3和4: 不需要转换
            print(f"无需转换: [{section_name}]")
            return section_name
        
        # 定义支持重复section的ConfigParser子类
        class MultiConfigParser(configparser.ConfigParser):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._sections = []
                self._section_data = []
            
            def read(self, filenames, encoding=None):
                """读取INI文件，支持重复section，兼容UTF-8和UTF-8 BOM编码"""
                if isinstance(filenames, str):
                    filenames = [filenames]
                
                for filename in filenames:
                    print(f"MultiConfigParser: 开始读取文件 {filename}")
                    self._sections = []
                    self._section_data = []
                    current_section = None
                    current_data = {}
                    line_count = 0
                    
                    # 尝试以不同编码读取文件
                    file_content = None
                    tried_encodings = []
                    
                    # 优先使用指定的编码，如果没有指定则尝试常用编码
                    encodings_to_try = [encoding] if encoding else []
                    encodings_to_try.extend(['utf-8', 'gbk', 'gb2312', 'utf-16'])
                    encodings_to_try = [enc for enc in encodings_to_try if enc]
                    
                    for enc in encodings_to_try:
                        if enc in tried_encodings:
                            continue
                        tried_encodings.append(enc)
                        
                        try:
                            with open(filename, 'r', encoding=enc) as f:
                                file_content = f.read()
                            print(f"MultiConfigParser: 成功以 {enc} 编码读取文件")
                            break
                        except UnicodeDecodeError:
                            print(f"MultiConfigParser: 尝试以 {enc} 编码读取失败，继续尝试其他编码")
                    
                    if file_content is None:
                        print(f"MultiConfigParser: 所有编码尝试失败，无法读取文件")
                        return
                    
                    # 移除BOM标记（如果存在）
                    if file_content.startswith('\ufeff'):
                        file_content = file_content[1:]
                        print(f"MultiConfigParser: 移除了UTF-8 BOM标记")
                    
                    # 按行分割，处理所有类型的行尾符
                    all_lines = file_content.splitlines()
                    print(f"MultiConfigParser: 共读取 {len(all_lines)} 行")
                    
                    for i, line in enumerate(all_lines):
                        line_count += 1
                        # 保留原始行用于调试
                        original_line = line
                        
                        # 去除行前后的空白字符
                        line = line.strip()
                        print(f"MultiConfigParser: 第 {i+1} 行: 原始='{original_line}', 处理后='{line}'")
                        
                        if not line:
                            print(f"MultiConfigParser: 第 {i+1} 行: 跳过空行")
                            continue
                        
                        # 跳过注释行，支持#和;两种注释符号
                        if line.startswith('#') or line.startswith(';'):
                            print(f"MultiConfigParser: 第 {i+1} 行: 跳过注释行")
                            continue
                        
                        # 匹配section行：[section_name]
                        if len(line) >= 2 and line[0] == '[' and line[-1] == ']':
                            print(f"MultiConfigParser: 第 {i+1} 行: 发现section行")
                            # 保存当前section
                            if current_section is not None:
                                print(f"MultiConfigParser: 保存当前section [{current_section}], 数据: {current_data}")
                                self._sections.append(current_section)
                                self._section_data.append(current_data.copy())
                            # 提取section名称，去除前后空白，并进行英文到中文的转换
                            raw_section = line[1:-1].strip()
                            new_section = translate_section_name(raw_section)
                            print(f"MultiConfigParser: 开始新section [{new_section}] (原始: [{raw_section}])")
                            current_section = new_section
                            current_data = {}
                        else:
                            # 匹配键值对：key = value
                            if '=' in line and current_section is not None:
                                print(f"MultiConfigParser: 第 {i+1} 行: 发现键值对，属于section [{current_section}]")
                                # 分割键值对，只分割第一个等号
                                key_part, value_part = line.split('=', 1)
                                key = key_part.strip()
                                # 处理值，去除前后空白和可能的引号
                                value = value_part.strip()
                                # 处理带引号的值，支持单引号和双引号
                                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                                    value = value[1:-1]
                                current_data[key] = value
                                print(f"MultiConfigParser: 添加键值对: {key} = {value}")
                            elif current_section is None:
                                print(f"MultiConfigParser: 第 {i+1} 行: 键值对没有所属section，跳过")
                            else:
                                print(f"MultiConfigParser: 第 {i+1} 行: 不是有效的键值对，跳过")
                    
                    # 保存最后一个section，移出循环外部
                    if current_section is not None and current_data:
                        print(f"MultiConfigParser: 保存最后一个section [{current_section}], 数据: {current_data}")
                        self._sections.append(current_section)
                        self._section_data.append(current_data.copy())
                    
                    print(f"MultiConfigParser: 文件读取完成，共找到 {len(self._sections)} 个section: {self._sections}")
            
            def sections(self):
                """返回所有section名称列表"""
                return self._sections
            
            def __getitem__(self, section):
                """获取指定section的数据"""
                # 这个方法在直接访问config[section]时调用，但我们不需要它
                # 我们会使用自定义的方式访问section数据
                return self._section_data[0]
        
        # 选择要导入的INI文件
        file_path = filedialog.askopenfilename(
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                print(f"\n=== 开始导入INI文件: {file_path} ===")
                
                # 读取INI文件 - 使用支持重复section的MultiConfigParser
                config = MultiConfigParser()
                config.read(file_path, encoding='utf-8')
                
                print(f"成功读取INI文件，共找到 {len(config._sections)} 个section")
                print(f"所有section: {config._sections}")
                
                # 首先收集所有需要的绑定值，确保它们都在binding_options中
                all_binding_values = set(self.binding_options)
                print(f"初始binding_options: {self.binding_options}")
                
                for section in config._sections:
                    section_index = config._sections.index(section)
                    section_config = config._section_data[section_index]
                    # 获取变量绑定值，如果没有则使用section名称
                    binding_value = section_config.get('变量绑定', section)
                    binding_value = re.sub(r'_\d+$', '', binding_value)
                    # 根据当前语言状态转换绑定值
                    binding_value = translate_section_name(binding_value)
                    all_binding_values.add(binding_value)
                    print(f"从section [{section}] 收集到绑定值: {binding_value}")
                
                # 更新binding_options和所有下拉菜单，保持原有顺序
                # 先保留原有binding_options中的值，然后添加新的值
                updated_bindings = []
                for binding in self.binding_options:
                    if binding in all_binding_values:
                        updated_bindings.append(binding)
                        all_binding_values.remove(binding)
                # 添加剩余的新值
                for binding in all_binding_values:
                    updated_bindings.append(binding)
                # 确保默认选项在最前面
                if self.bindings_default in updated_bindings:
                    updated_bindings.remove(self.bindings_default)
                updated_bindings.insert(0, self.bindings_default)
                self.binding_options = updated_bindings
                print(f"更新后的binding_options: {self.binding_options}")
                
                for idx, var_data in enumerate(self.variables):
                    var_data["binding_combobox"].configure(values=self.binding_options)
                    print(f"更新变量 {idx+1} 的下拉菜单选项")
                
                # 保存更新后的binding_options到配置文件
                self.save_api_dir_to_config()
                
                # 遍历所有section，按顺序恢复到对应的变量配置（变量1-10）
                for i in range(len(config._sections)):
                    # 只处理前10个section（对应变量1-10）
                    if i >= len(self.variables):
                        print(f"变量配置框已用完，跳过剩余 {len(config._sections) - i} 个section")
                        break
                    
                    section = config._sections[i]
                    section_config = config._section_data[i]
                    
                    print(f"\n=== 处理第 {i+1} 个section: [{section}] ===")
                    print(f"section配置: {section_config}")
                    
                    # 获取变量数据（按顺序分配，i对应变量i+1）
                    var_data = self.variables[i]
                    
                    # 恢复变量绑定 - 优先使用变量绑定字段，否则使用section名称
                    # 移除section名称中的_1、_2等后缀
                    binding_value = section_config.get('变量绑定', section)
                    # 移除可能存在的数字后缀
                    binding_value = re.sub(r'_\d+$', '', binding_value)
                    # 根据当前语言状态转换绑定值
                    binding_value = translate_section_name(binding_value)
                    print(f"设置变量绑定值: {binding_value}")
                    var_data["binding_var"].set(binding_value)
                    
                    # 恢复变量名称
                    name_value = section_config.get('变量名称', '')
                    print(f"设置变量名称: {name_value}")
                    var_data["name_entry"].delete(0, tk.END)
                    var_data["name_entry"].insert(0, name_value)
                    
                    # 恢复变量代码
                    code_value = section_config.get('变量代码', '')
                    print(f"设置变量代码，长度: {len(code_value)} 字符")
                    var_data["code_entry"].delete("1.0", tk.END)
                    var_data["code_entry"].insert("1.0", code_value)
                    
                    # 恢复变量明细 - 重新构建完整的赋值语句
                    data_node_path = section_config.get('数据节点路径', '')
                    param_value = section_config.get('参数值', '')
                    if data_node_path and param_value:
                        # 构建完整的赋值语句：data["84"]["inputs"]["clip_name"] = "wan2.1\umt5_xxl_fp8_e4m3fn_scaled.safetensors"
                        full_detail = f'{data_node_path} = "{param_value}"'
                        print(f"设置变量明细: {full_detail}")
                        var_data["detail_entry"].delete(0, tk.END)
                        var_data["detail_entry"].insert(0, full_detail)
                    else:
                        print(f"跳过变量明细设置，data_node_path: {data_node_path}, param_value: {param_value}")
                
                print("\n=== INI文件导入完成 ===")
                messagebox.showinfo("成功", "INI配置文件已导入")
            except Exception as e:
                print(f"\n=== 导入失败: {e} ===")
                import traceback
                traceback.print_exc()
                messagebox.showerror("错误", f"导入INI配置文件失败: {e}")
    
    def clear_variable(self, index):
        # 清除变量配置框中的所有内容
        if 0 <= index < len(self.variables):
            var_data = self.variables[index]
            
            # 清除变量绑定 - 设置为配置文件中的默认值
            var_data["binding_var"].set(self.bindings_default)
            
            # 清除变量名称
            var_data["name_entry"].delete(0, tk.END)
            
            # 清除变量代码
            var_data["code_entry"].delete("1.0", tk.END)
            
            # 清除变量明细
            var_data["detail_entry"].delete(0, tk.END)
            
            # 更新对应按钮颜色为默认颜色
            if 0 <= index < len(self.copy_buttons):
                self.copy_buttons[index].configure(bootstyle="default")
    
    def clear_all_variables(self):
        # 清除所有变量配置框中的内容
        for i in range(len(self.variables)):
            self.clear_variable(i)
        
        # 更新所有按钮颜色为默认颜色
        for button in self.copy_buttons:
            button.configure(bootstyle="default")
    
    def open_help_window(self):
        # 导入help模块
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from src.help.help import get_help_content
        
        # 创建帮助窗口
        help_window = tk.Toplevel(self)
        help_window.title(tr("帮助文档"))
        help_window.geometry("800x600")
        help_window.resizable(True, True)
        help_window.transient(self)
        
        # 居中显示窗口
        help_window.update_idletasks()  # 确保获取正确的窗口尺寸
        parent_width = self.winfo_width()
        parent_height = self.winfo_height()
        x = self.winfo_x() + (parent_width - help_window.winfo_width()) // 2
        y = self.winfo_y() + (parent_height - help_window.winfo_height()) // 2
        help_window.geometry(f"{help_window.winfo_width()}x{help_window.winfo_height()}+{x}+{y}")
        
        # 从help.py文件读取帮助内容
        cn_content = get_help_content("chinese")
        en_content = get_help_content("english")
        
        # 创建笔记本控件
        notebook = ttk.Notebook(help_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 中文标签页
        cn_frame = ttk.Frame(notebook, padding="10")
        notebook.add(cn_frame, text=tr("中文"))
        
        # 中文内容
        cn_text = tk.Text(cn_frame, wrap=tk.WORD, font=("SimSun", 10))
        cn_scrollbar = ttk.Scrollbar(cn_frame, orient=tk.VERTICAL, command=cn_text.yview)
        cn_text.configure(yscrollcommand=cn_scrollbar.set)
        cn_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cn_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        cn_text.insert(tk.END, cn_content)
        cn_text.config(state=tk.DISABLED)  # 设置为只读
        
        # 英文标签页
        en_frame = ttk.Frame(notebook, padding="10")
        notebook.add(en_frame, text="English")
        
        # 英文内容
        en_text = tk.Text(en_frame, wrap=tk.WORD, font=("Arial", 10))
        en_scrollbar = ttk.Scrollbar(en_frame, orient=tk.VERTICAL, command=en_text.yview)
        en_text.configure(yscrollcommand=en_scrollbar.set)
        en_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        en_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        en_text.insert(tk.END, en_content)
        en_text.config(state=tk.DISABLED)  # 设置为只读
        
        # 关闭按钮
        close_frame = ttk.Frame(help_window, padding="10")
        close_frame.pack(fill=tk.X)
        ttk.Button(close_frame, text=tr("关闭"), command=help_window.destroy).pack(side=tk.RIGHT)
    
    def check_variable(self, index):
        """
        检测变量代码，直接在主程序中实现，不依赖外部程序
        """
        # 导入必要模块
        import re
        import json
        import os
        import logging
        import datetime
        
        # 配置日志
        log_dir = "日志"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"json_parse_log_{datetime.datetime.now().strftime('%Y%m%d')}.log")
        
        # 创建日志器
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        
        # 清除现有的处理器（防止重复）
        logger.handlers.clear()
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 添加处理器到日志器
        logger.addHandler(file_handler)
        
        # 获取变量代码
        var_data = self.variables[index]
        code_text = var_data["code_entry"].get("1.0", tk.END).strip()
        
        if not code_text:
            messagebox.showwarning("警告", "请输入变量代码")
            return
        
        # 最外层try-except，防止程序崩溃
        try:
            logger.info(f"开始检测JSON: {code_text[:100]}...")
            
            # 步骤1：尝试解析为JSON对象，检测节点数量
            node_id = None
            node_content = None
            
            # 预处理输入，确保格式正确
            processed_text = code_text.strip()
            
            # 处理末尾可能存在的逗号
            if processed_text.endswith(','):
                processed_text = processed_text[:-1]
            
            # 尝试多种解析方式
            parsing_succeeded = False
            
            # 添加调试日志
            logger.debug(f"处理后的文本: {processed_text[:100]}...")
            
            # 方式0：先尝试将多行JSON转换为单行，这可能解决大部分问题
            try:
                # 尝试直接解析为JSON对象（处理多行问题）
                # 首先将多行JSON转换为单行
                single_line = processed_text.replace('\n', '').replace('\r', '').strip()
                logger.debug(f"转换为单行后: {single_line[:100]}...")
                
                # 尝试添加大括号并解析
                if not (single_line.startswith('{') and single_line.endswith('}')):
                    test_json = f"{{ {single_line} }}"
                else:
                    test_json = single_line
                
                parsed_json = json.loads(test_json)
                logger.debug(f"方式0解析成功: {parsed_json}")
                
                # 检查节点数量
                if len(parsed_json) > 1:
                    # 多个节点，不支持
                    logger.warning("检测到多个节点的JSON内容")
                    messagebox.showerror("错误", "请输入单个节点的JSON内容，多个节点格式不被支持。\n\n请修改输入后重试。")
                    return
                elif len(parsed_json) == 1:
                    # 单个节点，获取节点ID和内容
                    node_id, node_content = next(iter(parsed_json.items()))
                    parsing_succeeded = True
                    logger.info("✅ 方式0解析成功")
                else:
                    # 空对象
                    logger.warning("检测到空JSON对象")
                    messagebox.showerror("错误", "请输入有效的JSON内容，不能为空对象。\n\n请修改输入后重试。")
                    return
            except Exception as e0:
                logger.error(f"方式0解析失败: {e0}")
                
                # 方式1：尝试作为完整JSON对象解析（带数字键）
                try:
                    # 检查是否已经有外层大括号
                    if not (processed_text.startswith('{') and processed_text.endswith('}')):
                        # 尝试添加大括号
                        json_with_braces = f"{{ {processed_text} }}"
                        logger.debug(f"添加大括号后: {json_with_braces[:100]}...")
                    else:
                        json_with_braces = processed_text
                    
                    # 解析JSON
                    parsed_json = json.loads(json_with_braces)
                    logger.debug(f"解析成功: {parsed_json}")
                    
                    # 检查节点数量
                    if len(parsed_json) > 1:
                        # 多个节点，不支持
                        logger.warning("检测到多个节点的JSON内容")
                        messagebox.showerror("错误", "请输入单个节点的JSON内容，多个节点格式不被支持。\n\n请修改输入后重试。")
                        return
                    elif len(parsed_json) == 1:
                        # 单个节点，获取节点ID和内容
                        node_id, node_content = next(iter(parsed_json.items()))
                        parsing_succeeded = True
                        logger.info("✅ 方式1解析成功")
                    else:
                        # 空对象
                        logger.warning("检测到空JSON对象")
                        messagebox.showerror("错误", "请输入有效的JSON内容，不能为空对象。\n\n请修改输入后重试。")
                        return
                except json.JSONDecodeError as e1:
                    logger.error(f"方式1解析失败: {e1}")
                    
                    # 方式2：尝试用正则表达式提取数字键和内容
                    try:
                        # 匹配格式："数字": {...} 或 数字: {...}
                        pattern = re.compile(r'^\s*["\']?([\d]+)["\']?\s*:\s*(\{.*\})\s*$', re.DOTALL)
                        match = pattern.match(processed_text)
                        if match:
                            node_id = match.group(1)
                            node_content_str = match.group(2)
                            node_content = json.loads(node_content_str)
                            parsing_succeeded = True
                            logger.info("✅ 方式2解析成功")
                        else:
                            logger.error("未匹配到数字键格式")
                    except Exception as e2:
                        logger.error(f"方式2解析失败: {e2}")
                        
                        # 方式3：尝试作为单个节点内容解析
                        try:
                            # 检查是否包含数字键格式（如 "84": ）
                            key_value_pattern = re.compile(r'^\s*["\']?([\d]+)["\']?\s*:\s*(.*)$', re.DOTALL)
                            key_value_match = key_value_pattern.match(processed_text)
                            if key_value_match:
                                node_id = key_value_match.group(1)
                                content_part = key_value_match.group(2).strip()
                                # 尝试解析内容部分
                                node_content = json.loads(content_part)
                                parsing_succeeded = True
                                logger.info("✅ 方式3解析成功")
                            else:
                                logger.error("未匹配到键值对格式")
                        except Exception as e3:
                            logger.error(f"方式3解析失败: {e3}")
            
            if not parsing_succeeded:
                # 所有解析方式都失败，提示错误
                error_msg = "JSON解析失败，请检查输入的JSON格式是否正确。\n\n"
                error_msg += "请确保输入格式为：\n\n"
                error_msg += '"58": { ... }\n\n或\n\n58: { ... }\n\n'
                error_msg += "并确保JSON内容格式正确，没有语法错误。"
                # 创建自定义错误窗口，不影响主窗口层级
                error_window = tk.Toplevel(self.parent)
                error_window.title("JSON解析错误")
                error_window.geometry("400x250")
                error_window.resizable(False, False)
                # 不设置为置顶，保持主窗口层级不变
                # error_window.attributes('-topmost', True)
                
                # 计算窗口位置，使其居中在父窗口正中间
                parent_x = self.parent.winfo_x()
                parent_y = self.parent.winfo_y()
                parent_width = self.parent.winfo_width()
                parent_height = self.parent.winfo_height()
                
                # 计算错误窗口的位置
                error_width = 400
                error_height = 250
                x = parent_x + (parent_width - error_width) // 2
                y = parent_y + (parent_height - error_height) // 2
                
                # 设置窗口位置
                error_window.geometry(f"{error_width}x{error_height}+{x}+{y}")
                
                # 创建错误内容标签
                error_label = ttk.Label(error_window, text=error_msg, wraplength=380, justify="left")
                error_label.pack(padx=20, pady=20, fill=tk.X, expand=True)
                
                # 创建按钮框架
                button_frame = ttk.Frame(error_window)
                button_frame.pack(fill=tk.X, pady=10, padx=20)
                
                # 创建确定按钮
                ok_button = ttk.Button(button_frame, text="确定", command=error_window.destroy, width=10, bootstyle="primary")
                ok_button.pack(side=tk.RIGHT, padx=5, pady=5)
                
                # 设置窗口关闭回调
                error_window.protocol("WM_DELETE_WINDOW", error_window.destroy)
                return
            
            # 步骤2：将JSON转换为单行形式
            try:
                # 转换为单行JSON
                single_line_content = json.dumps(node_content, ensure_ascii=False, separators=(',', ':'))
                # 重新组合带有数字键的格式
                single_line_code = f'"{node_id}": {single_line_content}'
                
                # 更新代码输入框为单行形式
                var_data["code_entry"].delete("1.0", tk.END)
                var_data["code_entry"].insert("1.0", single_line_code)
                
                logger.info(f"JSON已转换为单行形式: {single_line_code[:100]}...")
            except Exception as e:
                logger.error(f"转换为单行JSON失败: {e}")
                # 转换失败不影响后续检测，继续使用原代码
                single_line_code = code_text
            
            # 步骤3：处理节点数据
            processed_nodes = []
            
            # 创建处理后的节点
            processed_nodes.append({
                'id': node_id,
                'title': node_content.get('_meta', {}).get('title', node_content.get('class_type', '')),
                'inputs': {k: v if not isinstance(v, list) else ', '.join(map(str, v)) for k, v in node_content.get('inputs', {}).items()}
            })
            
            logger.debug(f"成功解析带数字键的节点，ID: {node_id}")
            logger.info(f"处理完成，共找到 {len(processed_nodes)} 个节点")
            
            # 创建检测结果窗口
            self.show_check_result(index, processed_nodes)
            logger.info("检测结果窗口已创建")
            
        except Exception as e:
            # 最外层异常处理，确保程序不会崩溃
            import traceback
            logger.error(f"检测变量时发生未知错误: {e}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            
            # 显示简洁的错误信息
            error_msg = f"检测过程中发生错误: {str(e)}\n\n"
            error_msg += "程序已捕获异常，不会崩溃。\n"
            error_msg += "请检查输入的JSON格式是否正确，确保是单个节点格式。\n\n"
            error_msg += "正确格式示例：\n\"58\": { ... }\n或\n58: { ... }"
            # 创建自定义错误窗口，不影响主窗口层级
            error_window = tk.Toplevel(self.parent)
            error_window.title("错误")
            error_window.geometry("400x250")
            error_window.resizable(False, False)
            # 不设置为置顶，保持主窗口层级不变
            # error_window.attributes('-topmost', True)
            
            # 计算窗口位置，使其居中在父窗口正中间
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            # 计算错误窗口的位置
            error_width = 400
            error_height = 250
            x = parent_x + (parent_width - error_width) // 2
            y = parent_y + (parent_height - error_height) // 2
            
            # 设置窗口位置
            error_window.geometry(f"{error_width}x{error_height}+{x}+{y}")
            
            # 创建错误内容标签
            error_label = ttk.Label(error_window, text=error_msg, wraplength=380, justify="left")
            error_label.pack(padx=20, pady=20, fill=tk.X, expand=True)
            
            # 创建按钮框架
            button_frame = ttk.Frame(error_window)
            button_frame.pack(fill=tk.X, pady=10, padx=20)
            
            # 创建确定按钮
            ok_button = ttk.Button(button_frame, text="确定", command=error_window.destroy, width=10, bootstyle="primary")
            ok_button.pack(side=tk.RIGHT, padx=5, pady=5)
            
            # 设置窗口关闭回调
            error_window.protocol("WM_DELETE_WINDOW", error_window.destroy)
    
    def show_check_result(self, index, processed_nodes):
        # 检查是否已经有弹窗打开
        if self.result_window_open:
            # 如果已经打开，激活并置顶
            self.result_window.lift()
            self.result_window.focus_force()
            return
        
        # 创建检测结果窗口
        self.result_window = tk.Toplevel(self.parent)
        self.result_window.title(tr("变量明细检测结果"))
        
        # 设置窗口大小
        window_width = 400
        window_height = 500
        self.result_window.geometry(f"{window_width}x{window_height}")
        self.result_window.resizable(True, True)
        
        # 计算窗口位置，使其居中在父窗口正中间
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # 计算居中位置
        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2
        
        # 设置窗口位置
        self.result_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 设置窗口为置顶
        self.result_window.attributes('-topmost', True)
        
        # 设置窗口关闭时的回调
        def on_window_close():
            self.result_window_open = False
            self.result_window.destroy()
        
        self.result_window.protocol("WM_DELETE_WINDOW", on_window_close)
        self.result_window_open = True
        
        # 创建主框架
        main_frame = ttk.Frame(self.result_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 变量选择
        selected_var = tk.StringVar()
        current_node = None
        
        # 创建容器框架，用于分隔滚动区域和信息区域
        container_frame = ttk.Frame(main_frame)
        container_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建滚动区域
        canvas = tk.Canvas(container_frame)
        scrollbar = ttk.Scrollbar(container_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill=tk.BOTH, expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 创建节点列表
        for node in processed_nodes:
            current_node = node
            # 显示节点标题行：节点ID.节点标题（图2格式）
            node_title_label = ttk.Label(scrollable_frame, text=f"{node['id']}.{node['title']}", font=("Arial", 10, "bold"))
            node_title_label.pack(anchor=tk.W, pady=5, padx=5)
            
            # 显示节点属性
            for attr_name, attr_value in node["inputs"].items():
                # 创建勾选项
                frame = ttk.Frame(scrollable_frame)
                frame.pack(fill=tk.X, pady=2, padx=20)
                
                # 组合选项值，包含节点信息和属性信息
                option_value = f"{attr_name}:{attr_value}"
                
                # 创建单选按钮
                radio_btn = ttk.Radiobutton(frame, variable=selected_var, value=option_value)
                radio_btn.pack(side=tk.LEFT, padx=5)
                
                # 属性标签
                attr_label = ttk.Label(frame, text=f"{attr_name}: {attr_value}", font=("Arial", 9))
                attr_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 添加分隔线
        separator = ttk.Separator(scrollable_frame, orient="horizontal")
        separator.pack(fill=tk.X, pady=10, padx=5)
        
        # 节点信息标签 - 使用默认字体
        node_info_label = ttk.Label(scrollable_frame, text=tr("节点名称: "))
        node_info_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # 标题信息标签 - 使用默认字体
        title_info_label = ttk.Label(scrollable_frame, text=tr("标题名称: "))
        title_info_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # 寻址代码标签 - 使用默认字体，修正了"称寻址代码:"的拼写
        address_info_label = ttk.Label(scrollable_frame, text=tr("寻址代码: "))
        address_info_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # 动态更新寻址代码的函数
        def update_address_code():
            selected_value = selected_var.get()
            if selected_value and current_node:
                attr_name, attr_value = selected_value.split(":", 1)
                # 更新节点信息和寻址代码
                node_info_label.config(text=tr("节点名称: ") + f"{current_node['id']}")
                title_info_label.config(text=tr("标题名称: ") + f"{current_node['title']}")
                address_code = f'data["{current_node["id"]}"]["inputs"]["{attr_name}"] = "{attr_value}"'
                address_info_label.config(text=tr("寻址代码: ") + f"{address_code}")
        
        # 绑定单选按钮变化事件
        selected_var.trace_add("write", lambda *args: update_address_code())
        
        # 按钮框架 - 直接显示在标签下方
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, pady=10, padx=5)
        
        def on_confirm_click(index=index):
            # 获取当前选中的属性
            selected_value = selected_var.get()
            if selected_value and current_node:
                attr_name, attr_value = selected_value.split(":", 1)
                # 生成寻址代码
                address_code = f'data["{current_node["id"]}"]["inputs"]["{attr_name.strip()}"] = "{attr_value.strip()}"'
                
                # 将寻址代码复制到变量明细输入框
                self.variables[index]["detail_entry"].delete(0, tk.END)
                self.variables[index]["detail_entry"].insert(0, address_code)
                
                # 将节点ID和标题以"85-K采样器(高级)"格式赋值到变量名称输入框
                node_combined_name = f"{current_node['id']}-{current_node['title']}"
                self.variables[index]["name_entry"].delete(0, tk.END)
                self.variables[index]["name_entry"].insert(0, node_combined_name)
                
                # 关闭窗口
                on_window_close()
        
        def on_cancel_click():
            # 直接关闭窗口
            on_window_close()
        
        # 创建确定按钮 - 改成红色
        confirm_btn = ttk.Button(button_frame, text=tr("确定"), command=on_confirm_click, width=8, bootstyle="danger")
        confirm_btn.pack(side=tk.LEFT, padx=5)
        
        # 创建取消按钮 - 无特殊样式，使用默认
        cancel_btn = ttk.Button(button_frame, text=tr("取消"), command=on_cancel_click, width=8)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    # 查找功能相关方法
    def find_next(self, event=None):
        # 查找下一个匹配项
        self.find(False)
    
    def find_previous(self, event=None):
        # 查找上一个匹配项
        self.find(True)
    
    def find(self, backwards=False):
        # 查找逻辑
        search_text = self.search_entry.get()
        if not search_text:
            return
        
        # 清除之前的高亮
        self.clear_search_highlight()
        
        # 查找当前位置
        current_pos = self.json_text.search(search_text, "insert", backwards=backwards)
        
        if not current_pos:
            # 如果没有找到，从头开始查找
            current_pos = self.json_text.search(search_text, "1.0", backwards=backwards)
        
        if current_pos:
            # 高亮显示找到的文本
            end_pos = f"{current_pos}+{len(search_text)}c"
            self.json_text.tag_add("search_highlight", current_pos, end_pos)
            self.json_text.tag_config("search_highlight", background="yellow", foreground="black")
            # 滚动到找到的位置
            self.json_text.see(current_pos)
            # 将光标移动到找到的位置
            self.json_text.mark_set("insert", end_pos)
    
    def clear_search_highlight(self):
        # 清除所有查找高亮
        self.json_text.tag_remove("search_highlight", "1.0", "end")
    
    def create_variable_frame(self, parent, index):
        # 创建变量框架
        var_frame = ttk.Labelframe(parent, text=tr("变量") + f" {index+1}", padding="10")
        var_frame.pack(fill=tk.X, expand=False, pady=5)
        
        # 主容器：左侧输入框，右侧按钮
        main_frame = ttk.Frame(var_frame)
        main_frame.pack(fill=tk.X, expand=True)
        
        # 左侧：变量名称、代码、明细输入框
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 变量绑定下拉菜单
        binding_frame = ttk.Frame(left_frame)
        binding_frame.pack(fill=tk.X, pady=2)
        ttk.Label(binding_frame, text=tr("变量绑定:"), width=10).pack(side=tk.LEFT, padx=5)
        binding_var = tk.StringVar()
        # 直接使用从配置文件读取的选项（已根据语言选择）
        binding_combobox = ttk.Combobox(binding_frame, textvariable=binding_var, values=self.binding_options, state="readonly", width=20)
        binding_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 确保bindings_default在binding_options中
        if self.bindings_default not in self.binding_options and self.bindings_default:
            self.binding_options.append(self.bindings_default)
            binding_combobox.configure(values=self.binding_options)
        
        # 设置默认绑定值
        binding_var.set(self.bindings_default)  # 直接使用配置的默认值
        # 如果默认值无效且有选项，使用第一个选项
        if binding_var.get() not in self.binding_options and self.binding_options:
            binding_var.set(self.binding_options[0])
        
        # 变量名称输入框
        name_frame = ttk.Frame(left_frame)
        name_frame.pack(fill=tk.X, pady=2)
        ttk.Label(name_frame, text=tr("变量名称:"), width=10).pack(side=tk.LEFT, padx=5)
        name_entry = ttk.Entry(name_frame)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 变量代码输入框
        code_frame = ttk.Frame(left_frame)
        code_frame.pack(fill=tk.X, pady=2)
        ttk.Label(code_frame, text=tr("变量代码:"), width=10).pack(side=tk.LEFT, padx=5)
        code_entry = tk.Text(code_frame, height=4, width=40)
        code_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 变量明细输入框
        detail_frame = ttk.Frame(left_frame)
        detail_frame.pack(fill=tk.X, pady=2)
        ttk.Label(detail_frame, text=tr("变量明细:"), width=10).pack(side=tk.LEFT, padx=5)
        detail_entry = ttk.Entry(detail_frame)
        detail_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 右侧：检测按钮和清除按钮
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, padx=5)
        
        # 检测按钮
        check_button = ttk.Button(right_frame, text=tr("检测"), command=lambda: self.check_variable(index), width=10)
        check_button.pack(pady=5)
        
        # 清除按钮
        clear_button = ttk.Button(right_frame, text=tr("清除"), command=lambda: self.clear_variable(index), width=10)
        clear_button.pack(pady=5)
        
        # 绑定输入事件，实现自动检测按钮变色
        def on_input_change(event=None):
            # 当输入变化时，调用自动检测方法
            self.update_button_colors()
        
        # 为变量绑定下拉菜单绑定事件
        binding_var.trace_add("write", lambda *args: on_input_change())
        
        # 为文本框绑定事件
        name_entry.bind("<KeyRelease>", on_input_change)
        code_entry.bind("<KeyRelease>", on_input_change)
        detail_entry.bind("<KeyRelease>", on_input_change)
        code_entry.bind("<ButtonRelease-1>", on_input_change)  # 处理鼠标选择
        
        # 将变量数据添加到列表中
        var_data = {
            "frame": var_frame,
            "binding_var": binding_var,
            "binding_combobox": binding_combobox,
            "name_entry": name_entry,
            "code_entry": code_entry,
            "detail_entry": detail_entry,
            "check_button": check_button,
            "clear_button": clear_button
        }
        
        # 确保self.variables列表有足够的空间
        while len(self.variables) <= index:
            self.variables.append(None)
        
        # 更新或添加变量数据
        self.variables[index] = var_data
    
    def update_button_colors(self):
        # 自动检测按钮变色逻辑
        for index in range(len(self.copy_buttons)):
            if index < len(self.variables):
                var_data = self.variables[index]
                binding_value = var_data["binding_var"].get()
                name_content = var_data["name_entry"].get().strip()
                code_content = var_data["code_entry"].get("1.0", tk.END).strip()
                detail_content = var_data["detail_entry"].get().strip()
                
                # 规则1：当变量绑定为默认值且其他三个文本框都为空时，显示默认颜色
                # 规则2：否则显示红色
                should_be_red = (binding_value != self.bindings_default) or bool(name_content) or bool(code_content) or bool(detail_content)
                if should_be_red:
                    self.copy_buttons[index].configure(bootstyle="danger")  # 红色
                else:
                    self.copy_buttons[index].configure(bootstyle="default")  # 默认颜色
        self.update_idletasks()
    
    def load_json_files(self):
        # 清空文件列表
        self.file_listbox.delete(0, tk.END)
        
        # 添加返回上一级选项（如果当前目录不是根目录）
        parent_dir = os.path.dirname(self.api_dir)
        if parent_dir != self.api_dir:  # 当前目录不是根目录
            self.file_listbox.insert(tk.END, f"📁 返回上一级/")
        
        # 获取目录中的所有文件和文件夹
        try:
            items = os.listdir(self.api_dir)
        except Exception as e:
            messagebox.showerror("错误", f"无法读取目录: {str(e)}")
            return
        
        # 过滤出JSON文件和文件夹
        json_files = []
        folders = []
        for item in items:
            item_path = os.path.join(self.api_dir, item)
            if os.path.isdir(item_path):
                folders.append(item)
            elif os.path.isfile(item_path) and item.endswith('.json'):
                json_files.append(item)
        
        # 按名称排序，文件夹在前，文件在后
        folders.sort()
        json_files.sort()
        
        # 添加文件夹到列表
        for folder in folders:
            self.file_listbox.insert(tk.END, f"📁 {folder}/")
        
        # 添加JSON文件到列表
        for json_file in json_files:
            self.file_listbox.insert(tk.END, f"📄 {json_file}")
    
    def on_file_double_click(self, event):
        # 获取选中的文件名
        selection = self.file_listbox.curselection()
        if not selection:
            return
        
        selected_index = selection[0]
        selected_item = self.file_listbox.get(selected_index)
        
        # 处理返回上一级
        if selected_item == "📁 返回上一级/":
            # 获取当前目录的父目录
            parent_dir = os.path.dirname(self.api_dir)
            if parent_dir != self.api_dir:  # 确保不是根目录
                # 将当前目录添加到历史记录中，以便可以返回
                self.dir_history.append(self.api_dir)
                # 切换到父目录
                self.api_dir = parent_dir
                self.load_json_files()
            return
        
        # 处理文件夹
        if selected_item.startswith("📁 "):
            folder_name = selected_item[2:-1]  # 去掉"📁 "和末尾的"/"
            self.dir_history.append(self.api_dir)
            self.api_dir = os.path.join(self.api_dir, folder_name)
            self.load_json_files()
            return
        
        # 处理JSON文件
        if selected_item.startswith("📄 "):
            json_filename = selected_item[2:]  # 去掉"📄 "
            json_path = os.path.join(self.api_dir, json_filename)
            self.current_json_file = json_path
            
            # 读取JSON文件内容
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.json_text.delete("1.0", tk.END)
                self.json_text.insert("1.0", content)
                
                # 更新标题
                self.json_frame_title = f"JSON内容 - 当前打开文件: {json_filename}"
                self.json_frame.configure(text=self.json_frame_title)
                self.current_opened_file = json_filename
                self.current_json_content = content
            except Exception as e:
                messagebox.showerror("错误", f"无法读取JSON文件: {str(e)}")

if __name__ == "__main__":
    # 鍏堝垱寤篢kinterDnD鏍圭獥鍙?
    root = TkinterDnD.Tk()
    # 搴旂敤ttkbootstrap鏍峰紡
    root.style = ttk.Style()
    root.style.theme_use("cosmo")
    app = CreativeArea(root)
    root.mainloop()