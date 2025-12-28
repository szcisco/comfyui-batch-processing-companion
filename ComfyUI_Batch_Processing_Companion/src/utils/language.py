#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多语言支持模块
实现中英文界面切换功能
"""

# 语言翻译字典
TRANSLATIONS = {
    # 窗口标题
    "ComfyUI批量处理伴侣": {
        "zh_CN": "ComfyUI批量处理伴侣",
        "en_US": "ComfyUI Batch Processing Companion"
    },
    "未保存": {
        "zh_CN": "未保存",
        "en_US": "Unsaved"
    },
    "已编辑": {
        "zh_CN": "已编辑",
        "en_US": "Edited"
    },
    
    # 菜单栏
    "文件": {
        "zh_CN": "文件",
        "en_US": "File"
    },
    "exit": {
        "zh_CN": "退出",
        "en_US": "Exit"
    },
    "API设置": {
        "zh_CN": "API设置",
        "en_US": "API Settings"
    },
    "系统设置": {
        "zh_CN": "系统设置",
        "en_US": "System Settings"
    },
    "联系作者": {
        "zh_CN": "联系作者",
        "en_US": "Contact Author"
    },
    
    # 系统设置对话框
    "生图API超时时间(分钟):": {
        "zh_CN": "生图API超时时间(分钟):",
        "en_US": "Image API Timeout (min):"
    },
    "文本框字符大小:": {
        "zh_CN": "文本框字符大小:",
        "en_US": "Text Box Font Size:"
    },
    "程序主题:": {
        "zh_CN": "程序主题:",
        "en_US": "Theme:"
    },
    "语言:": {
        "zh_CN": "语言:",
        "en_US": "Language:"
    },
    "中文简体": {
        "zh_CN": "中文简体",
        "en_US": "Chinese Simplified"
    },
    "English": {
        "zh_CN": "English",
        "en_US": "English"
    },
    "保存": {
        "zh_CN": "保存",
        "en_US": "Save"
    },
    "取消": {
        "zh_CN": "取消",
        "en_US": "Cancel"
    },
    "确定": {
        "zh_CN": "确定",
        "en_US": "OK"
    },
    
    # 顶部框体
    "当前工作流": {
        "zh_CN": "当前工作流",
        "en_US": "Current Workflow"
    },
    "测试API": {
        "zh_CN": "测试API",
        "en_US": "Test API"
    },
    "状态: 未测试": {
        "zh_CN": "状态: 未测试",
        "en_US": "Status: Not Tested"
    },
    "状态: 测试中...": {
        "zh_CN": "状态: 测试中...",
        "en_US": "Status: Testing..."
    },
    "状态: 正常": {
        "zh_CN": "状态: 正常",
        "en_US": "Status: OK"
    },
    "状态: 异常": {
        "zh_CN": "状态: 异常",
        "en_US": "Status: Error"
    },
    "状态: 错误": {
        "zh_CN": "状态: 错误",
        "en_US": "Status: Error"
    },
    "更换API": {
        "zh_CN": "更换API",
        "en_US": "Change API"
    },
    "索引- 未加载": {
        "zh_CN": "索引- 未加载",
        "en_US": "Index- Not Loaded"
    },
    "图片": {
        "zh_CN": "图片",
        "en_US": "Image"
    },
    "批量导入图片": {
        "zh_CN": "批量导入图片",
        "en_US": "Batch Import"
    },
    "批量删除图片": {
        "zh_CN": "批量删除图片",
        "en_US": "Batch Delete"
    },
    "批量删除出图": {
        "zh_CN": "批量删除出图",
        "en_US": "Delete Output"
    },
    "批量导出图片": {
        "zh_CN": "批量导出图片",
        "en_US": "Batch Export"
    },
    "批量拖入图片区域": {
        "zh_CN": "批量拖入图片区域",
        "en_US": "Drag & Drop Area"
    },
    "将多张图片拖入此区域，按升序分配到每行图片框": {
        "zh_CN": "将多张图片拖入此区域，按升序分配到每行图片框",
        "en_US": "Drag images here to assign to each row in order"
    },
    "动作提示词": {
        "zh_CN": "动作提示词",
        "en_US": "Action Prompts"
    },
    "批量生成新资源": {
        "zh_CN": "批量生成新资源",
        "en_US": "Batch Generate"
    },
    "图片参数(全局)": {
        "zh_CN": "图片参数(全局)",
        "en_US": "Image Params (Global)"
    },
    "K采样器步数:": {
        "zh_CN": "K采样器步数:",
        "en_US": "K Sampler Steps:"
    },
    "图片尺寸:": {
        "zh_CN": "图片尺寸:",
        "en_US": "Image Size:"
    },
    "高": {
        "zh_CN": "高",
        "en_US": "H"
    },
    "宽": {
        "zh_CN": "宽",
        "en_US": "W"
    },
    "竖屏": {
        "zh_CN": "竖屏",
        "en_US": "Portrait"
    },
    "横屏": {
        "zh_CN": "横屏",
        "en_US": "Landscape"
    },
    "批量同步": {
        "zh_CN": "批量同步",
        "en_US": "Sync All"
    },
    "* 重复生成次数": {
        "zh_CN": "* 重复生成次数",
        "en_US": "* Repeat Count"
    },
    
    # 批量翻译按钮
    "Tencent批量翻译": {
        "zh_CN": "Tencent批量翻译",
        "en_US": "Tencent Batch Trans"
    },
    "Ollama批量翻译": {
        "zh_CN": "Ollama批量翻译",
        "en_US": "Ollama Batch Trans"
    },
    "批量直译": {
        "zh_CN": "批量直译",
        "en_US": "Batch Copy"
    },
    "停止翻译": {
        "zh_CN": "停止翻译",
        "en_US": "Stop Translation"
    },
    
    # 内容行
    "拖入图片或点击导入": {
        "zh_CN": "拖入图片或点击导入",
        "en_US": "Drop or Click to Import"
    },
    "正向提示词": {
        "zh_CN": "正向提示词",
        "en_US": "Positive Prompt"
    },
    "负面提示词": {
        "zh_CN": "负面提示词",
        "en_US": "Negative Prompt"
    },
    "中文提示词": {
        "zh_CN": "中文提示词",
        "en_US": "Chinese Prompt"
    },
    "英文翻译": {
        "zh_CN": "英文翻译",
        "en_US": "English Translation"
    },
    "中文负面提示词": {
        "zh_CN": "中文负面提示词",
        "en_US": "Chinese Negative"
    },
    "英文负面翻译": {
        "zh_CN": "英文负面翻译",
        "en_US": "English Negative"
    },
    "腾讯翻译(正向)": {
        "zh_CN": "腾讯翻译(正向)",
        "en_US": "Tencent Trans(+)"
    },
    "Ollama翻译(正向)": {
        "zh_CN": "Ollama翻译(正向)",
        "en_US": "Ollama Trans(+)"
    },
    "腾讯翻译(负面)": {
        "zh_CN": "腾讯翻译(负面)",
        "en_US": "Tencent Trans(-)"
    },
    "Ollama翻译(负面)": {
        "zh_CN": "Ollama翻译(负面)",
        "en_US": "Ollama Trans(-)"
    },
    "删除(正向)": {
        "zh_CN": "删除(正向)",
        "en_US": "Delete(+)"
    },
    "删除(负面)": {
        "zh_CN": "删除(负面)",
        "en_US": "Delete(-)"
    },
    "直译(正向)": {
        "zh_CN": "直译(正向)",
        "en_US": "Copy(+)"
    },
    "直译(负面)": {
        "zh_CN": "直译(负面)",
        "en_US": "Copy(-)"
    },
    
    # 图片参数
    "图片参数": {
        "zh_CN": "图片参数",
        "en_US": "Image Params"
    },
    "步数:": {
        "zh_CN": "步数:",
        "en_US": "Steps:"
    },
    "尺寸:": {
        "zh_CN": "尺寸:",
        "en_US": "Size:"
    },
    "重复:": {
        "zh_CN": "重复:",
        "en_US": "Repeat:"
    },
    
    # 生成按钮
    "生成图片(单个)": {
        "zh_CN": "生成图片(单个)",
        "en_US": "Generate (Single)"
    },
    "批量生成图片": {
        "zh_CN": "批量生成图片",
        "en_US": "Batch Generate"
    },
    "全选": {
        "zh_CN": "全选",
        "en_US": "Select All"
    },
    
    # API返回图片区域
    "API返回图片": {
        "zh_CN": "API返回图片",
        "en_US": "API Output"
    },
    
    # 状态文本
    "(none)": {
        "zh_CN": "(none)",
        "en_US": "(none)"
    },
    "(生成中)": {
        "zh_CN": "(生成中)",
        "en_US": "(Generating)"
    },
    "(完成)": {
        "zh_CN": "(完成)",
        "en_US": "(Done)"
    },
    "none": {
        "zh_CN": "none",
        "en_US": "none"
    },
    "translating": {
        "zh_CN": "翻译中",
        "en_US": "translating"
    },
    "translated": {
        "zh_CN": "已翻译",
        "en_US": "translated"
    },
    "pass": {
        "zh_CN": "通过",
        "en_US": "pass"
    },
    "error": {
        "zh_CN": "错误",
        "en_US": "error"
    },
    "无需翻译": {
        "zh_CN": "无需翻译",
        "en_US": "no translation"
    },
    "正向提示词(pass)": {
        "zh_CN": "正向提示词(pass)",
        "en_US": "Positive Prompt(pass)"
    },
    "负面提示词(pass)": {
        "zh_CN": "负面提示词(pass)",
        "en_US": "Negative Prompt(pass)"
    },
    "API返回图片(已生图-1张)": {
        "zh_CN": "API返回图片(已生图-1张)",
        "en_US": "API Output(Generated-1)"
    },
    "正在生成图片...": {
        "zh_CN": "正在生成图片...",
        "en_US": "Generating image..."
    },
    "API接口返回的新图片(生成中)": {
        "zh_CN": "API接口返回的新图片(生成中)",
        "en_US": "API Output Image(Generating)"
    },
    "正向提示词(translated)": {
        "zh_CN": "正向提示词(translated)",
        "en_US": "Positive Prompt(translated)"
    },
    "负面提示词(translated)": {
        "zh_CN": "负面提示词(translated)",
        "en_US": "Negative Prompt(translated)"
    },
    "生成中": {
        "zh_CN": "生成中",
        "en_US": "Generating"
    },
    "已生图": {
        "zh_CN": "已生图",
        "en_US": "Generated"
    },
    "张": {
        "zh_CN": "张",
        "en_US": ""
    },
    
    # 对话框
    "错误": {
        "zh_CN": "错误",
        "en_US": "Error"
    },
    "警告": {
        "zh_CN": "警告",
        "en_US": "Warning"
    },
    "提示": {
        "zh_CN": "提示",
        "en_US": "Info"
    },
    "确认": {
        "zh_CN": "确认",
        "en_US": "Confirm"
    },
    "是": {
        "zh_CN": "是",
        "en_US": "Yes"
    },
    "否": {
        "zh_CN": "否",
        "en_US": "No"
    },
    "确认退出": {
        "zh_CN": "确认退出",
        "en_US": "Confirm Exit"
    },
    "确定要退出程序吗？": {
        "zh_CN": "确定要退出程序吗？",
        "en_US": "Are you sure you want to exit?"
    },
    "有未保存的更改，确定要退出吗？": {
        "zh_CN": "有未保存的更改，确定要退出吗？",
        "en_US": "You have unsaved changes. Exit anyway?"
    },
    "图片文件": {
        "zh_CN": "图片文件",
        "en_US": "Image Files"
    },
    "所有文件": {
        "zh_CN": "所有文件",
        "en_US": "All Files"
    },
    "选择图片文件": {
        "zh_CN": "选择图片文件",
        "en_US": "Select Image File"
    },
    
    # API设置
    "Ollama API": {
        "zh_CN": "Ollama API",
        "en_US": "Ollama API"
    },
    "腾讯翻译 API": {
        "zh_CN": "腾讯翻译 API",
        "en_US": "Tencent Translate API"
    },
    "ComfyUI API": {
        "zh_CN": "ComfyUI API",
        "en_US": "ComfyUI API"
    },
    "ComfyUI API设置": {
        "zh_CN": "ComfyUI API设置",
        "en_US": "ComfyUI API Settings"
    },
    "API地址:": {
        "zh_CN": "API地址:",
        "en_US": "API URL:"
    },
    "超时时间(秒):": {
        "zh_CN": "超时时间(秒):",
        "en_US": "Timeout (sec):"
    },
    "工作流文件:": {
        "zh_CN": "工作流文件:",
        "en_US": "Workflow File:"
    },
    "选择文件": {
        "zh_CN": "选择文件",
        "en_US": "Browse"
    },
    "输出目录:": {
        "zh_CN": "输出目录:",
        "en_US": "Output Dir:"
    },
    "选择目录": {
        "zh_CN": "选择目录",
        "en_US": "Browse"
    },
    
    # 联系作者
    "技术交流:": {
        "zh_CN": "技术交流:",
        "en_US": "Tech Support:"
    },
    "开源项目地址：": {
        "zh_CN": "开源项目地址：",
        "en_US": "Open Source:"
    },
    "商务合作：": {
        "zh_CN": "商务合作：",
        "en_US": "Business:"
    },
    
    # 提示信息
    "数值越大,图质量越好, 耗时更多": {
        "zh_CN": "数值越大,图质量越好, 耗时更多",
        "en_US": "Higher value = better quality, longer time"
    },
    "主题预览": {
        "zh_CN": "主题预览",
        "en_US": "Theme Preview"
    },
    "主题选择": {
        "zh_CN": "主题选择",
        "en_US": "Theme Selection"
    },
    
    # 图片操作按钮
    "删除": {
        "zh_CN": "删除",
        "en_US": "Delete"
    },
    "替换": {
        "zh_CN": "替换",
        "en_US": "Replace"
    },
    "查看": {
        "zh_CN": "查看",
        "en_US": "View"
    },
    "删除提示词(正向)": {
        "zh_CN": "删除提示词(正向)",
        "en_US": "Delete Prompt(+)"
    },
    "删除提示词(负面)": {
        "zh_CN": "删除提示词(负面)",
        "en_US": "Delete Prompt(-)"
    },
    "API接口返回的新图片 (none)": {
        "zh_CN": "API接口返回的新图片 (none)",
        "en_US": "API Output Image (none)"
    },
    "API返回图片显示区域": {
        "zh_CN": "API返回图片显示区域",
        "en_US": "API Output Display Area"
    },
    "选择项目": {
        "zh_CN": "选择项目",
        "en_US": "Select Item"
    },
    "删除所有图片": {
        "zh_CN": "删除所有图片",
        "en_US": "Delete All Images"
    },
    "批量生成": {
        "zh_CN": "批量生成",
        "en_US": "Batch Generate"
    },
    
    # 计时器
    "计时器": {
        "zh_CN": "计时器",
        "en_US": "Timer"
    },
    "总计时:": {
        "zh_CN": "总计时:",
        "en_US": "Total:"
    },
    "生成时间:": {
        "zh_CN": "生成时间:",
        "en_US": "Generation Time:"
    },
    "全选项目": {
        "zh_CN": "全选项目",
        "en_US": "Select All"
    },
    "批量生成图片": {
        "zh_CN": "批量生成图片",
        "en_US": "Batch Generate Images"
    },
    
    # 项目管理
    "项目管理": {
        "zh_CN": "项目管理",
        "en_US": "Project Manager"
    },
    "新建项目": {
        "zh_CN": "新建项目",
        "en_US": "New Project"
    },
    "打开项目": {
        "zh_CN": "打开项目",
        "en_US": "Open Project"
    },
    "保存项目": {
        "zh_CN": "保存项目",
        "en_US": "Save Project"
    },
    "另存为": {
        "zh_CN": "另存为",
        "en_US": "Save As"
    },
    "修改文件名": {
        "zh_CN": "修改文件名",
        "en_US": "Rename"
    },
    
    # Push设置
    "Push设置": {
        "zh_CN": "Push设置",
        "en_US": "Push Settings"
    },
    
    # 主题描述
    "宇宙星空": {
        "zh_CN": "宇宙星空",
        "en_US": "Cosmic"
    },
    "清新简约": {
        "zh_CN": "清新简约",
        "en_US": "Flat"
    },
    "典雅日记": {
        "zh_CN": "典雅日记",
        "en_US": "Journal"
    },
    "清晰可读": {
        "zh_CN": "清晰可读",
        "en_US": "Readable"
    },
    "极简主义": {
        "zh_CN": "极简主义",
        "en_US": "Simple"
    },
    "和谐统一": {
        "zh_CN": "和谐统一",
        "en_US": "United"
    },
    "深邃暗黑": {
        "zh_CN": "深邃暗黑",
        "en_US": "Dark"
    },
    "沉稳石板": {
        "zh_CN": "沉稳石板",
        "en_US": "Slate"
    },
    "阳光活力": {
        "zh_CN": "阳光活力",
        "en_US": "Solar"
    },
    "未来机械": {
        "zh_CN": "未来机械",
        "en_US": "Cyborg"
    },
    "蒸汽波": {
        "zh_CN": "蒸汽波",
        "en_US": "Vapor"
    },
    "薄荷清新": {
        "zh_CN": "薄荷清新",
        "en_US": "Minty"
    },
    "轻盈文学": {
        "zh_CN": "轻盈文学",
        "en_US": "Litera"
    },
    "明亮光感": {
        "zh_CN": "明亮光感",
        "en_US": "Lumen"
    },
    "形态变换": {
        "zh_CN": "形态变换",
        "en_US": "Morph"
    },
    "律动脉搏": {
        "zh_CN": "律动脉搏",
        "en_US": "Pulse"
    },
    "手绘涂鸦": {
        "zh_CN": "手绘涂鸦",
        "en_US": "Sketchy"
    },
    "海蓝梦境": {
        "zh_CN": "海蓝梦境",
        "en_US": "Cerulean"
    },
    "超级英雄": {
        "zh_CN": "超级英雄",
        "en_US": "Superhero"
    },
    "砂岩质感": {
        "zh_CN": "砂岩质感",
        "en_US": "Sandstone"
    },
    "雪山精灵": {
        "zh_CN": "雪山精灵",
        "en_US": "Yeti"
    },
    "和风轻语": {
        "zh_CN": "和风轻语",
        "en_US": "Zephyr"
    },
    "默认主题": {
        "zh_CN": "默认主题",
        "en_US": "Default"
    },
    
    # 图片框体标题
    "图A": {
        "zh_CN": "图A",
        "en_US": "ImgA"
    },
    
    # 联系作者对话框
    "关闭": {
        "zh_CN": "关闭",
        "en_US": "Close"
    },
    "技术交流:": {
        "zh_CN": "技术交流:",
        "en_US": "Tech Support:"
    },
    "QQ群:": {
        "zh_CN": "QQ群:",
        "en_US": "QQ Group:"
    },
    "微信ID:": {
        "zh_CN": "微信ID:",
        "en_US": "WeChat ID:"
    },
    "开源项目地址:": {
        "zh_CN": "开源项目地址:",
        "en_US": "Open Source:"
    },
    "商务合作:": {
        "zh_CN": "商务合作:",
        "en_US": "Business:"
    },
    
    # ComfyUI API配置对话框
    "ComfyUI API配置": {
        "zh_CN": "ComfyUI API配置",
        "en_US": "ComfyUI API Config"
    },
    "ComfyUI文件列表": {
        "zh_CN": "ComfyUI文件列表",
        "en_US": "ComfyUI File List"
    },
    "序号": {
        "zh_CN": "序号",
        "en_US": "No."
    },
    "文件名": {
        "zh_CN": "文件名",
        "en_US": "Filename"
    },
    "选择API目录": {
        "zh_CN": "选择API目录",
        "en_US": "Select API Dir"
    },
    "重命名": {
        "zh_CN": "重命名",
        "en_US": "Rename"
    },
    "刷新列表": {
        "zh_CN": "刷新列表",
        "en_US": "Refresh"
    },
    "导入": {
        "zh_CN": "导入",
        "en_US": "Import"
    },
    "导出": {
        "zh_CN": "导出",
        "en_US": "Export"
    },
    "ini编辑": {
        "zh_CN": "ini编辑",
        "en_US": "Edit INI"
    },
    "正在使用的ComfyUI工作流": {
        "zh_CN": "正在使用的ComfyUI工作流",
        "en_US": "Current ComfyUI Workflow"
    },
    "当前API:": {
        "zh_CN": "当前API:",
        "en_US": "Current API:"
    },
    "当前脚本:": {
        "zh_CN": "当前脚本:",
        "en_US": "Current Script:"
    },
    "未选择": {
        "zh_CN": "未选择",
        "en_US": "Not Selected"
    },
    "选定工作流": {
        "zh_CN": "选定工作流",
        "en_US": "Select Workflow"
    },
    "测试API": {
        "zh_CN": "测试API",
        "en_US": "Test API"
    },
    
    # 腾讯翻译API配置对话框
    "腾讯翻译API配置": {
        "zh_CN": "腾讯翻译API配置",
        "en_US": "Tencent Translate API Config"
    },
    "API主机": {
        "zh_CN": "API主机",
        "en_US": "API Host"
    },
    "API动作": {
        "zh_CN": "API动作",
        "en_US": "API Action"
    },
    "API版本": {
        "zh_CN": "API版本",
        "en_US": "API Version"
    },
    "API区域": {
        "zh_CN": "API区域",
        "en_US": "API Region"
    },
    "浏览": {
        "zh_CN": "浏览",
        "en_US": "Browse"
    },
    
    # Ollama API配置对话框
    "Ollama API配置": {
        "zh_CN": "Ollama API配置",
        "en_US": "Ollama API Config"
    },
    "模型名称": {
        "zh_CN": "模型名称",
        "en_US": "Model Name"
    },
    "响应超时时间": {
        "zh_CN": "响应超时时间",
        "en_US": "Response Timeout"
    },
    
    # 确认关闭对话框
    "确认关闭": {
        "zh_CN": "确认关闭",
        "en_US": "Confirm Close"
    },
    "确定要关闭创作区域吗？": {
        "zh_CN": "确定要关闭创作区域吗？",
        "en_US": "Are you sure you want to close?"
    },
    "确定关闭": {
        "zh_CN": "确定关闭",
        "en_US": "Confirm"
    },
    
    # JSON转INI调试工具
    "JSON转INI调试工具": {
        "zh_CN": "JSON转INI调试工具",
        "en_US": "JSON to INI Debug Tool"
    },
    "JSON文件列表": {
        "zh_CN": "JSON文件列表",
        "en_US": "JSON File List"
    },
    "读取目录": {
        "zh_CN": "读取目录",
        "en_US": "Select Dir"
    },
    "刷新": {
        "zh_CN": "刷新",
        "en_US": "Refresh"
    },
    "返回上一级": {
        "zh_CN": "返回上一级",
        "en_US": "Go Back"
    },
    "JSON内容": {
        "zh_CN": "JSON内容",
        "en_US": "JSON Content"
    },
    "当前打开文件:": {
        "zh_CN": "当前打开文件:",
        "en_US": "Current File:"
    },
    "无": {
        "zh_CN": "无",
        "en_US": "None"
    },
    "下一个": {
        "zh_CN": "下一个",
        "en_US": "Next"
    },
    "上一个": {
        "zh_CN": "上一个",
        "en_US": "Previous"
    },
    "变量配置": {
        "zh_CN": "变量配置",
        "en_US": "Variable Config"
    },
    "寻址编辑": {
        "zh_CN": "寻址编辑",
        "en_US": "Address Edit"
    },
    "导出": {
        "zh_CN": "导出",
        "en_US": "Export"
    },
    "导入": {
        "zh_CN": "导入",
        "en_US": "Import"
    },
    "清除所有内容": {
        "zh_CN": "清除所有内容",
        "en_US": "Clear All"
    },
    "帮助(help)": {
        "zh_CN": "帮助(help)",
        "en_US": "Help"
    },
    "跳转到变量": {
        "zh_CN": "跳转到变量",
        "en_US": "Go to Variable"
    },
    "变量": {
        "zh_CN": "变量",
        "en_US": "Variable"
    },
    "变量绑定:": {
        "zh_CN": "变量绑定:",
        "en_US": "Binding:"
    },
    "变量名称:": {
        "zh_CN": "变量名称:",
        "en_US": "Name:"
    },
    "变量代码:": {
        "zh_CN": "变量代码:",
        "en_US": "Code:"
    },
    "变量明细:": {
        "zh_CN": "变量明细:",
        "en_US": "Detail:"
    },
    "检测": {
        "zh_CN": "检测",
        "en_US": "Detect"
    },
    "清除": {
        "zh_CN": "清除",
        "en_US": "Clear"
    },
    "配置保存成功": {
        "zh_CN": "配置保存成功",
        "en_US": "Config saved successfully"
    },
    "重命名文件": {
        "zh_CN": "重命名文件",
        "en_US": "Rename File"
    },
    "新文件名:": {
        "zh_CN": "新文件名:",
        "en_US": "New filename:"
    },
    "重命名成功": {
        "zh_CN": "重命名成功",
        "en_US": "Rename successful"
    },
    "重命名失败": {
        "zh_CN": "重命名失败",
        "en_US": "Rename failed"
    },
    "请选择要重命名的文件": {
        "zh_CN": "请选择要重命名的文件",
        "en_US": "Please select a file to rename"
    },
    "请选择要删除的文件": {
        "zh_CN": "请选择要删除的文件",
        "en_US": "Please select files to delete"
    },
    "确定要删除选中的文件吗？": {
        "zh_CN": "确定要删除选中的文件吗？",
        "en_US": "Are you sure you want to delete selected files?"
    },
    "删除成功": {
        "zh_CN": "删除成功",
        "en_US": "Delete successful"
    },
    "删除失败": {
        "zh_CN": "删除失败",
        "en_US": "Delete failed"
    },
    "请先选择工作流文件": {
        "zh_CN": "请先选择工作流文件",
        "en_US": "Please select a workflow file first"
    },
    "请选择要使用的工作流文件": {
        "zh_CN": "请选择要使用的工作流文件",
        "en_US": "Please select a workflow file to use"
    },
    "是否选择该comfyui工作流": {
        "zh_CN": "是否选择该comfyui工作流",
        "en_US": "Select this ComfyUI workflow?"
    },
    "文件名不能为空": {
        "zh_CN": "文件名不能为空",
        "en_US": "Filename cannot be empty"
    },
    "文件名已存在": {
        "zh_CN": "文件名已存在",
        "en_US": "Filename already exists"
    },
    "(暂无文件或文件夹)": {
        "zh_CN": "(暂无文件或文件夹)",
        "en_US": "(No files or folders)"
    },
    
    # 变量绑定选项
    "图片载入": {
        "zh_CN": "图片载入",
        "en_US": "Image Load"
    },
    "K采样步值": {
        "zh_CN": "K采样步值",
        "en_US": "K Sampler Steps"
    },
    "图片尺寸宽度": {
        "zh_CN": "图片尺寸宽度",
        "en_US": "Image Width"
    },
    "图片尺寸高度": {
        "zh_CN": "图片尺寸高度",
        "en_US": "Image Height"
    },
    "图片输出": {
        "zh_CN": "图片输出",
        "en_US": "Image Output"
    },
    "视频尺寸宽度": {
        "zh_CN": "视频尺寸宽度",
        "en_US": "Video Width"
    },
    "视频尺寸高度": {
        "zh_CN": "视频尺寸高度",
        "en_US": "Video Height"
    },
    
    # 变量明细检测结果窗口
    "变量明细检测结果": {
        "zh_CN": "变量明细检测结果",
        "en_US": "Variable Detail Detection Result"
    },
    "节点名称:": {
        "zh_CN": "节点名称:",
        "en_US": "Node Name:"
    },
    "标题名称:": {
        "zh_CN": "标题名称:",
        "en_US": "Title:"
    },
    "寻址代码:": {
        "zh_CN": "寻址代码:",
        "en_US": "Address Code:"
    },
    "节点名称: ": {
        "zh_CN": "节点名称: ",
        "en_US": "Node Name: "
    },
    "标题名称: ": {
        "zh_CN": "标题名称: ",
        "en_US": "Title: "
    },
    "寻址代码: ": {
        "zh_CN": "寻址代码: ",
        "en_US": "Address Code: "
    },
    
    # API测试消息
    "API测试中...": {
        "zh_CN": "API测试中...",
        "en_US": "API Testing..."
    },
    "ollama启动正常": {
        "zh_CN": "ollama启动正常",
        "en_US": "Ollama started successfully"
    },
    "ollama启动失败": {
        "zh_CN": "ollama启动失败",
        "en_US": "Ollama failed to start"
    },
    "翻译失败!请修改或检查模型名称再试!": {
        "zh_CN": "翻译失败!请修改或检查模型名称再试!",
        "en_US": "Translation failed! Please check model name!"
    },
    "请填写模型名称": {
        "zh_CN": "请填写模型名称",
        "en_US": "Please enter model name"
    },
    "腾讯翻译API连接成功": {
        "zh_CN": "腾讯翻译API连接成功",
        "en_US": "Tencent Translate API connected"
    },
    "Hello翻译成功": {
        "zh_CN": "Hello翻译成功",
        "en_US": "Hello translation successful"
    },
    "腾讯翻译API配置不完整，缺少必要参数": {
        "zh_CN": "腾讯翻译API配置不完整，缺少必要参数",
        "en_US": "Tencent API config incomplete"
    },
    
    # 导出ini配置
    "导出ini配置": {
        "zh_CN": "导出ini配置",
        "en_US": "Export INI Config"
    },
    "复制到变量": {
        "zh_CN": "复制到变量",
        "en_US": "Copy to Variable"
    },
    
    # 帮助窗口
    "帮助文档": {
        "zh_CN": "帮助文档",
        "en_US": "Help Document"
    },
    "中文": {
        "zh_CN": "中文",
        "en_US": "Chinese"
    },
    
    # 确认批量导入
    "确认批量导入": {
        "zh_CN": "确认批量导入",
        "en_US": "Confirm Batch Import"
    },
    "确认批量删除": {
        "zh_CN": "确认批量删除",
        "en_US": "Confirm Batch Delete"
    },
    "确定要批量删除所有图片和相关内容吗？此操作将重置所有行的数据，不可恢复！": {
        "zh_CN": "确定要批量删除所有图片和相关内容吗？此操作将重置所有行的数据，不可恢复！",
        "en_US": "Delete all images and content? This will reset all rows and cannot be undone!"
    },
    "确定删除": {
        "zh_CN": "确定删除",
        "en_US": "Confirm Delete"
    },
    "成功批量删除所有图片和相关内容": {
        "zh_CN": "成功批量删除所有图片和相关内容",
        "en_US": "Successfully deleted all images and content"
    },
    "确认批量删除出图": {
        "zh_CN": "确认批量删除出图",
        "en_US": "Confirm Delete Output Images"
    },
    "确定要批量删除所有图片的显示关系吗？\n此操作会清除程序的已生成图片的绑定显示关系，但不会删除png图片原文件。": {
        "zh_CN": "确定要批量删除所有图片的显示关系吗？\n此操作会清除程序的已生成图片的绑定显示关系，但不会删除png图片原文件。",
        "en_US": "Delete all image display bindings?\nThis will clear generated image bindings but won't delete the PNG files."
    },
    
    # 批量生成确认对话框
    "批量生成确认": {
        "zh_CN": "批量生成确认",
        "en_US": "Batch Generate Confirm"
    },
    "是否执行可批量生成任务?": {
        "zh_CN": "是否执行可批量生成任务?",
        "en_US": "Execute batch generation task?"
    },
    "确认删除": {
        "zh_CN": "确认删除",
        "en_US": "Confirm Delete"
    },
    "确定要批量删除此行的所有图片显示关系吗?此操作会清除程序的已生成图片的绑定显示关系，但不会删除png图片原文件。": {
        "zh_CN": "确定要批量删除此行的所有图片显示关系吗?此操作会清除程序的已生成图片的绑定显示关系，但不会删除png图片原文件。",
        "en_US": "Delete all image display bindings for this row? This will clear generated image bindings but won't delete the PNG files."
    },
    "确定删除": {
        "zh_CN": "确定删除",
        "en_US": "Confirm Delete"
    },
    
    # 选择目录
    "选择导出目录": {
        "zh_CN": "选择导出目录",
        "en_US": "Select Export Directory"
    },
    "导出完成": {
        "zh_CN": "导出完成",
        "en_US": "Export Complete"
    },
    "选择多张图片文件": {
        "zh_CN": "选择多张图片文件",
        "en_US": "Select Multiple Images"
    },
    "选择API JSON文件目录": {
        "zh_CN": "选择API JSON文件目录",
        "en_US": "Select API JSON Directory"
    },
    
    # 成功/失败消息
    "成功": {
        "zh_CN": "成功",
        "en_US": "Success"
    },
    "INI配置文件已导出到:": {
        "zh_CN": "INI配置文件已导出到:",
        "en_US": "INI config exported to:"
    },
    "导出INI配置文件失败:": {
        "zh_CN": "导出INI配置文件失败:",
        "en_US": "Failed to export INI config:"
    },
    "INI配置文件已导入": {
        "zh_CN": "INI配置文件已导入",
        "en_US": "INI config imported"
    },
    "导入INI配置文件失败:": {
        "zh_CN": "导入INI配置文件失败:",
        "en_US": "Failed to import INI config:"
    },
    
    # JSON解析错误
    "JSON解析错误": {
        "zh_CN": "JSON解析错误",
        "en_US": "JSON Parse Error"
    },
    "请输入变量代码": {
        "zh_CN": "请输入变量代码",
        "en_US": "Please enter variable code"
    },
    "请输入单个节点的JSON内容，多个节点格式不被支持。\n\n请修改输入后重试。": {
        "zh_CN": "请输入单个节点的JSON内容，多个节点格式不被支持。\n\n请修改输入后重试。",
        "en_US": "Please enter single node JSON. Multiple nodes not supported.\n\nPlease modify and retry."
    },
    "请输入有效的JSON内容，不能为空对象。\n\n请修改输入后重试。": {
        "zh_CN": "请输入有效的JSON内容，不能为空对象。\n\n请修改输入后重试。",
        "en_US": "Please enter valid JSON content, cannot be empty.\n\nPlease modify and retry."
    },
    
    # 无法读取
    "无法读取目录:": {
        "zh_CN": "无法读取目录:",
        "en_US": "Cannot read directory:"
    },
    "无法读取JSON文件:": {
        "zh_CN": "无法读取JSON文件:",
        "en_US": "Cannot read JSON file:"
    },
    
    # 消息框文本
    "没有需要翻译的内容": {
        "zh_CN": "没有需要翻译的内容",
        "en_US": "No content to translate"
    },
    "批量直译完成，共复制 {count} 条内容": {
        "zh_CN": "批量直译完成，共复制 {count} 条内容",
        "en_US": "Batch copy completed, {count} items copied"
    },
    "确定要删除选中的 {count} 个文件吗？": {
        "zh_CN": "确定要删除选中的 {count} 个文件吗？",
        "en_US": "Are you sure you want to delete {count} selected file(s)?"
    },
    "重命名文件": {
        "zh_CN": "重命名文件",
        "en_US": "Rename File"
    },
    "新文件名:": {
        "zh_CN": "新文件名:",
        "en_US": "New filename:"
    },
    "确认": {
        "zh_CN": "确认",
        "en_US": "Confirm"
    },
}

class LanguageManager:
    """语言管理器类"""
    
    _instance = None
    _current_language = "zh_CN"
    _callbacks = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def set_language(cls, language):
        """设置当前语言
        
        Args:
            language: 语言代码，"zh_CN" 或 "en_US"
        """
        if language in ["zh_CN", "en_US"]:
            cls._current_language = language
            # 触发所有注册的回调函数
            for callback in cls._callbacks:
                try:
                    callback()
                except Exception as e:
                    print(f"语言切换回调执行失败: {e}")
    
    @classmethod
    def get_language(cls):
        """获取当前语言"""
        return cls._current_language
    
    @classmethod
    def register_callback(cls, callback):
        """注册语言切换回调函数
        
        Args:
            callback: 回调函数，无参数
        """
        if callback not in cls._callbacks:
            cls._callbacks.append(callback)
    
    @classmethod
    def unregister_callback(cls, callback):
        """取消注册回调函数"""
        if callback in cls._callbacks:
            cls._callbacks.remove(callback)
    
    @classmethod
    def clear_callbacks(cls):
        """清除所有回调函数"""
        cls._callbacks.clear()


def tr(text):
    """翻译函数
    
    Args:
        text: 要翻译的文本（中文）
        
    Returns:
        翻译后的文本
    """
    current_lang = LanguageManager.get_language()
    
    if text in TRANSLATIONS:
        return TRANSLATIONS[text].get(current_lang, text)
    
    # 如果没有找到翻译，返回原文
    return text


def get_language_display_name(lang_code):
    """获取语言的显示名称
    
    Args:
        lang_code: 语言代码
        
    Returns:
        语言显示名称
    """
    names = {
        "zh_CN": "中文简体",
        "en_US": "English"
    }
    return names.get(lang_code, lang_code)


def get_language_code(display_name):
    """根据显示名称获取语言代码
    
    Args:
        display_name: 语言显示名称
        
    Returns:
        语言代码
    """
    codes = {
        "中文简体": "zh_CN",
        "English": "en_US"
    }
    return codes.get(display_name, "zh_CN")
