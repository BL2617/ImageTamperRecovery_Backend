"""
客户端水印嵌入工具示例

此工具演示如何在客户端本地进行水印嵌入和备份操作。
推荐在客户端完成这些操作，提高安全性。

使用流程：
1. 用户选择原始图片
2. 输入密钥
3. 在本地嵌入水印（生成带水印图片）
4. 在本地加密备份原图
5. 上传带水印的图片到服务器
6. 备份文件保留在客户端本地
"""

from watermark import embed_watermark
from encryption import encrypt_image
import os
import sys
import hashlib


def process_image_local(
    original_image_path: str,
    watermarked_output_path: str,
    backup_output_path: str,
    key: str
) -> tuple[bool, str]:
    """
    在客户端本地处理图片：嵌入水印并备份原图
    
    Args:
        original_image_path: 原始图片路径
        watermarked_output_path: 带水印的图片输出路径
        backup_output_path: 加密备份文件输出路径
        key: 用户密钥
    
    Returns:
        (是否成功, 密钥哈希值)
    """
    if not os.path.exists(original_image_path):
        return False, f"错误：图片文件不存在: {original_image_path}"
    
    try:
        # 1. 嵌入水印
        print("正在嵌入水印...")
        if not embed_watermark(original_image_path, watermarked_output_path, key):
            return False, "嵌入水印失败"
        print(f"✓ 水印已嵌入，保存到: {watermarked_output_path}")
        
        # 2. 加密备份原图
        print("正在加密备份原图...")
        if not encrypt_image(original_image_path, backup_output_path, key):
            return False, "加密备份失败"
        print(f"✓ 原图已加密备份，保存到: {backup_output_path}")
        
        # 3. 计算密钥哈希（用于上传到服务器验证）
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        print(f"✓ 密钥哈希: {key_hash}")
        
        return True, key_hash
        
    except Exception as e:
        return False, f"处理失败: {e}"


def main():
    """命令行工具入口"""
    if len(sys.argv) != 5:
        print("用法: python client_watermark_tool.py <原始图片路径> <水印输出路径> <备份输出路径> <密钥>")
        print("\n示例:")
        print("  python client_watermark_tool.py photo.jpg photo_watermarked.jpg photo_backup.encrypted my_secret_key")
        print("\n后续操作：")
        print("  1. 上传 photo_watermarked.jpg 到服务器")
        print("  2. 保存 photo_backup.encrypted 在本地")
        print("  3. 使用密钥哈希验证服务器上的图片")
        sys.exit(1)
    
    original_path = sys.argv[1]
    watermarked_path = sys.argv[2]
    backup_path = sys.argv[3]
    key = sys.argv[4]
    
    success, result = process_image_local(original_path, watermarked_path, backup_path, key)
    
    if success:
        print(f"\n处理完成！")
        print(f"密钥哈希（用于上传）: {result}")
    else:
        print(f"\n处理失败: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()

