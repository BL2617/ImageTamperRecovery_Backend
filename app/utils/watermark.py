"""
水印嵌入与检测模块
基于LSB（最低有效位）的图像水印算法
"""
import numpy as np
from PIL import Image
import hashlib
from typing import Tuple


def generate_watermark_sequence(image_shape: Tuple[int, int], key: str) -> np.ndarray:
    """
    根据密钥生成伪随机水印序列
    
    Args:
        image_shape: 图像尺寸 (height, width)
        key: 用户密钥（可以为空字符串）
    
    Returns:
        水印序列（二维数组，0或1）
    """
    height, width = image_shape
    
    # 确保key不为None
    if key is None:
        key = ""
    
    # 使用密钥生成伪随机序列
    key_hash = hashlib.sha256(key.encode()).digest()
    # 限制seed在0到2^32-1之间（numpy.random.seed的要求）
    # 使用前4个字节（32位）来生成seed
    seed = int.from_bytes(key_hash[:4], 'big') % (2**32)
    
    # 创建新的随机数生成器，避免影响全局状态
    rng = np.random.RandomState(seed)
    
    # 生成随机水印位（0或1）
    watermark = rng.randint(0, 2, size=(height, width), dtype=np.uint8)
    
    return watermark


def embed_watermark(original_path: str, output_path: str, key: str) -> bool:
    """
    在图像中嵌入水印（LSB方法）
    
    Args:
        original_path: 原始图像路径
        output_path: 输出图像路径
        key: 用户密钥
    
    Returns:
        是否成功
    """
    try:
        # 打开图像
        img = Image.open(original_path)
        
        # 转换为RGB模式
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 转换为numpy数组
        img_array = np.array(img)
        height, width, channels = img_array.shape
        
        # 生成水印序列
        watermark = generate_watermark_sequence((height, width), key)
        
        # 在R通道的LSB中嵌入水印
        # 将最低位清零，然后嵌入水印位
        img_array[:, :, 0] = (img_array[:, :, 0] & 0xFE) | watermark
        
        # 转换回PIL Image并保存
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
        (是否被篡改, 篡改掩码, 篡改比例)
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
        original_watermark = generate_watermark_sequence((height, width), key)
        
        # 从R通道的LSB中提取水印
        extracted_watermark = img_array[:, :, 0] & 0x01
        
        # 比较原始水印和提取的水印
        tamper_mask = (original_watermark != extracted_watermark).astype(np.uint8)
        
        # 计算篡改比例
        tamper_ratio = np.sum(tamper_mask) / (height * width)
        
        # 判断是否被篡改（阈值：0.01，即1%）
        is_tampered = tamper_ratio > 0.01
        
        return is_tampered, tamper_mask, tamper_ratio
    except Exception as e:
        print(f"检测失败: {e}")
        return False, np.zeros((1, 1), dtype=np.uint8), 0.0


def visualize_tampering(image_path: str, tamper_mask: np.ndarray, output_path: str):
    """
    可视化篡改位置
    
    Args:
        image_path: 原始图像路径
        tamper_mask: 篡改掩码
        output_path: 输出图像路径
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
        
        # 确保掩码是二维的且尺寸匹配
        if len(tamper_mask.shape) != 2:
            # 如果掩码是1维的，尝试重塑
            if len(tamper_mask.shape) == 1:
                # 尝试重塑为(height, width)
                if tamper_mask.size == height * width:
                    tamper_mask = tamper_mask.reshape((height, width))
                else:
                    raise ValueError(f"掩码尺寸不匹配: 掩码大小={tamper_mask.size}, 图片大小={height*width}")
            else:
                raise ValueError(f"掩码维度不正确: {tamper_mask.shape}, 期望2维")
        
        # 确保掩码尺寸与图片匹配
        if tamper_mask.shape != (height, width):
            # 如果尺寸不匹配，尝试调整
            from PIL import Image as PILImage
            mask_pil = PILImage.fromarray((tamper_mask * 255).astype(np.uint8))
            mask_resized = mask_pil.resize((width, height), PILImage.NEAREST)
            tamper_mask = np.array(mask_resized) / 255.0
            tamper_mask = (tamper_mask > 0.5).astype(np.uint8)
        
        # 创建可视化图像（红色标记篡改区域）
        vis_array = img_array.copy()
        
        # 将篡改区域标记为红色（使用布尔索引）
        tamper_indices = tamper_mask == 1
        vis_array[tamper_indices, 0] = 255  # R通道
        vis_array[tamper_indices, 1] = 0     # G通道
        vis_array[tamper_indices, 2] = 0     # B通道
        
        # 转换回PIL Image并保存
        vis_img = Image.fromarray(vis_array)
        vis_img.save(output_path, quality=95)
    except Exception as e:
        import traceback
        error_msg = f"可视化失败: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        raise Exception(error_msg)
