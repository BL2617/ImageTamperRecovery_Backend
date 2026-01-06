"""
图像加密模块
用于加密备份原图
"""
from cryptography.fernet import Fernet
import hashlib
import base64
from typing import Optional
import os


def derive_key_from_password(password: str) -> bytes:
    """
    从用户密码派生加密密钥
    
    Args:
        password: 用户密码
    
    Returns:
        加密密钥
    """
    # 使用SHA256哈希密码
    password_hash = hashlib.sha256(password.encode()).digest()
    # 转换为Fernet格式的密钥（base64编码）
    key = base64.urlsafe_b64encode(password_hash[:32])
    return key


def encrypt_image(image_path: str, output_path: str, password: str) -> bool:
    """
    加密图像文件
    
    Args:
        image_path: 原始图像路径
        output_path: 加密后图像路径
        password: 用户密码
    
    Returns:
        是否成功
    """
    try:
        # 派生密钥
        key = derive_key_from_password(password)
        fernet = Fernet(key)
        
        # 读取图像文件
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # 加密
        encrypted_data = fernet.encrypt(image_data)
        
        # 保存加密文件
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
        
        return True
    except Exception as e:
        print(f"加密失败: {e}")
        return False


def decrypt_image(encrypted_path: str, output_path: str, password: str) -> bool:
    """
    解密图像文件
    
    Args:
        encrypted_path: 加密图像路径
        output_path: 解密后图像路径
        password: 用户密码
    
    Returns:
        是否成功
    """
    try:
        # 派生密钥
        key = derive_key_from_password(password)
        fernet = Fernet(key)
        
        # 读取加密文件
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
        
        # 解密
        decrypted_data = fernet.decrypt(encrypted_data)
        
        # 保存解密文件
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        return True
    except Exception as e:
        print(f"解密失败: {e}")
        return False



