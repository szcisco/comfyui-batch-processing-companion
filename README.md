# ComfyUI Batch Processing Companion

<p align="center">
  <img src="https://img.shields.io/badge/version-v1.0-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/python-3.8+-green.svg" alt="Python">
  <img src="https://img.shields.io/badge/license-GPLv3-orange.svg" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg" alt="Platform">
</p>

<p align="center">
  <b>A desktop batch image generation tool designed for ComfyUI users</b>
</p>

<p align="center">
  <a href="#introduction">Introduction</a> •
  <a href="#core-features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#contact">Contact</a>
</p>

---

## Introduction

ComfyUI Batch Processing Companion is a desktop batch image generation tool designed specifically for ComfyUI users. It simplifies the ComfyUI API workflow through a visual interface, allowing users to perform batch image-to-image, text-to-image, and other AI drawing tasks without writing any code.

## 🎬 Demo Video
<iframe src="https://player.bilibili.com/player.html?bvid=BV1oavHBCEBp&page=1" width="800" height="450" scrolling="no" border="0" frameborder="no" framespacing="0" allowfullscreen="true"></iframe>

## Core Features

### 🖼️ Batch Image Processing
Import multiple images at once and generate new images in batch with prompts. Ideal for scenarios requiring large-scale processing of similar-style images, such as e-commerce product image optimization, short video material batch production, and comic storyboard batch rendering.

### ⚙️ Flexible Workflow Management
Manage ComfyUI workflows using a combination of JSON + INI configuration files. Users can export API-format JSON workflows from ComfyUI and use INI configuration files to define parameter mappings, enabling quick switching between different models and generation modes.

### 🔗 Smart Parameter Binding
Through a visual variable configuration panel, users can bind key workflow parameters (such as image loading nodes, prompt nodes, sampling steps, image dimensions, etc.) to interface controls. The program automatically identifies the workflow type (image-to-image/text-to-image) and displays the corresponding operation interface.

### 🌐 Multi-language Translation Integration
Built-in support for Tencent Translation API and Ollama local LLM translation, enabling one-click translation of Chinese prompts to English. For users who need to process large amounts of Chinese descriptions, batch translation of all prompts significantly improves work efficiency.

### 🌍 Bilingual Interface (Chinese/English)
Full support for Simplified Chinese and English interface languages, switchable at any time in settings. Also supports workflow configuration files in both Chinese and English formats.

## Use Cases

- 🎨 Batch image generation for AI art studios
- 📱 Batch material generation for short video/content creators
- 🛒 AI stylization of e-commerce product images
- 🎮 Batch iteration of concept art for games/animation
- 🔧 Any scenario requiring batch image processing with ComfyUI

## Technical Highlights

- Developed with Python + Tkinter, cross-platform support
- Communicates with ComfyUI server via HTTP API, supporting both local and remote deployment
- Modular workflow configuration system, easy to extend with new generation modes
- Supports multiple theme switching with 20+ visual styles

## Installation

### Requirements

- Python 3.8+
- ComfyUI server (local or remote)

### Installation Steps

1. Clone the repository
```bash
git clone https://github.com/szcisco/ComfyUI_Batch_Processing_Companion.git
cd ComfyUI_Batch_Processing_Companion
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Run the program
```bash
python ComfyUI_Batch_Processing_Companion/ComfyUl批量处理伴侣(ComfyUI_Batch_Processing_Companion).py
```

## Usage

1. Ensure the ComfyUI server is running (default address: http://127.0.0.1:8188)
2. Select or import a ComfyUI workflow (JSON + INI configuration files) in the program
3. Batch import the images to be processed
4. Enter or translate prompts
5. Click "Batch Generate" to start processing

## Contact

- **Author**: victor (szcisco@gmail.com)
- **QQ Group**: [Join here](https://qm.qq.com/q/eBWAzdjzmE)
- **WeChat**: lilian_wang1206
- **GitHub**: [szcisco](https://github.com/szcisco)

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).

---

<p align="center">
  <b>If this project helps you, please give it a Star ⭐!</b>
</p>
