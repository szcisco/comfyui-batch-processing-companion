#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接输入SecretKey的腾讯翻译API测试脚本
无需设置环境变量，直接在脚本中输入SecretKey即可使用
"""

import json
import time
import hmac
import hashlib
import requests

# =========================================================
# 请直接在这里输入您的SecretKey
# 注意：这个密钥是敏感信息，请勿泄露给他人
# =========================================================
SECRET_KEY = "xxxxx"  # 用户提供的SecretKey
# =========================================================

# 其他配置信息（用户提供的完整信息）
APPID = "xxxxx"  # 用户提供的APPID
SECRET_ID = "xxxxx"  # 用户提供的SecretId
API_HOST = "tmt.tencentcloudapi.com"
API_ACTION = "TextTranslate"
API_VERSION = "2018-03-21"
API_REGION = "ap-guangzhou"


def main():
    """主函数"""
    print("=" * 60)
    print("腾讯翻译API测试脚本")
    print("测试内容：hello -> 你好")
    print("=" * 60)
    
    # 检查SecretKey是否已填写
    if not SECRET_KEY:
        print("❌ 错误：请先在脚本中填写SecretKey")
        print("\n📋 填写指南：")
        print("   1. 打开此文件：direct_test.py")
        print("   2. 在第15行找到：SECRET_KEY = \"\"")
        print("   3. 在引号中输入您的SecretKey")
        print("   4. 保存文件后重新运行")
        print("   ")
        print("🔍 如何获取SecretKey？")
        print("   1. 登录腾讯云控制台：https://console.cloud.tencent.com/")
        print("   2. 进入访问密钥页面：https://console.cloud.tencent.com/cam/capi")
        print("   3. 找到SecretId为xxxxx的密钥对")
        print("   4. 查看或创建对应的SecretKey")
        print("   5. 将SecretKey复制到第15行的引号中")
        return
    
    # 构建请求参数
    params = {
        "SourceText": "hello",
        "Source": "en",
        "Target": "zh",
        "ProjectId": 0
    }
    
    print(f"\n📋 配置信息：")
    print(f"   APPID: {APPID}")
    print(f"   SecretId: {SECRET_ID[:10]}...{SECRET_ID[-10:]}")
    print(f"   SecretKey: {'已填写' if SECRET_KEY else '未填写'}")
    print(f"   ")
    print(f"📝 测试内容：")
    print(f"   输入：hello")
    print(f"   预期输出：你好")
    
    # 生成签名
    def sign():
        """生成TC3-HMAC-SHA256签名"""
        http_method = "POST"
        canonical_uri = "/"
        canonical_query = ""
        
        payload = json.dumps(params)
        hashed_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        
        canonical_headers = f"content-type:application/json\nhost:{API_HOST}\n"
        signed_headers = "content-type;host"
        canonical_request = f"{http_method}\n{canonical_uri}\n{canonical_query}\n{canonical_headers}\n{signed_headers}\n{hashed_payload}"
        
        timestamp = int(time.time())
        date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
        credential_scope = f"{date}/tmt/tc3_request"
        hashed_canonical = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"TC3-HMAC-SHA256\n{timestamp}\n{credential_scope}\n{hashed_canonical}"
        
        def hmac_sha256(key, msg):
            return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
        
        secret_date = hmac_sha256(f"TC3{SECRET_KEY}".encode("utf-8"), date)
        secret_service = hmac_sha256(secret_date, "tmt")
        secret_signing = hmac_sha256(secret_service, "tc3_request")
        signature = hmac_sha256(secret_signing, string_to_sign)
        signature_hex = signature.hex()
        
        auth_header = f"TC3-HMAC-SHA256 Credential={SECRET_ID}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature_hex}"
        
        return auth_header, timestamp
    
    # 发送请求
    try:
        auth_header, timestamp = sign()
        
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "Host": API_HOST,
            "X-TC-Action": API_ACTION,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": API_VERSION,
            "X-TC-Region": API_REGION
        }
        
        print("\n📤 发送请求...")
        response = requests.post(
            url=f"https://{API_HOST}",
            headers=headers,
            data=json.dumps(params),
            timeout=10
        )
        
        print(f"\n📥 响应结果：")
        print(f"   状态码：{response.status_code}")
        print(f"   内容：{response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if "Response" in result:
                resp_data = result["Response"]
                if "Error" in resp_data:
                    print(f"\n❌ API调用失败：")
                    print(f"   错误码：{resp_data['Error']['Code']}")
                    print(f"   错误信息：{resp_data['Error']['Message']}")
                    print("   ")
                    print("💡 解决方案：")
                    print("   1. 检查SecretKey是否正确")
                    print("   2. 检查腾讯云账户是否开通了翻译服务")
                    print("   3. 检查腾讯云账户是否有可用余额")
                    print("   4. 查看腾讯云控制台的API调用日志")
                else:
                    target_text = resp_data.get("TargetText", "")
                    print(f"\n🎉 翻译结果：")
                    print(f"   输入：hello")
                    print(f"   输出：{target_text}")
                    print(f"   ")
                    
                    if target_text == "你好":
                        print("✅ 测试通过")
                        print("   翻译正常：hello -> 你好")
                    else:
                        print(f"⚠️  测试结果异常")
                        print(f"   预期输出：你好")
                        print(f"   实际输出：{target_text}")
            else:
                print("\n❌ 响应格式错误")
        else:
            print(f"\n❌ HTTP请求失败：状态码 {response.status_code}")
            print("   ")
            print("💡 解决方案：")
            print("   1. 检查网络连接是否正常")
            print("   2. 检查防火墙设置")
            print("   3. 稍后重试")
    
    except Exception as e:
        print(f"\n❌ 程序异常：{str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试结束")
    print("=" * 60)


if __name__ == "__main__":
    main()
