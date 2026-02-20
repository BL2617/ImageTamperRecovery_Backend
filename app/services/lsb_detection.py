"""
LSB水印检测服务
方式1：检测图片中的自定义最低位是否符合自定义规则
"""
import numpy as np
from PIL import Image as PILImage
import hashlib
from typing import Tuple, Optional
import os
import uuid
from app.utils.watermark import detect_tampering, visualize_tampering
from app.utils.config import UPLOAD_DIR


def detect_lsb_watermark(
    image_path: str,
    key: str,
    save_visualization: bool = True
) -> Tuple[bool, float, Optional[str], Optional[np.ndarray]]:
    """
    检测LSB水印
    
    Args:
        image_path: 待检测图片路径
        key: 用户密钥
        save_visualization: 是否保存可视化图片
    
    Returns:
        (是否被篡改, 篡改比例, 可视化图片路径, 篡改掩码)
    """
    try:
        # 使用现有的水印检测函数
        is_tampered, tamper_mask, tamper_ratio = detect_tampering(image_path, key)
        
        visualization_path = None
        if save_visualization:
            # 生成可视化图片
            vis_filename = f"lsb_vis_{uuid.uuid4()}.jpg"
            visualization_path = os.path.join(UPLOAD_DIR, vis_filename)
            visualize_tampering(image_path, tamper_mask, visualization_path)
            # 只返回文件名，不返回完整路径
            visualization_path = vis_filename
        
        return is_tampered, tamper_ratio, visualization_path, tamper_mask
    except Exception as e:
        raise Exception(f"LSB检测失败: {str(e)}")

