#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinterdnd2 import DND_FILES, TkinterDnD

class BaseUI:
    def __init__(self, root, config_manager, logger):
        self.root = root
        self.config_manager = config_manager
        self.logger = logger
        
        # 初始化样式
        self.style = ttk.Style()
        theme = self.config_manager.ui_theme
        self.style.theme_use(theme)
        
        # 设置窗口标题和大小
        self.root.title("创作区域")
        adjusted_height = max(self.config_manager.ui_height, 1200)
        self.root.geometry(f"{self.config_manager.ui_width}x{adjusted_height}")
        self.root.resizable(True, True)
        
        # 添加关闭窗口确认对话框
        self.root.protocol("WM_DELETE_WINDOW", self.confirm_exit)
        
        # 初始化变量
        self._init_variables()
        
        # 创建UI结构
        self._create_ui_structure()
    
    def _init_variables(self):
        """初始化变量"""
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
        
        # UI相关变量
        self.select_all_var = None
        self.global_k_sampler_steps = None
        self.global_image_height = None
        self.global_image_width = None
        self.global_orientation = None
        
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
    
    def _create_ui_structure(self):
        """创建UI结构"""
        # 创建固定顶部框架
        self.fixed_frame = ttk.Frame(self.root, padding="10")
        self.fixed_frame.pack(side=tk.TOP, fill=tk.X, expand=False)
        
        # 创建滚动区域
        self._create_scrollable_area()
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建网格布局
        self.create_grid_layout()
    
    def _create_scrollable_area(self):
        """创建滚动区域"""
        # 1. 创建Canvas作为滚动容器
        self.canvas = tk.Canvas(self.root, borderwidth=0, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 2. 创建垂直滚动条
        self.scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 3. 创建主框架，将其放在Canvas中
        self.main_frame = ttk.Frame(self.canvas, padding="10")
        
        # 4. 将主框架添加到Canvas的窗口中
        self.canvas.create_window((0, 0), window=self.main_frame, anchor=tk.NW)
        
        # 5. 绑定主框架大小变化事件，更新Canvas滚动区域
        self.main_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # 6. 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            # 对于Windows系统
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # 为Canvas绑定鼠标滚轮事件
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 7. 配置网格权重
        self.configure_grid_weights()
    
    def configure_grid_weights(self):
        """配置网格权重"""
        # 配置主框架的网格权重
        # 图片列
        self.main_frame.grid_columnconfigure(0, weight=1)
        # 正向提示词列
        self.main_frame.grid_columnconfigure(1, weight=1)
        # 负面提示词列
        self.main_frame.grid_columnconfigure(2, weight=1)
        # API图片列
        self.main_frame.grid_columnconfigure(3, weight=1)
        # 图片参数列
        self.main_frame.grid_columnconfigure(4, weight=0)
    
    def confirm_exit(self):
        """确认关闭窗口对话框"""
        # 创建自定义确认对话框
        exit_window = tk.Toplevel(self.root)
        exit_window.title("确认关闭")
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
        message = ttk.Label(main_frame, text="确定要关闭创作区域吗？", font=("Arial", 12))
        message.pack(pady=20)
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        # 确定关闭按钮
        def on_confirm():
            exit_window.destroy()
            self.root.destroy()
        
        confirm_btn = ttk.Button(btn_frame, text="确定关闭", command=on_confirm, style="danger.TButton", width=10)
        confirm_btn.pack(side=tk.LEFT, padx=10)
        
        # 取消按钮
        cancel_btn = ttk.Button(btn_frame, text="取消", command=exit_window.destroy, style="secondary.TButton", width=10)
        cancel_btn.pack(side=tk.LEFT, padx=10)
    
    def create_menu(self):
        """创建菜单栏"""
        # 创建菜单栏
        menubar = tk.Menu(self.root)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="项目管理", command=self.show_project_manager)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        # API设置菜单
        api_menu = tk.Menu(menubar, tearoff=0)
        api_menu.add_command(label="Ollama API", command=self.config_ollama_api)
        api_menu.add_command(label="腾讯翻译 API", command=self.config_translate_api)
        api_menu.add_command(label="ComfyUI API 状态", command=self.config_comfyui_status_api)
        api_menu.add_command(label="ComfyUI API 生图", command=self.config_comfyui_gen_api)
        menubar.add_cascade(label="API设置", menu=api_menu)
        
        # API测试菜单
        menubar.add_command(label="API测试", command=self.show_api_test)
        
        # 创作篇幅菜单
        menubar.add_command(label="创作篇幅", command=self.show_content_length_dialog)
        
        # 系统设置菜单
        menubar.add_command(label="系统设置", command=self.show_system_settings)
        
        # 设置菜单栏
        self.root.config(menu=menubar)
    
    def create_grid_layout(self):
        """创建网格布局"""
        # 创建顶部标题行
        self.create_top_row()
        
        # 创建批量翻译行
        self.create_batch_translate_row()
        
        # 从配置文件获取行数，默认30行
        content_rows = self.config_manager.content_rows
        
        # 创建内容行
        for i in range(content_rows):
            self.create_content_row(i)
    
    def create_top_row(self):
        """创建顶部标题行"""
        # 左侧图片区域 - LabelFrame
        self.img_frame = ttk.Labelframe(self.fixed_frame, text="图片")
        self.img_frame.grid(row=0, column=0, padx=5, pady=5, sticky=tk.NSEW)
        
        # 批量操作按钮框架
        batch_btn_frame = ttk.Frame(self.img_frame)
        batch_btn_frame.pack(padx=5, pady=5, fill=tk.X)
        
        # 批量导入图片按钮
        batch_import_btn = ttk.Button(batch_btn_frame, text="批量导入图片", command=self.batch_import_images, width=15)
        batch_import_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        # 批量删除图片按钮
        batch_delete_btn = ttk.Button(batch_btn_frame, text="批量删除图片", command=self.batch_delete_images, width=15)
        batch_delete_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        # 批量图片拖入区域 - 暂时注释拖放功能
        # drag_drop_frame = ttk.Labelframe(self.img_frame, text="批量拖入图片区域")
        # drag_drop_frame.pack(padx=5, pady=5, fill=tk.X)
        
        # 拖入提示
        # drag_drop_prompt = ttk.Label(drag_drop_frame, text="将多张图片拖入此区域，按升序分配到每行图片框", justify=tk.CENTER)
        # drag_drop_prompt.pack(padx=10, pady=20, expand=True)
        
        # 绑定拖入事件
        # drag_drop_frame.drop_target_register(DND_FILES)
        # drag_drop_frame.dnd_bind("<<Drop>>", self.handle_batch_drop)
        
        # 中间图生图动作提示词区域 - LabelFrame
        self.prompt_frame = ttk.Labelframe(self.fixed_frame, text="图生图动作提示词")
        self.prompt_frame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.NSEW)
        
        # 右侧API生成图片区域 - LabelFrame
        self.image_gen_frame = ttk.Labelframe(self.fixed_frame, text="API生成图片")
        self.image_gen_frame.grid(row=0, column=2, padx=5, pady=5, sticky=tk.NSEW)
    
    # 以下方法需要在子类中实现
    def create_batch_translate_row(self):
        """创建批量翻译行"""
        pass
    
    def create_content_row(self, row_index):
        """创建内容行"""
        pass
    
    def batch_import_images(self):
        """批量导入图片"""
        pass
    
    def batch_delete_images(self):
        """批量删除图片"""
        pass
    
    def handle_batch_drop(self, event):
        """处理批量拖入图片"""
        pass
    
    def show_project_manager(self):
        """显示项目管理器"""
        pass
    
    def config_ollama_api(self):
        """配置Ollama API"""
        pass
    
    def config_translate_api(self):
        """配置翻译API"""
        pass
    
    def config_comfyui_status_api(self):
        """配置ComfyUI状态API"""
        pass
    
    def config_comfyui_gen_api(self):
        """配置ComfyUI生成API"""
        pass
    
    def show_api_test(self):
        """显示API测试"""
        pass
    
    def show_content_length_dialog(self):
        """显示创作篇幅对话框"""
        pass
    
    def show_system_settings(self):
        """显示系统设置"""
        pass