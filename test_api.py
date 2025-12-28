"""
API测试脚本
用于测试后端API功能
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_get_image_list():
    """测试获取图片列表"""
    print("=" * 50)
    print("测试：获取图片列表")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/api/images", params={
        "page": 1,
        "pageSize": 20
    })
    
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()


def test_get_image_by_id(image_id: str):
    """测试获取单张图片信息"""
    print("=" * 50)
    print(f"测试：获取图片信息 (ID: {image_id})")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/api/images/{image_id}")
    
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()


def test_download_image(image_id: str):
    """测试下载图片"""
    print("=" * 50)
    print(f"测试：下载图片 (ID: {image_id})")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/api/images/{image_id}/download")
    
    print(f"状态码: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"文件大小: {len(response.content)} 字节")
    
    # 保存图片到本地
    if response.status_code == 200:
        filename = f"downloaded_{image_id}.jpg"
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"图片已保存到: {filename}")
    print()


def test_upload_image(file_path: str, category: str = None):
    """测试上传图片"""
    print("=" * 50)
    print(f"测试：上传图片 ({file_path})")
    print("=" * 50)
    
    upload_url = "http://localhost:8001/api/upload"  # 上传服务端口
    
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {"category": category} if category else {}
        response = requests.post(upload_url, files=files, data=data)
    
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()
    
    if response.status_code == 200:
        return response.json().get("data", {}).get("id")
    return None


if __name__ == "__main__":
    print("API 测试脚本")
    print("=" * 50)
    print()
    
    # 测试获取图片列表
    try:
        test_get_image_list()
    except Exception as e:
        print(f"错误: {e}")
        print("请确保服务器已启动 (python main.py)")
        print()
    
    # 如果有图片ID，可以测试其他接口
    # image_id = "your-image-id"
    # test_get_image_by_id(image_id)
    # test_download_image(image_id)
    
    # 测试上传（需要先启动上传服务）
    # image_id = test_upload_image("test_image.jpg", "测试")
    # if image_id:
    #     test_get_image_by_id(image_id)
    #     test_download_image(image_id)

