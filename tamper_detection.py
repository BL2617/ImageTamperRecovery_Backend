"""
图像篡改检测API
支持增量传输和局部恢复功能
"""
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Path as PathParam, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from typing import Optional, List
import os
import numpy as np
from PIL import Image as PILImage
import base64
import io
import json

from app.utils.watermark import detect_tampering, visualize_tampering
from app.utils.database import get_image_by_id, get_image_file_path, SessionLocal
from app.utils.config import UPLOAD_DIR, BASE_URL
from app.utils.auth import get_current_active_user
from app.models.models import User
from app.services.image_service import get_tamper_regions, extract_region_data, recover_image_region
from app.services.user_service import create_operation_log
import hashlib

app = FastAPI(title="图像篡改检测API - 支持增量传输和局部恢复")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/api/detect")
async def detect_tamper(
    file: UploadFile = File(...),
    key: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """
    检测上传的图片是否被篡改（推荐方式）
    
    此接口可以检测任意来源的图片，不依赖服务器存储：
    - 可以从平台下载图片后上传检测
    - 可以检测传输过程中收到的图片
    - 适用于版权保护和证据保全场景
    
    - **file**: 待检测的图片文件（可以是下载的图片）
    - **key**: 用户密钥（用于生成和验证水印）
    
    返回：
    - isTampered: 是否被篡改
    - tamperRatio: 篡改比例（0-1）
    - visualization: 篡改位置可视化（base64编码的图片）
    """
    temp_path = None
    vis_path = None
    try:
        # 保存临时文件
        import uuid
        temp_filename = f"temp_{uuid.uuid4()}_{file.filename}"
        temp_path = os.path.join(UPLOAD_DIR, temp_filename)
        with open(temp_path, "wb") as f:
            contents = await file.read()
            f.write(contents)
        
        # 检测篡改并获取篡改区域
        is_tampered, tamper_mask, tamper_ratio, tamper_regions = get_tamper_regions(temp_path, key)
        
        # 生成可视化图像
        vis_filename = f"temp_vis_{uuid.uuid4()}.jpg"
        vis_path = os.path.join(UPLOAD_DIR, vis_filename)
        visualize_tampering(temp_path, tamper_mask, vis_path)
        
        # 读取可视化图像并转换为base64
        with open(vis_path, "rb") as f:
            vis_data = f.read()
        vis_base64 = base64.b64encode(vis_data).decode()
        
        # 确定图片格式
        img = PILImage.open(temp_path)
        format_name = img.format.lower() if img.format else "jpeg"
        media_type = "image/jpeg" if format_name in ["jpg", "jpeg"] else f"image/{format_name}"
        
        # 记录操作日志
        create_operation_log(
            db=db,
            user_id=current_user.id,
            operation_type="detect",
            operation_desc=f"检测图片篡改: {file.filename}, 篡改比例: {tamper_ratio:.2%}"
        )
        
        return {
            "code": 200,
            "message": "检测完成",
            "data": {
                "isTampered": is_tampered,
                "tamperRatio": float(tamper_ratio),
                "tamperRatioPercent": round(float(tamper_ratio) * 100, 2),
                "tamperRegions": tamper_regions,  # 篡改区域列表
                "visualization": f"data:{media_type};base64,{vis_base64}"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")
    finally:
        # 清理临时文件
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        if vis_path and os.path.exists(vis_path):
            try:
                os.remove(vis_path)
            except:
                pass


@app.post("/api/detect/{image_id}")
async def detect_tamper_by_id(
    image_id: str = PathParam(..., description="图片ID"),
    key: str = Form(..., description="用户密钥")
):
    """
    检测服务器上存储的图片是否被篡改
    
    此接口用于检测已上传到服务器的图片。
    更推荐使用 /api/detect 接口，可以直接检测任意图片文件。
    
    - **image_id**: 图片ID
    - **key**: 用户密钥（用于生成和验证水印）
    
    返回：
    - isTampered: 是否被篡改
    - tamperRatio: 篡改比例（0-1）
    - visualizationUrl: 篡改位置可视化图片的URL
    """
    try:
        # 获取图片信息
        image = get_image_by_id(image_id)
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        if not image.watermark_key_hash:
            raise HTTPException(
                status_code=400,
                detail="该图片未嵌入水印，无法检测"
            )
        
        # 验证密钥
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        if key_hash != image.watermark_key_hash:
            raise HTTPException(
                status_code=403,
                detail="密钥错误，无法验证"
            )
        
        # 获取图片路径
        file_path = get_image_file_path(image_id)
        if not file_path:
            raise HTTPException(status_code=404, detail="图片文件不存在")
        
        full_path = os.path.join(UPLOAD_DIR, file_path)
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="图片文件不存在")
        
        # 检测篡改
        is_tampered, tamper_mask, tamper_ratio = detect_tampering(full_path, key)
        
        # 生成可视化图像
        vis_filename = f"{image_id}_tamper_vis.jpg"
        vis_path = os.path.join(UPLOAD_DIR, vis_filename)
        visualize_tampering(full_path, tamper_mask, vis_path)
        
        # 返回可视化图像的URL
        vis_url = f"{BASE_URL}/api/images/{image_id}/tamper-vis"
        
        return {
            "code": 200,
            "message": "检测完成",
            "data": {
                "isTampered": is_tampered,
                "tamperRatio": float(tamper_ratio),
                "tamperRatioPercent": round(float(tamper_ratio) * 100, 2),
                "visualizationUrl": vis_url
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@app.get("/api/images/{image_id}/tamper-vis")
async def get_tamper_visualization(
    image_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取篡改可视化图像
    
    - **image_id**: 图片ID
    """
    from fastapi.responses import FileResponse
    
    # 检查图片是否属于当前用户
    image = get_image_by_id(image_id)
    if not image or image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该图片")
    
    vis_filename = f"{image_id}_tamper_vis.jpg"
    vis_path = os.path.join(UPLOAD_DIR, vis_filename)
    
    if not os.path.exists(vis_path):
        raise HTTPException(status_code=404, detail="可视化图像不存在")
    
    return FileResponse(vis_path, media_type="image/jpeg")


@app.post("/api/images/{image_id}/incremental-transfer")
async def incremental_transfer(
    image_id: str = PathParam(..., description="图片ID"),
    key: str = Form(..., description="水印密钥"),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """
    增量传输：仅传输篡改区域的数据
    
    - **image_id**: 图片ID
    - **key**: 水印密钥
    
    返回：篡改区域的图像数据（base64编码）
    """
    # 检查图片是否属于当前用户
    image = get_image_by_id(image_id)
    if not image or image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该图片")
    
    # 获取图片路径
    file_path = get_image_file_path(image_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="图片文件不存在")
    
    full_path = os.path.join(UPLOAD_DIR, file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="图片文件不存在")
    
    # 检测篡改区域
    is_tampered, tamper_mask, tamper_ratio, tamper_regions = get_tamper_regions(full_path, key)
    
    if not is_tampered or len(tamper_regions) == 0:
        return {
            "code": 200,
            "message": "未检测到篡改",
            "data": {
                "hasTamper": False,
                "regions": []
            }
        }
    
    # 提取所有篡改区域的数据
    region_data_list = []
    for region in tamper_regions:
        region_data = extract_region_data(full_path, region)
        if region_data:
            region_base64 = base64.b64encode(region_data).decode('utf-8')
            region_data_list.append({
                "region": region,
                "data": region_base64
            })
    
    # 记录操作日志
    create_operation_log(
        db=db,
        user_id=current_user.id,
        operation_type="incremental_transfer",
        operation_desc=f"增量传输图片: {image_id}, 篡改区域数: {len(tamper_regions)}",
        image_id=image_id
    )
    
    return {
        "code": 200,
        "message": "增量传输完成",
        "data": {
            "hasTamper": True,
            "tamperRatio": float(tamper_ratio),
            "regions": region_data_list
        }
    }


@app.post("/api/images/{image_id}/recover-region")
async def recover_region(
    image_id: str = PathParam(..., description="图片ID"),
    region: str = Form(..., description="需要恢复的区域，格式: x1,y1,x2,y2"),
    decrypt_key: str = Form(..., description="解密密钥"),
    backup_file: UploadFile = File(..., description="加密的原始备份文件"),
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """
    局部恢复：恢复指定区域
    
    - **image_id**: 图片ID
    - **region**: 需要恢复的区域坐标，格式: "x1,y1,x2,y2"
    - **decrypt_key**: 解密密钥
    - **backup_file**: 加密的原始备份文件
    """
    # 检查图片是否属于当前用户
    image = get_image_by_id(image_id)
    if not image or image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该图片")
    
    # 获取图片路径
    file_path = get_image_file_path(image_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="图片文件不存在")
    
    full_path = os.path.join(UPLOAD_DIR, file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="图片文件不存在")
    
    # 解析区域坐标
    try:
        coords = [int(x) for x in region.split(',')]
        if len(coords) != 4:
            raise ValueError("区域坐标格式错误")
        region_tuple = tuple(coords)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"区域坐标格式错误: {str(e)}")
    
    # 保存备份文件到临时位置
    import uuid
    temp_backup_path = os.path.join(UPLOAD_DIR, f"temp_backup_{uuid.uuid4()}.encrypted")
    with open(temp_backup_path, "wb") as f:
        contents = await backup_file.read()
        f.write(contents)
    
    try:
        # 执行局部恢复
        success = recover_image_region(full_path, temp_backup_path, region_tuple, decrypt_key)
        
        if not success:
            raise HTTPException(status_code=500, detail="局部恢复失败")
        
        # 记录操作日志
        create_operation_log(
            db=db,
            user_id=current_user.id,
            operation_type="recover_region",
            operation_desc=f"局部恢复图片: {image_id}, 区域: {region}",
            image_id=image_id
        )
        
        return {
            "code": 200,
            "message": "局部恢复成功",
            "data": {
                "imageId": image_id,
                "recoveredRegion": region
            }
        }
    finally:
        # 清理临时文件
        if os.path.exists(temp_backup_path):
            os.remove(temp_backup_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)









