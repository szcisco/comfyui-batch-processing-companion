import requests
import subprocess
import json

def check_ollama_service():
    """检查Ollama服务是否正在运行"""
    try:
        # 尝试获取Ollama模型列表，这是检查服务是否正常的常用方法
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            print("✅ Ollama API 正常")
            return True
        else:
            print(f"❌ Ollama API 响应异常，状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Ollama 服务未启动或无法连接")
        return False
    except Exception as e:
        print(f"❌ 检查Ollama服务时发生错误: {e}")
        return False

def get_ollama_models():
    """获取可用的Ollama模型列表"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"\n📋 可用模型列表 ({len(models)}个):")
            for model in models:
                print(f"   - {model['name']} (尺寸: {model['size']}B)")
            return models
        else:
            print(f"❌ 获取模型列表失败，状态码: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ 获取模型列表时发生错误: {e}")
        return []

def test_chat_completion():
    """测试Ollama的聊天完成功能"""
    try:
        payload = {
            "model": "llama3.2-vision:latest",
            "prompt": "你好，Ollama！",
            "stream": False
        }
        response = requests.post("http://localhost:11434/api/generate", json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"\n💬 聊天测试成功:")
            print(f"   输入: {payload['prompt']}")
            print(f"   输出: {result['response']}")
            return True
        else:
            print(f"❌ 聊天测试失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 聊天测试时发生错误: {e}")
        return False

def test_image_understanding(image_path):
    """测试Ollama的图片理解功能"""
    try:
        # 注意：Ollama API的图片理解需要特定格式，这里使用正确的multipart/form-data格式
        files = {
            'image': open(image_path, 'rb')
        }
        data = {
            'model': 'llama3.2-vision:latest',
            'prompt': '详细分析这张图片的内容，包括主体、颜色、场景、关键元素',
            'stream': 'false'
        }
        
        response = requests.post("http://localhost:11434/api/generate", files=files, data=data)
        if response.status_code == 200:
            result = response.json()
            print(f"\n🖼️  图片理解测试成功:")
            print(f"   分析结果: {result['response']}")
            return True
        else:
            print(f"❌ 图片理解测试失败，状态码: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
    except FileNotFoundError:
        print(f"❌ 图片文件不存在: {image_path}")
        return False
    except Exception as e:
        print(f"❌ 图片理解测试时发生错误: {e}")
        return False

def main():
    print("🔍 开始测试Ollama API...\n")
    
    # 1. 检查服务状态
    if not check_ollama_service():
        print("\n❌ 测试失败：Ollama服务未正常运行")
        return
    
    # 2. 获取模型列表
    models = get_ollama_models()
    if not models:
        print("\n⚠️  警告：未找到可用模型")
    
    # 3. 测试聊天功能
    test_chat_completion()
    
    # 4. 测试图片理解功能（可选，需要提供图片路径）
    # 请将下面的路径替换为实际的图片路径
    test_image_path = "C:/Users/Administrator/Downloads/5fdff1d27f429b197747f3f7aa331a80.jpg"
    test_image_understanding(test_image_path)
    
    print("\n✅ 所有测试完成！")

if __name__ == "__main__":
    main()
