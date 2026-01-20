"""
图片上传客户端脚本
用于从命令行上传图片到服务器
"""
import requests
import sys
import os
from pathlib import Path

# 上传服务地址
UPLOAD_URL = "http://localhost:8001/api/upload"


def upload_image(image_path: str, category: str = None):
    """
    上传图片到服务器
    
    Args:
        image_path: 图片文件路径
        category: 图片分类（可选）
    
    Returns:
        上传结果
    """
    if not os.path.exists(image_path):
        print(f"错误: 文件不存在: {image_path}")
        return None
    
    try:
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
            data = {}
            if category:
                data["category"] = category
            
            print(f"正在上传: {image_path}...")
            response = requests.post(UPLOAD_URL, files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 上传成功!")
                print(f"图片ID: {result.get('data', {}).get('id')}")
                print(f"图片URL: {result.get('data', {}).get('url')}")
                return result
            else:
                print(f"❌ 上传失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                return None
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败: 无法连接到服务器 {UPLOAD_URL}")
        print("请确保上传服务已启动: python upload_image.py")
        return None
    except Exception as e:
        print(f"❌ 上传出错: {str(e)}")
        return None


def upload_multiple_images(image_paths: list, category: str = None):
    """
    批量上传图片
    
    Args:
        image_paths: 图片文件路径列表
        category: 图片分类（可选）
    """
    success_count = 0
    fail_count = 0
    
    for image_path in image_paths:
        result = upload_image(image_path, category)
        if result:
            success_count += 1
        else:
            fail_count += 1
        print("-" * 50)
    
    print(f"\n上传完成: 成功 {success_count} 个, 失败 {fail_count} 个")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  上传单张图片: python upload_image_client.py <图片路径> [分类]")
        print("  批量上传: python upload_image_client.py <图片路径1> <图片路径2> ... [分类]")
        print("\n示例:")
        print("  python upload_image_client.py test.jpg")
        print("  python upload_image_client.py test.jpg 风景")
        print("  python upload_image_client.py img1.jpg img2.jpg img3.jpg")
        sys.exit(1)
    
    # 解析参数
    args = sys.argv[1:]
    
    # 检查最后一个参数是否是分类（如果所有参数都是文件路径，则没有分类）
    category = None
    if len(args) > 1:
        # 检查最后一个参数是否是文件路径
        last_arg = args[-1]
        if not os.path.exists(last_arg) and not last_arg.startswith("-"):
            # 可能是分类
            category = last_arg
            image_paths = args[:-1]
        else:
            image_paths = args
    else:
        image_paths = args
    
    # 过滤掉分类参数
    image_paths = [path for path in image_paths if os.path.exists(path) or not path.startswith("-")]
    
    if not image_paths:
        print("错误: 没有找到有效的图片文件")
        sys.exit(1)
    
    # 上传图片
    if len(image_paths) == 1:
        upload_image(image_paths[0], category)
    else:
        upload_multiple_images(image_paths, category)


if __name__ == "__main__":
    main()










