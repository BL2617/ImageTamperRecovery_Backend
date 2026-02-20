"""
模型检测服务（占位）
方式3：使用小模型检测可能被修改的区域
"""
from typing import Tuple, Optional
import numpy as np
from PIL import Image as PILImage
import os
import uuid
from app.utils.config import UPLOAD_DIR


def detect_with_model(
    image_path: str,
    confidence_threshold: float = 0.5,
    save_visualization: bool = True
) -> Tuple[bool, float, list, Optional[np.ndarray]]:
    """
    使用模型检测图片是否被篡改（占位实现）
    
    Args:
        image_path: 待检测图片路径
        confidence_threshold: 置信度阈值（默认0.5）
        save_visualization: 是否保存可视化图片
    
    Returns:
        (是否被篡改, 篡改比例, 篡改区域列表, 篡改掩码)
    
    注意：这是一个占位实现，实际需要集成深度学习模型
    当前实现：返回空结果，表示未检测到篡改
    """
    try:
        # 打开图片获取尺寸
        img = PILImage.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        width, height = img.size
        
        # TODO: 集成实际的深度学习模型
        # 当前占位实现：返回未检测到篡改
        is_tampered = False
        tamper_ratio = 0.0
        tampered_regions = []
        tamper_mask = None
        
        # 如果需要可视化，生成一个空的可视化图片（与原图相同）
        if save_visualization:
            vis_filename = f"model_vis_{uuid.uuid4()}.jpg"
            vis_path = os.path.join(UPLOAD_DIR, vis_filename)
            img.save(vis_path, quality=95)
            # 注意：这里不返回可视化路径，因为detection_service会处理
        
        return is_tampered, tamper_ratio, tampered_regions, tamper_mask
    except Exception as e:
        raise Exception(f"模型检测失败: {str(e)}")

