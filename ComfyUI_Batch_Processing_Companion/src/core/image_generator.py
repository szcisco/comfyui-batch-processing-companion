#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
import requests
from PIL import Image
from src.api.comfyui_api import ComfyUIAPI
from src.api.ollama_api import OllamaAPI
from src.api.tencent_translate import TencentTranslateAPI
from src.utils.logger import Logger

class ImageGenerator:
    def __init__(self, config_manager, logger=None):
        self.config_manager = config_manager
        self.logger = logger or Logger()
        self.comfyui_api = None
        self.ollama_api = None
        self.tencent_api = None
        
        # 初始化API客户端
        self._init_apis()
    
    def _init_apis(self):
        """初始化API客户端"""
        # 初始化ComfyUI API
        comfyui_url = self.config_manager.get("ComfyUI", "URL", "http://127.0.0.1:8188")
        comfyui_timeout = int(self.config_manager.get("ComfyUI", "Timeout", "2700"))
        self.comfyui_api = ComfyUIAPI(comfyui_url, comfyui_timeout)
        
        # 初始化Ollama API
        if self.config_manager.get("Ollama", "Enable", "false").lower() == "true":
            ollama_url = self.config_manager.get("Ollama", "URL", "http://localhost:11434")
            ollama_timeout = int(self.config_manager.get("Ollama", "Timeout", "10"))
            self.ollama_api = OllamaAPI(ollama_url, ollama_timeout)
        
        # 初始化腾讯翻译API
        secret_id = self.config_manager.get("TencentTranslate", "secret_id", "")
        secret_key = self.config_manager.get("TencentTranslate", "secret_key", "")
        if secret_id and secret_key:
            region = self.config_manager.get("TencentTranslate", "region", "ap-guangzhou")
            self.tencent_api = TencentTranslateAPI(secret_id, secret_key, region)
    
    def generate_image_single(self, image_number, image_path, pos_prompt, neg_prompt, 
                            fps, duration, output_dir, ui_callback=None):
        """生成单个图片"""
        try:
            # 更新UI状态
            if ui_callback:
                ui_callback("status", f"处理图片 {image_number}: {os.path.basename(image_path)}")
                ui_callback("progress", 0)
            
            # 参数验证
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
            # 验证图片格式
            try:
                with Image.open(image_path) as img:
                    img.verify()
            except Exception as e:
                raise ValueError(f"图片格式无效: {e}")
            
            # 获取英文提示词
            english_pos_prompt = self._get_english_prompt(pos_prompt)
            english_neg_prompt = self._get_english_prompt(neg_prompt)
            
            # 构建工作流数据
            workflow_data = self._build_workflow_data(
                image_path, english_pos_prompt, english_neg_prompt, fps, duration
            )
            
            # 提交工作流
            if ui_callback:
                ui_callback("status", f"提交工作流到ComfyUI...")
                ui_callback("progress", 20)
            
            prompt_id = self.comfyui_api.queue_workflow(workflow_data)
            
            # 等待生成完成
            if ui_callback:
                ui_callback("status", f"等待图片生成完成...")
                ui_callback("progress", 40)
            
            image_path = self._wait_for_image_generation(prompt_id, output_dir, image_number, ui_callback)
            
            if ui_callback:
                ui_callback("status", f"图片 {image_number} 生成完成！")
                ui_callback("progress", 100)
            
            return image_path
            
        except Exception as e:
            self.logger.error(f"生成图片 {image_number} 失败: {e}")
            if ui_callback:
                ui_callback("status", f"生成失败: {e}")
            raise
    
    def _get_english_prompt(self, prompt):
        """获取英文提示词"""
        if not prompt:
            return ""
        
        # 优先使用腾讯翻译
        if self.tencent_api:
            try:
                return self.tencent_api.translate_text(prompt)
            except Exception as e:
                self.logger.warning(f"腾讯翻译失败，尝试使用Ollama: {e}")
        
        # 其次使用Ollama
        if self.ollama_api:
            try:
                return self.ollama_api.translate_to_english(prompt)
            except Exception as e:
                self.logger.warning(f"Ollama翻译失败，使用原提示词: {e}")
        
        # 如果都失败，使用原提示词
        return prompt
    
    def _build_workflow_data(self, image_path, pos_prompt, neg_prompt, fps, duration):
        """构建工作流数据"""
        # 这里需要根据实际的ComfyUI工作流JSON结构进行构建
        # 以下是示例结构，需要根据实际情况调整
        workflow = {
            "3": {
                "inputs": {
                    "seed": self.config_manager.get("ComfyUI", "Seed", "-1"),
                    "steps": int(self.config_manager.get("ComfyUI", "Steps", "20")),
                    "cfg": float(self.config_manager.get("ComfyUI", "CFGScale", "7.0")),
                    "sampler_name": self.config_manager.get("ComfyUI", "Sampler", "euler"),
                    "scheduler": self.config_manager.get("ComfyUI", "Scheduler", "normal"),
                    "denoise": 1.0,
                    "model": ["4", 0]
                },
                "class_type": "KSampler"
            },
            "4": {
                "inputs": {
                    "ckpt_name": self.config_manager.get("ComfyUI", "Model", "v1-5-pruned-emaonly.safetensors")
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "6": {
                "inputs": {
                    "text": pos_prompt,
                    "clip": ["5", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "text": neg_prompt,
                    "clip": ["5", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["5", 2]
                },
                "class_type": "VAEDecode"
            },
            "9": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage"
            }
        }
        
        return {"prompt": json.dumps(workflow), "client_id": "batch-image-generator"}
    
    def _wait_for_image_generation(self, prompt_id, output_dir, image_number, ui_callback=None):
        """等待图片生成完成"""
        max_wait_time = int(self.config_manager.get("ComfyUI", "Timeout", "2700"))
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # 检查历史记录
                history = self.comfyui_api.get_history(prompt_id)
                
                if prompt_id in history and "outputs" in history[prompt_id]:
                    # 检查是否有图片输出
                    outputs = history[prompt_id]["outputs"]
                    for node_id, node_output in outputs.items():
                        if "files" in node_output:
                            for file in node_output["files"]:
                                if file.lower().endswith((".png", ".jpg", ".jpeg")):
                                    # 下载图片
                                    image_path = os.path.join(output_dir, f"image_{image_number}.png")
                                    # 这里需要根据ComfyUI的实际输出方式调整下载逻辑
                                    # 暂时简单返回路径
                                    return image_path
                
                # 更新进度
                if ui_callback:
                    elapsed = time.time() - start_time
                    progress = 40 + int((elapsed / max_wait_time) * 50)
                    progress = min(progress, 90)
                    ui_callback("progress", progress)
                
                time.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                self.logger.warning(f"检查生成状态失败: {e}")
                time.sleep(5)
        
        raise TimeoutError("图片生成超时")
    
    def batch_generate_images(self, image_files, pos_prompts, neg_prompts, fps, duration, 
                             output_dir, ui_callback=None):
        """批量生成图片"""
        results = []
        
        for i, (image_path, pos_prompt, neg_prompt) in enumerate(zip(image_files, pos_prompts, neg_prompts)):
            image_number = i + 1
            try:
                image_path = self.generate_image_single(
                    image_number, image_path, pos_prompt, neg_prompt, fps, duration, output_dir, ui_callback
                )
                results.append({
                    "image_number": image_number,
                    "image_path": image_path,
                    "output_path": image_path,
                    "status": "success"
                })
            except Exception as e:
                results.append({
                    "image_number": image_number,
                    "image_path": image_path,
                    "error": str(e),
                    "status": "failed"
                })
        
        return results