#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

class OllamaAPI:
    def __init__(self, base_url="http://localhost:11434", timeout=10):
        self.base_url = base_url
        self.timeout = timeout
    
    def generate(self, prompt, model="llama3", system_prompt=None):
        """生成文本响应"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        return result.get("response", "")
    
    def translate_to_english(self, text):
        """将文本翻译成英文"""
        prompt = f"""Translate the following Chinese text to English, preserving the original meaning and context:

{text}"""
        system_prompt = "You are a professional translator. Translate the given text accurately and fluently."
        
        try:
            result = self.generate(prompt, model="llama3", system_prompt=system_prompt)
            # 确保结果不是空字符串
            return result if result.strip() else text
        except requests.RequestException as e:
            # 如果Ollama请求失败，返回原始文本
            return text
    
    def list_models(self):
        """列出可用模型"""
        response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("models", [])
    
    def pull_model(self, model_name):
        """拉取模型"""
        payload = {"name": model_name}
        response = requests.post(
            f"{self.base_url}/api/pull",
            json=payload,
            timeout=300  # 拉取模型可能需要更长时间
        )
        response.raise_for_status()
        return response.json()