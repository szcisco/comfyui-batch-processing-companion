#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import os
import time

class ComfyUIAPI:
    def __init__(self, base_url="http://127.0.0.1:8188", timeout=2700, retry_count=3):
        self.base_url = base_url
        self.timeout = timeout
        self.retry_count = retry_count
    
    def _make_request(self, endpoint, method="GET", data=None, files=None):
        """发送请求并处理重试逻辑"""
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(self.retry_count):
            try:
                if method == "GET":
                    response = requests.get(url, timeout=self.timeout)
                elif method == "POST":
                    if files:
                        response = requests.post(url, data=data, files=files, timeout=self.timeout)
                    else:
                        response = requests.post(url, json=data, timeout=self.timeout)
                else:
                    raise ValueError(f"不支持的请求方法: {method}")
                
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                if attempt == self.retry_count - 1:
                    raise
                time.sleep(2 ** attempt)  # 指数退避
    
    def get_status(self):
        """获取ComfyUI API状态"""
        return self._make_request("")
    
    def get_workflows(self):
        """获取可用的工作流"""
        return self._make_request("workflows")
    
    def queue_workflow(self, workflow_data):
        """提交工作流到队列"""
        return self._make_request("prompt", method="POST", data=workflow_data)
    
    def get_history(self, prompt_id):
        """获取历史记录"""
        return self._make_request(f"history/{prompt_id}")
    
    def get_images(self, filename, subfolder="", folder_type="output"):
        """获取生成的图片"""
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }
        url = f"{self.base_url}/view"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.content
    
    def upload_image(self, image_path, filename=None):
        """上传图片"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        if not filename:
            filename = os.path.basename(image_path)
        
        with open(image_path, "rb") as f:
            files = {"image": (filename, f, "image/png")}
            response = requests.post(f"{self.base_url}/upload/image", files=files, timeout=self.timeout)
            response.raise_for_status()
            return response.json()