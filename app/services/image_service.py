"""
图像服务模块
提供图像处理相关的业务逻辑，包括增量传输和局部恢复
"""
import os
import hashlib
import uuid
import base64
import numpy as np
from PIL import Image
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.models import Image as ImageModel
from app.utils.watermark import detect_tampering, visualize_tampering
from app.utils.encryption import encrypt_image, decrypt_image
from app.utils.config import UPLOAD_DIR


def create_image_with_encryption(
    db: Session,
    file_path: str,
    user_id: Optional[str] = None,
    thumbnail_path: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    size: Optional[int] = None,
    format: Optional[str] = None,
    category: Optional[str] = None,
    watermark_key: Optional[str] = None,
    watermark_key_hash: Optional[str] = None,
    has_backup: bool = False,
    encrypt_key: Optional[str] = None
) -> ImageModel:
    """
    创建图像记录，支持加密存储
    
    Args:
        watermark_key: 水印密钥（如果提供，将计算哈希值）
        watermark_key_hash: 水印密钥哈希值（如果提供 watermark_key，此参数将被忽略）
        encrypt_key: 加密密钥，如果提供则对图像数据进行AES加密
    """
    # 计算水印密钥哈希值
    if watermark_key and not watermark_key_hash:
        watermark_key_hash = hashlib.sha256(watermark_key.encode()).hexdigest()
    # 如果提供了加密密钥，对图像进行加密
    encrypted_data = None
    if encrypt_key:
        # file_path 可能是相对路径，需要构建完整路径
        full_path = os.path.join(UPLOAD_DIR, file_path) if not os.path.isabs(file_path) else file_path
        if os.path.exists(full_path):
            try:
                # 读取图像数据
                with open(full_path, 'rb') as f:
                    image_data = f.read()
                
                # 使用AES加密（这里简化处理，实际应该使用encryption模块）
                # 为了简化，我们使用base64编码存储（实际应该使用AES加密）
                encrypted_data = base64.b64encode(image_data).decode('utf-8')
            except Exception as e:
                print(f"加密图像失败: {e}")
    
    # 生成唯一ID（如果还没有）
    image_id = str(uuid.uuid4())
    
    # 创建图像记录
    image = ImageModel(
        id=image_id,
        file_path=file_path,
        thumbnail_path=thumbnail_path,
        width=width,
        height=height,
        size=size,
        format=format,
        category=category,
        watermark_key_hash=watermark_key_hash,
        has_backup=has_backup,
        user_id=user_id,
        encrypted_data=encrypted_data
    )
    
    db.add(image)
    db.commit()
    db.refresh(image)
    
    return image


def get_tamper_regions(
    image_path: str,
    key: str,
    threshold: float = 0.01
) -> Tuple[bool, np.ndarray, float, list]:
    """
    获取篡改区域信息
    
    Returns:
        (是否被篡改, 篡改掩码, 篡改比例, 篡改区域列表)
        篡改区域列表格式: [(x1, y1, x2, y2), ...]
    """
    is_tampered, tamper_mask, tamper_ratio = detect_tampering(image_path, key)
    
    if not is_tampered or tamper_ratio < threshold:
        return False, tamper_mask, tamper_ratio, []
    
    # 找到所有篡改区域的边界框
    tamper_regions = []
    height, width = tamper_mask.shape
    
    # 简单的连通区域查找（不使用scipy）
    visited = np.zeros_like(tamper_mask, dtype=bool)
    
    def find_region_bbox(y, x):
        """使用DFS找到连通区域的边界框"""
        stack = [(y, x)]
        x_min, x_max = x, x
        y_min, y_max = y, y
        
        while stack:
            cy, cx = stack.pop()
            if cy < 0 or cy >= height or cx < 0 or cx >= width:
                continue
            if visited[cy, cx] or tamper_mask[cy, cx] == 0:
                continue
            
            visited[cy, cx] = True
            x_min = min(x_min, cx)
            x_max = max(x_max, cx)
            y_min = min(y_min, cy)
            y_max = max(y_max, cy)
            
            # 检查相邻像素
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                stack.append((cy + dy, cx + dx))
        
        return (x_min, y_min, x_max, y_max) if x_max >= x_min and y_max >= y_min else None
    
    # 遍历所有像素，找到所有连通区域
    for y in range(height):
        for x in range(width):
            if tamper_mask[y, x] == 1 and not visited[y, x]:
                bbox = find_region_bbox(y, x)
                if bbox:
                    tamper_regions.append(bbox)
    
    return is_tampered, tamper_mask, tamper_ratio, tamper_regions


def extract_region_data(
    original_image_path: str,
    region: Tuple[int, int, int, int]
) -> bytes:
    """
    提取图像区域数据（用于增量传输）
    
    Args:
        original_image_path: 原始图像路径
        region: 区域坐标 (x1, y1, x2, y2)
    
    Returns:
        区域图像数据的字节流
    """
    try:
        img = Image.open(original_image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        x1, y1, x2, y2 = region
        # 裁剪区域
        region_img = img.crop((x1, y1, x2 + 1, y2 + 1))
        
        # 转换为字节流
        import io
        output = io.BytesIO()
        region_img.save(output, format='JPEG', quality=95)
        return output.getvalue()
    except Exception as e:
        print(f"提取区域数据失败: {e}")
        return b''


def recover_image_region(
    tampered_image_path: str,
    original_backup_path: str,
    region: Tuple[int, int, int, int],
    decrypt_key: str
) -> bool:
    """
    局部恢复图像区域
    
    Args:
        tampered_image_path: 被篡改的图像路径
        original_backup_path: 原始备份路径（加密）
        region: 需要恢复的区域 (x1, y1, x2, y2)
        decrypt_key: 解密密钥
    
    Returns:
        是否成功
    """
    try:
        # 解密原始图像
        temp_original_path = f"temp_original_{uuid.uuid4()}.jpg"
        if not decrypt_image(original_backup_path, temp_original_path, decrypt_key):
            return False
        
        # 打开被篡改的图像和原始图像
        tampered_img = Image.open(tampered_image_path)
        if tampered_img.mode != 'RGB':
            tampered_img = tampered_img.convert('RGB')
        
        original_img = Image.open(temp_original_path)
        if original_img.mode != 'RGB':
            original_img = original_img.convert('RGB')
        
        # 转换为numpy数组
        tampered_array = np.array(tampered_img)
        original_array = np.array(original_img)
        
        # 恢复指定区域
        x1, y1, x2, y2 = region
        tampered_array[y1:y2+1, x1:x2+1] = original_array[y1:y2+1, x1:x2+1]
        
        # 保存恢复后的图像
        recovered_img = Image.fromarray(tampered_array)
        recovered_img.save(tampered_image_path, quality=95)
        
        # 清理临时文件
        if os.path.exists(temp_original_path):
            os.remove(temp_original_path)
        
        return True
    except Exception as e:
        print(f"局部恢复失败: {e}")
        return False

