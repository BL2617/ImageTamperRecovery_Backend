"""
图像加密模块
使用AES对称加密算法对图像进行加密存储
支持本地和云端存储的加密
"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import hashlib
import base64
import os
from typing import Optional


def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> bytes:
    """
    从用户密码派生加密密钥（使用PBKDF2）
    
    Args:
        password: 用户密码
        salt: 盐值（可选，如果不提供则使用固定盐值）
    
    Returns:
        加密密钥（32字节）
    """
    if salt is None:
        # 使用固定盐值（生产环境应使用随机盐值）
        salt = b'image_tamper_recovery_salt_2024'
    
    # 使用PBKDF2派生密钥
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
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









