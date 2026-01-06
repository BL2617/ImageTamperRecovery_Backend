"""
图像水印嵌入和检测模块
使用LSB（最低有效位）嵌入水印，配合密钥进行加密
"""
import numpy as np
from PIL import Image
import hashlib
import os
from typing import Tuple, Optional


def generate_watermark_sequence(image: Image.Image, key: str) -> np.ndarray:
    """
    根据密钥生成伪随机水印序列
    
    Args:
        image: PIL图像对象
        key: 用户密钥
    
    Returns:
        水印序列（0或1的数组）
    """
    # 使用密钥生成哈希值作为随机种子
    key_hash = hashlib.md5(key.encode()).hexdigest()
    seed = int(key_hash[:8], 16)
    
    np.random.seed(seed)
    width, height = image.size
    total_pixels = width * height
    
    # 生成伪随机序列（0或1）
    watermark = np.random.randint(0, 2, size=total_pixels)
    
    return watermark


def embed_watermark(image_path: str, output_path: str, key: str) -> bool:
    """
    在图像中嵌入水印（LSB方法）
    
    Args:
        image_path: 原始图像路径
        output_path: 输出图像路径
        key: 用户密钥
    
    Returns:
        是否成功
    """
    try:
        # 打开图像
        img = Image.open(image_path)
        
        # 转换为RGB模式（确保有3个通道）
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 转换为numpy数组
        img_array = np.array(img)
        height, width, channels = img_array.shape
        
        # 生成水印序列
        watermark = generate_watermark_sequence(img, key)
        
        # 将水印序列重塑为图像形状（只使用第一个通道）
        watermark_2d = watermark.reshape(height, width)
        
        # 在第一个通道的LSB中嵌入水印
        for y in range(height):
            for x in range(width):
                # 获取当前像素的R值
                r_value = img_array[y, x, 0]
                # 清除LSB
                r_value_cleared = r_value & 0xFE
                # 嵌入水印位
                img_array[y, x, 0] = r_value_cleared | watermark_2d[y, x]
        
        # 转换回PIL图像并保存
        watermarked_img = Image.fromarray(img_array)
        watermarked_img.save(output_path, quality=95)
        
        return True
    except Exception as e:
        print(f"嵌入水印失败: {e}")
        return False


def detect_tampering(image_path: str, key: str) -> Tuple[bool, np.ndarray, float]:
    """
    检测图像是否被篡改
    
    Args:
        image_path: 待检测图像路径
        key: 用户密钥
    
    Returns:
        (是否被篡改, 篡改位置掩码, 篡改比例)
    """
    try:
        # 打开图像
        img = Image.open(image_path)
        
        # 转换为RGB模式
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 转换为numpy数组
        img_array = np.array(img)
        height, width, channels = img_array.shape
        
        # 生成原始水印序列
        original_watermark = generate_watermark_sequence(img, key)
        original_watermark_2d = original_watermark.reshape(height, width)
        
        # 提取当前图像中的水印
        extracted_watermark = np.zeros((height, width), dtype=np.uint8)
        for y in range(height):
            for x in range(width):
                # 提取LSB
                extracted_watermark[y, x] = img_array[y, x, 0] & 0x01
        
        # 比较原始水印和提取的水印
        tamper_mask = (original_watermark_2d != extracted_watermark).astype(np.uint8)
        
        # 计算篡改比例
        tamper_ratio = np.sum(tamper_mask) / (height * width)
        
        # 判断是否被篡改（阈值设为1%）
        is_tampered = tamper_ratio > 0.01
        
        return is_tampered, tamper_mask, tamper_ratio
    except Exception as e:
        print(f"检测篡改失败: {e}")
        return False, np.zeros((1, 1), dtype=np.uint8), 0.0


def visualize_tampering(image_path: str, tamper_mask: np.ndarray, output_path: str) -> bool:
    """
    可视化篡改位置
    
    Args:
        image_path: 原始图像路径
        tamper_mask: 篡改位置掩码
        output_path: 输出图像路径
    
    Returns:
        是否成功
    """
    try:
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        img_array = np.array(img)
        height, width = tamper_mask.shape
        
        # 创建可视化图像
        vis_array = img_array.copy()
        
        # 在篡改位置标记为红色
        for y in range(height):
            for x in range(width):
                if tamper_mask[y, x] == 1:
                    vis_array[y, x] = [255, 0, 0]  # 红色标记
        
        vis_img = Image.fromarray(vis_array)
        vis_img.save(output_path)
        
        return True
    except Exception as e:
        print(f"可视化失败: {e}")
        return False



