# ComfyUI 批量处理伴侣 (ComfyUI Batch Processing Companion)

<p align="center">
  <img src="https://img.shields.io/badge/version-v1.0-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/python-3.8+-green.svg" alt="Python">
  <img src="https://img.shields.io/badge/license-GPLv3-orange.svg" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg" alt="Platform">
</p>

<p align="center">
  <b>专为 ComfyUI 用户打造的桌面端批量图像生成工具</b>
</p>

<p align="center">
  <a href="#项目简介">简介</a> •
  <a href="#核心功能">功能</a> •
  <a href="#安装使用">安装</a> •
  <a href="#使用说明">使用</a> •
  <a href="#联系方式">联系</a>
</p>

---

## 项目简介

ComfyUI 批量处理伴侣是一款专为 ComfyUI 用户打造的桌面端批量图像生成工具。它通过可视化界面简化了 ComfyUI API 的调用流程，让用户无需编写代码即可实现批量图生图、文生图等 AI 绘图任务。

## 核心功能

### 🖼️ 批量图像处理
支持一次性导入多张图片，配合提示词批量生成新图像。适用于需要大量处理相似风格图片的场景，如电商产品图优化、短视频素材批量制作、漫画分镜批量渲染等。

### ⚙️ 灵活的工作流管理
采用 JSON + INI 配置文件组合的方式管理 ComfyUI 工作流。用户可以从 ComfyUI 导出 API 格式的 JSON 工作流，配合 INI 配置文件定义参数映射关系，实现不同大模型、不同生图模式的快速切换。

### 🔗 智能参数绑定
通过可视化的变量配置面板，用户可以将工作流中的关键参数（如图片载入节点、提示词节点、采样步数、图片尺寸等）绑定到界面控件上。程序会自动识别工作流类型（图生图/文生图），并显示对应的操作界面。

### 🌐 多语言翻译集成
内置腾讯翻译 API 和 Ollama 本地大模型翻译两种方式，支持将中文提示词一键翻译为英文。对于需要处理大量中文描述的用户，可以批量翻译所有行的提示词，大幅提升工作效率。

### 🌍 中英文双语界面
完整支持中文简体和英文两种界面语言，可在设置中随时切换，同时支持中英文两种格式的工作流配置文件。

## 适用场景

- 🎨 AI 绘图工作室的批量出图需求
- 📱 短视频/自媒体创作者的素材批量生成
- 🛒 电商产品图的 AI 风格化处理
- 🎮 游戏/动漫美术的概念图批量迭代
- 🔧 任何需要调用 ComfyUI 进行批量图像处理的场景

## 技术特点

- 基于 Python + Tkinter 开发，跨平台支持
- 通过 HTTP API 与 ComfyUI 服务端通信，支持本地和远程部署
- 模块化的工作流配置系统，易于扩展新的生图模式
- 支持多主题界面切换，提供 20+ 种视觉风格

## 安装使用

### 环境要求

- Python 3.8+
- ComfyUI 服务端（本地或远程）

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/szcisco/ComfyUI_Batch_Processing_Companion.git
cd ComfyUI_Batch_Processing_Companion
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 运行程序
```bash
python ComfyUl批量图生图工具/ComfyUl批量处理伴侣(ComfyUI_Batch_Processing_Companion).py
```

## 使用说明

1. 确保 ComfyUI 服务端已启动（默认地址：http://127.0.0.1:8188）
2. 在程序中选择或导入 ComfyUI 工作流（JSON + INI 配置文件）
3. 批量导入需要处理的图片
4. 填写或翻译提示词
5. 点击"批量生成"开始处理

## 联系方式

- **作者**: victor (szcisco@gmail.com)
- **QQ群**: [点击加入](https://qm.qq.com/q/eBWAzdjzmE)
- **微信**: lilian_wang1206
- **GitHub**: [szcisco](https://github.com/szcisco)

## 开源协议

本项目采用 [GNU General Public License v3.0](LICENSE) 开源协议。

---

<p align="center">
  <b>如果这个项目对你有帮助，欢迎 Star ⭐ 支持！</b>
</p>
