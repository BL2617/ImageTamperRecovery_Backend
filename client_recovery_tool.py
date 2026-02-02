"""
客户端本地恢复工具示例

此工具演示如何在客户端本地进行图片恢复操作。
备份文件存储在客户端本地，使用密钥解密后恢复原图。

使用场景：
1. 检测到图片被篡改后
2. 使用本地备份文件恢复原始图片
"""

from encryption import decrypt_image
import os
import sys


def recover_image_local(encrypted_backup_path: str, output_path: str, key: str) -> bool:
    """
    在客户端本地恢复图片
    
    Args:
        encrypted_backup_path: 加密的备份文件路径（客户端本地）
        output_path: 恢复后的图片保存路径
        key: 用户密钥
    
    Returns:
        是否成功
    """
    if not os.path.exists(encrypted_backup_path):
        print(f"错误：备份文件不存在: {encrypted_backup_path}")
        return False
    
    try:
        success = decrypt_image(encrypted_backup_path, output_path, key)
        if success:
            print(f"恢复成功！原图已保存到: {output_path}")
            return True
        else:
            print("恢复失败：解密过程出错")
            return False
    except Exception as e:
        print(f"恢复失败: {e}")
        return False


def main():
    """命令行工具入口"""
    if len(sys.argv) != 4:
        print("用法: python client_recovery_tool.py <加密备份文件路径> <输出路径> <密钥>")
        print("\n示例:")
        print("  python client_recovery_tool.py backup/photo_encrypted.backup recovered_photo.jpg my_secret_key")
        sys.exit(1)
    
    encrypted_path = sys.argv[1]
    output_path = sys.argv[2]
    key = sys.argv[3]
    
    recover_image_local(encrypted_path, output_path, key)


if __name__ == "__main__":
    main()

