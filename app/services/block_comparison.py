"""
分块比对检测服务
方式2：原图与待检测图分块比对，识别被篡改的块
"""
import numpy as np
from PIL import Image as PILImage
from typing import List, Tuple, Optional
import os
import uuid
import base64
from io import BytesIO
from app.utils.config import UPLOAD_DIR


class BlockComparisonResult:
    """分块比对结果"""
    def __init__(self):
        self.blocks: List[dict] = []  # 块信息列表
        self.tampered_blocks: List[dict] = []  # 被篡改的块
        self.tamper_ratio: float = 0.0  # 篡改比例
        self.is_tampered: bool = False


def compare_images_by_blocks(
    original_path: str,
    detected_path: str,
    block_size: int = 64
) -> Tuple[BlockComparisonResult, Optional[np.ndarray]]:
    """
    分块比对两张图片
    
    Args:
        original_path: 原图路径
        detected_path: 待检测图片路径
        block_size: 块大小（默认64x64）
    
    Returns:
        (比对结果, 篡改掩码)
    """
    try:
        # 打开两张图片
        original_img = PILImage.open(original_path)
        detected_img = PILImage.open(detected_path)
        
        # 转换为RGB模式
        if original_img.mode != 'RGB':
            original_img = original_img.convert('RGB')
        if detected_img.mode != 'RGB':
            detected_img = detected_img.convert('RGB')
        
        # 转换为numpy数组
        original_array = np.array(original_img)
        detected_array = np.array(detected_img)
        
        # 检查两张图片尺寸是否相同
        if original_array.shape != detected_array.shape:
            # 尺寸不同，直接判断为篡改
            result = BlockComparisonResult()
            result.is_tampered = True
            result.tamper_ratio = 1.0  # 100%篡改
            result.tampered_blocks.append({
                'reason': '尺寸不匹配',
                'original_size': original_array.shape,
                'detected_size': detected_array.shape
            })
            return result, None
        
        height, width = original_array.shape[:2]
        
        # 创建结果对象
        result = BlockComparisonResult()
        tamper_mask = np.zeros((height, width), dtype=np.uint8)
        
        # 分块比对
        block_index = 0
        for y in range(0, height, block_size):
            for x in range(0, width, block_size):
                # 计算块的边界
                block_width = min(block_size, width - x)
                block_height = min(block_size, height - y)
                
                # 提取块
                original_block = original_array[y:y+block_height, x:x+block_width]
                detected_block = detected_array[y:y+block_height, x:x+block_width]
                
                # 检查是否有任何像素不一致
                has_diff = not np.array_equal(original_block, detected_block)
                
                block_info = {
                    'block_index': block_index,
                    'x': x,
                    'y': y,
                    'width': block_width,
                    'height': block_height,
                    'is_tampered': has_diff
                }
                
                result.blocks.append(block_info)
                
                if has_diff:
                    result.tampered_blocks.append(block_info)
                    # 在掩码中标记被篡改的区域
                    tamper_mask[y:y+block_height, x:x+block_width] = 1
                    

                
                block_index += 1
        
        # 计算篡改比例
        total_blocks = len(result.blocks)
        tampered_count = len(result.tampered_blocks)
        result.tamper_ratio = tampered_count / total_blocks if total_blocks > 0 else 0.0
        result.is_tampered = tampered_count > 0  # 只要有一个块被篡改，就认为图片被篡改
        
        return result, tamper_mask
    except Exception as e:
        raise Exception(f"分块比对失败: {str(e)}")


def visualize_block_comparison(
    image_path: str,
    tamper_mask: np.ndarray,
    output_path: str
):
    """
    可视化分块比对结果
    
    Args:
        image_path: 原始图片路径
        tamper_mask: 篡改掩码
        output_path: 输出路径
    """
    try:
        img = PILImage.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        img_array = np.array(img)
        height, width = img_array.shape[:2]
        
        # 确保掩码尺寸匹配
        if tamper_mask.shape != (height, width):
            mask_img = PILImage.fromarray(tamper_mask * 255)
            mask_img = mask_img.resize((width, height), PILImage.Resampling.NEAREST)
            tamper_mask = np.array(mask_img) / 255
        
        # 创建可视化图像（红色标记篡改区域）
        vis_array = img_array.copy()
        vis_array[tamper_mask == 1, 0] = 255  # R通道
        vis_array[tamper_mask == 1, 1] = 0     # G通道
        vis_array[tamper_mask == 1, 2] = 0     # B通道
        
        vis_img = PILImage.fromarray(vis_array)
        vis_img.save(output_path, quality=95)
    except Exception as e:
        raise Exception(f"可视化失败: {str(e)}")

