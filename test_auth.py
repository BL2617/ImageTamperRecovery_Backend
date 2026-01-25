"""
测试认证API的脚本
用于快速验证登录/注册功能
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_register():
    """测试用户注册"""
    print("\n=== 测试用户注册 ===")
    url = f"{BASE_URL}/api/auth/register"
    data = {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "Test123456",
        "device_id": "test_device_001"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.json()
    except Exception as e:
        print(f"错误: {e}")
        return None

def test_login():
    """测试用户登录"""
    print("\n=== 测试用户登录 ===")
    url = f"{BASE_URL}/api/auth/login"
    data = {
        "username": "testuser",
        "password": "Test123456",
        "device_id": "test_device_001"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # 返回 token 用于后续测试
        if result.get("code") == 200:
            return result.get("accessToken")
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None

def test_get_current_user(token):
    """测试获取当前用户信息"""
    print("\n=== 测试获取当前用户信息 ===")
    url = f"{BASE_URL}/api/auth/me"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"错误: {e}")

def test_image_list(token):
    """测试获取图片列表（需要认证）"""
    print("\n=== 测试获取图片列表 ===")
    url = f"{BASE_URL}/api/images"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {
        "page": 1,
        "pageSize": 20
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("图像篡改检测系统 - 认证API测试")
    print("=" * 50)
    
    # 1. 测试注册
    result = test_register()
    if result and result.get("code") == 200:
        token = result.get("accessToken")
    else:
        # 如果注册失败（可能是用户已存在），尝试登录
        token = test_login()
    
    if token:
        # 2. 测试获取当前用户信息
        test_get_current_user(token)
        
        # 3. 测试获取图片列表
        test_image_list(token)
        
        print(f"\n=== 测试完成 ===")
        print(f"Token: {token}")
        print(f"\n你可以在 Android 应用中使用以下测试账号：")
        print(f"用户名: testuser")
        print(f"密码: Test123456")
    else:
        print("\n认证失败，无法继续测试")



