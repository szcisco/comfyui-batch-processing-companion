#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import hmac
import base64
import time
import random
import requests

class TencentTranslateAPI:
    def __init__(self, secret_id, secret_key, region="ap-beijing", timeout=10):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.timeout = timeout
        self.endpoint = "tmt.tencentcloudapi.com"
    
    def _generate_signature(self, params):
        """生成签名"""
        # 对参数进行排序
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        # 构建请求字符串
        request_str = "GET"
        request_str += self.endpoint
        request_str += "/?"
        request_str += "&" .join([f"{k}={v}" for k, v in sorted_params])
        # 生成签名
        h = hmac.new(self.secret_key.encode("utf-8"), request_str.encode("utf-8"), hashlib.sha1)
        signature = base64.b64encode(h.digest()).decode("utf-8")
        return signature
    
    def translate_text(self, text, source="zh", target="en"):
        """翻译文本"""
        # 生成请求参数
        params = {
            "Action": "TextTranslate",
            "Version": "2018-03-21",
            "Region": self.region,
            "Source": source,
            "Target": target,
            "ProjectId": 0,
            "SourceText": text,
            "SecretId": self.secret_id,
            "Timestamp": str(int(time.time())),
            "Nonce": str(random.randint(1, 10000))
        }
        
        # 生成签名
        params["Signature"] = self._generate_signature(params)
        
        # 发送请求
        url = f"https://{self.endpoint}/"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        if "Response" in result:
            if "TargetText" in result["Response"]:
                return result["Response"]["TargetText"]
            elif "Error" in result["Response"]:
                raise Exception(f"翻译失败: {result['Response']['Error']['Message']}")
        
        raise Exception("翻译响应格式异常")
    
    def batch_translate_text(self, texts, source="zh", target="en"):
        """批量翻译文本"""
        results = []
        for text in texts:
            try:
                translated = self.translate_text(text, source, target)
                results.append(translated)
            except Exception:
                results.append("")
        return results