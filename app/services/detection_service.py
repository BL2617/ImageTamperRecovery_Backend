"""
统一检测服务入口
"""
from typing import Tuple, Optional
import uuid
import json
from sqlalchemy.orm import Session
from app.models.models import DetectionResult, TamperedBlock
from app.services.lsb_detection import detect_lsb_watermark
from app.services.block_comparison import compare_images_by_blocks, visualize_block_comparison, BlockComparisonResult
from app.services.model_detection import detect_with_model
from app.utils.config import UPLOAD_DIR
import os


def save_detection_result(
    db: Session,
    user_id: str,
    detection_type: str,
    is_tampered: bool,
    tamper_ratio: float,
    original_image_id: Optional[str] = None,
    detected_image_id: Optional[str] = None,
    confidence: Optional[float] = None,
    tampered_regions: Optional[list] = None,
    visualization_path: Optional[str] = None,
    detection_params: Optional[dict] = None
) -> DetectionResult:
    """
    保存检测结果到数据库
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        detection_type: 检测类型（lsb, compare, model）
        is_tampered: 是否被篡改
        tamper_ratio: 篡改比例
        original_image_id: 原图ID
        detected_image_id: 待检测图片ID
        confidence: 置信度
        tampered_regions: 篡改区域列表
        visualization_path: 可视化图片路径
        detection_params: 检测参数
    
    Returns:
        检测结果对象
    """
    detection_id = str(uuid.uuid4())
    
    result = DetectionResult(
        id=detection_id,
        user_id=user_id,
        detection_type=detection_type,
        original_image_id=original_image_id,
        detected_image_id=detected_image_id,
        is_tampered=is_tampered,
        tamper_ratio=f"{tamper_ratio:.4f}",
        confidence=f"{confidence:.4f}" if confidence else None,
        tampered_regions=json.dumps(tampered_regions) if tampered_regions else None,
        visualization_path=visualization_path,
        detection_params=json.dumps(detection_params) if detection_params else None
    )
    
    db.add(result)
    db.commit()
    db.refresh(result)
    
    return result


def save_tampered_blocks(
    db: Session,
    detection_result_id: str,
    blocks: list
):
    """
    保存被篡改的块信息到数据库
    
    Args:
        db: 数据库会话
        detection_result_id: 检测结果ID
        blocks: 块信息列表（包含original_block_data）
    """
    for block in blocks:
        if block.get('is_tampered') and block.get('original_block_data'):
            block_id = str(uuid.uuid4())
            tampered_block = TamperedBlock(
                id=block_id,
                detection_result_id=detection_result_id,
                block_index=block['block_index'],
                x=block['x'],
                y=block['y'],
                width=block['width'],
                height=block['height'],
                original_block_data=block['original_block_data']
            )
            db.add(tampered_block)
    
    db.commit()


def perform_lsb_detection(
    db: Session,
    user_id: str,
    image_path: str,
    key: str,
    detected_image_id: Optional[str] = None
) -> DetectionResult:
    """
    执行LSB水印检测（方式1）
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        image_path: 待检测图片路径
        key: 用户密钥
        detected_image_id: 待检测图片ID（如果有）
    
    Returns:
        检测结果对象
    """
    # 执行检测
    is_tampered, tamper_ratio, vis_path, tamper_mask = detect_lsb_watermark(
        image_path, key, save_visualization=True
    )
    
    # 构建篡改区域（LSB检测返回的是像素级掩码，这里简化为整个图片区域）
    tampered_regions = None
    if is_tampered and tamper_mask is not None:
        # 可以进一步处理掩码，提取连通区域等
        # 这里简化处理，只返回整体信息
        from PIL import Image as PILImage
        img = PILImage.open(image_path)
        tampered_regions = [{
            "x": 0,
            "y": 0,
            "width": img.width,
            "height": img.height,
            "confidence": float(tamper_ratio)
        }]
    
    # 保存检测参数
    import hashlib
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    detection_params = {
        "key_hash": key_hash,
        "method": "lsb"
    }
    
    # 保存结果
    result = save_detection_result(
        db=db,
        user_id=user_id,
        detection_type="lsb",
        is_tampered=is_tampered,
        tamper_ratio=tamper_ratio,
        detected_image_id=detected_image_id,
        tampered_regions=tampered_regions,
        visualization_path=vis_path,
        detection_params=detection_params
    )
    
    return result


def perform_block_comparison(
    db: Session,
    user_id: str,
    original_image_path: str,
    detected_image_path: str,
    original_image_id: str,
    detected_image_id: Optional[str] = None,
    block_size: int = 64,
    threshold: float = 0.1
) -> Tuple[DetectionResult, BlockComparisonResult]:
    """
    执行分块比对检测（方式2）
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        original_image_path: 原图路径
        detected_image_path: 待检测图片路径
        original_image_id: 原图ID
        detected_image_id: 待检测图片ID（如果有）
        block_size: 块大小
        threshold: 差异阈值
    
    Returns:
        (检测结果对象, 分块比对结果)
    """
    # 执行分块比对
    comparison_result, tamper_mask = compare_images_by_blocks(
        original_image_path,
        detected_image_path,
        block_size=block_size,
        threshold=threshold,
        save_original_blocks=True
    )
    
    # 生成可视化图片
    vis_filename = f"compare_vis_{uuid.uuid4()}.jpg"
    vis_path = os.path.join(UPLOAD_DIR, vis_filename)
    visualize_block_comparison(detected_image_path, tamper_mask, vis_path)
    vis_path = vis_filename  # 只保存文件名
    
    # 构建篡改区域列表
    tampered_regions = []
    for block in comparison_result.tampered_blocks:
        tampered_regions.append({
            "x": block['x'],
            "y": block['y'],
            "width": block['width'],
            "height": block['height'],
            "confidence": block.get('difference_ratio', 0.0)
        })
    
    # 保存检测参数
    detection_params = {
        "block_size": block_size,
        "threshold": threshold,
        "method": "block_comparison"
    }
    
    # 保存结果
    result = save_detection_result(
        db=db,
        user_id=user_id,
        detection_type="compare",
        is_tampered=comparison_result.is_tampered,
        tamper_ratio=comparison_result.tamper_ratio,
        original_image_id=original_image_id,
        detected_image_id=detected_image_id,
        tampered_regions=tampered_regions if tampered_regions else None,
        visualization_path=vis_path,
        detection_params=detection_params
    )
    
    # 保存被篡改的块信息
    save_tampered_blocks(db, result.id, comparison_result.blocks)
    
    return result, comparison_result


def perform_model_detection(
    db: Session,
    user_id: str,
    image_path: str,
    detected_image_id: Optional[str] = None,
    confidence_threshold: float = 0.5
) -> DetectionResult:
    """
    执行模型检测（方式3）
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        image_path: 待检测图片路径
        detected_image_id: 待检测图片ID（如果有）
        confidence_threshold: 置信度阈值
    
    Returns:
        检测结果对象
    """
    # 执行模型检测
    is_tampered, tamper_ratio, tampered_regions, tamper_mask = detect_with_model(
        image_path,
        confidence_threshold=confidence_threshold,
        save_visualization=True
    )
    
    # 生成可视化图片（如果有篡改区域）
    vis_path = None
    if tamper_mask is not None:
        vis_filename = f"model_vis_{uuid.uuid4()}.jpg"
        vis_path_full = os.path.join(UPLOAD_DIR, vis_filename)
        # 使用模型检测的可视化方法
        from app.services.model_detection import visualize_tamper_mask
        try:
            visualize_tamper_mask(image_path, tamper_mask, vis_path_full)
            vis_path = vis_filename  # 只保存文件名
        except Exception as e:
            print(f"可视化生成失败: {str(e)}")
            # 如果可视化失败，尝试使用 block_comparison 的方法
            try:
                from app.services.block_comparison import visualize_block_comparison
                visualize_block_comparison(image_path, tamper_mask, vis_path_full)
                vis_path = vis_filename
            except:
                pass
    elif is_tampered and tampered_regions:
        # 如果有篡改区域但没有掩码，生成一个简单的可视化
        from PIL import Image as PILImage
        import numpy as np
        img = PILImage.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img_array = np.array(img)
        
        # 在篡改区域上标记
        for region in tampered_regions:
            x = region.get('x', 0)
            y = region.get('y', 0)
            w = region.get('width', 0)
            h = region.get('height', 0)
            if x + w <= img_array.shape[1] and y + h <= img_array.shape[0]:
                img_array[y:y+h, x:x+w, 0] = 255  # 红色标记
                img_array[y:y+h, x:x+w, 1] = 0
                img_array[y:y+h, x:x+w, 2] = 0
        
        vis_filename = f"model_vis_{uuid.uuid4()}.jpg"
        vis_path_full = os.path.join(UPLOAD_DIR, vis_filename)
        vis_img = PILImage.fromarray(img_array)
        vis_img.save(vis_path_full, quality=95)
        vis_path = vis_filename
    
    # 保存检测参数
    detection_params = {
        "confidence_threshold": confidence_threshold,
        "method": "model"
    }
    
    # 保存结果
    result = save_detection_result(
        db=db,
        user_id=user_id,
        detection_type="model",
        is_tampered=is_tampered,
        tamper_ratio=tamper_ratio,
        detected_image_id=detected_image_id,
        confidence=tamper_ratio if tamper_ratio > 0 else None,
        tampered_regions=tampered_regions,
        visualization_path=vis_path,
        detection_params=detection_params
    )
    
    return result

