"""
图像篡改检测API

新架构说明：
1. 主要功能：检测任意来源的图片是否被篡改
   - 可以直接检测上传的图片文件（不依赖服务器存储）
   - 也可以检测服务器上存储的图片

2. 恢复功能：
   - 恢复功能已移除，改为客户端本地操作
   - 客户端使用本地备份文件进行恢复
   - 服务器不存储备份，提高安全性

3. 使用场景：
   - 验证从平台下载的图片是否被篡改
   - 验证传输过程中的图片完整性
   - 版权保护和证据保全
"""
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import os
import numpy as np
from PIL import Image as PILImage
import base64
import io

from watermark import detect_tampering, visualize_tampering
from database import get_image_by_id, get_image_file_path
from config import UPLOAD_DIR, BASE_URL
import hashlib

app = FastAPI(title="图像篡改检测API - 支持本地备份架构")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/detect")
async def detect_tamper(
    file: UploadFile = File(...),
    key: str = Form(...)
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
        
        # 检测篡改
        is_tampered, tamper_mask, tamper_ratio = detect_tampering(temp_path, key)
        
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
        
        return {
            "code": 200,
            "message": "检测完成",
            "data": {
                "isTampered": is_tampered,
                "tamperRatio": float(tamper_ratio),
                "visualization": f"data:{media_type};base64,{vis_base64}",
                "tamperRatioPercent": round(float(tamper_ratio) * 100, 2)
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
async def get_tamper_visualization(image_id: str):
    """
    获取篡改可视化图像
    
    - **image_id**: 图片ID
    """
    from fastapi.responses import FileResponse
    vis_filename = f"{image_id}_tamper_vis.jpg"
    vis_path = os.path.join(UPLOAD_DIR, vis_filename)
    
    if not os.path.exists(vis_path):
        raise HTTPException(status_code=404, detail="可视化图像不存在")
    
    return FileResponse(vis_path, media_type="image/jpeg")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)









