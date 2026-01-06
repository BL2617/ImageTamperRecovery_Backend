"""
图片上传API服务

新架构说明：
1. 支持两种上传模式：
   - 模式1：客户端已嵌入水印（推荐）- 客户端直接上传带水印的图片
   - 模式2：服务器嵌入水印 - 上传原图+密钥，服务器嵌入水印

2. 备份说明：
   - 原图备份存储在客户端本地，不在服务器
   - has_backup 标记是否有本地备份（由客户端管理）

3. 安全性：
   - 服务器只存储带水印的图片（用于分发）
   - 不存储原图备份，降低泄露风险
   - 只存储密钥哈希，用于验证但不存储密钥本身
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import uuid
from PIL import Image as PILImage
from datetime import datetime

from models import Image
from database import create_image, init_db
from config import UPLOAD_DIR, THUMBNAIL_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE, BASE_URL
from watermark import embed_watermark
import hashlib

app = FastAPI(title="图片上传API - 支持本地备份架构")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMBNAIL_DIR, exist_ok=True)


@app.on_event("startup")
async def startup_event():
    """初始化数据库"""
    init_db()


def generate_thumbnail(image_path: str, thumbnail_path: str, max_size: tuple = (200, 200)):
    """生成缩略图"""
    try:
        img = PILImage.open(image_path)
        img.thumbnail(max_size, PILImage.Resampling.LANCZOS)
        img.save(thumbnail_path)
        return True
    except Exception as e:
        print(f"生成缩略图失败: {e}")
        return False


@app.post("/api/upload")
async def upload_image(
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    key: Optional[str] = Form(None),
    watermark_key_hash: Optional[str] = Form(None),
    has_backup: Optional[bool] = Form(False),
    mode: Optional[str] = Form("server")  # "server" 或 "client"
):
    """
    上传图片（支持两种模式）
    
    **模式1：服务器嵌入水印（mode="server"）**
    - file: 原始图片文件
    - key: 用户密钥（用于嵌入水印）
    - category: 图片分类（可选）
    
    **模式2：客户端已嵌入水印（mode="client"，推荐）**
    - file: 已嵌入水印的图片文件
    - watermark_key_hash: 密钥的SHA256哈希值
    - has_backup: 是否有本地备份（True/False）
    - category: 图片分类（可选）
    
    说明：
    - 模式2更安全，备份在客户端本地，服务器不存储原图
    - 模式1适合客户端无法嵌入水印的场景（服务器代为处理）
    """
    # 检查文件扩展名
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持的格式: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 读取文件内容
    contents = await file.read()
    
    # 检查文件大小
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大允许 {MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    # 生成唯一文件名
    file_id = str(uuid.uuid4())
    file_name = f"{file_id}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    
    # 保存文件
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # 获取图片信息
    try:
        img = PILImage.open(file_path)
        width, height = img.size
        format_name = img.format.lower() if img.format else file_ext[1:]
        file_size = os.path.getsize(file_path)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"无法读取图片信息: {str(e)}")
    
    # 根据模式处理
    final_watermark_key_hash = None
    final_has_backup = False
    
    if mode == "client":
        # 模式2：客户端已嵌入水印
        if not watermark_key_hash:
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail="客户端模式下必须提供 watermark_key_hash"
            )
        final_watermark_key_hash = watermark_key_hash
        final_has_backup = bool(has_backup)
        
    elif mode == "server":
        # 模式1：服务器嵌入水印
        if not key:
            # 如果没有提供密钥，直接保存（不带水印）
            pass
        else:
            try:
                # 计算密钥哈希
                final_watermark_key_hash = hashlib.sha256(key.encode()).hexdigest()
                
                # 嵌入水印
                watermarked_path = os.path.join(UPLOAD_DIR, f"{file_id}_watermarked{file_ext}")
                if embed_watermark(file_path, watermarked_path, key):
                    # 替换原文件为带水印的文件
                    os.remove(file_path)
                    os.rename(watermarked_path, file_path)
                    file_size = os.path.getsize(file_path)
                else:
                    raise HTTPException(status_code=500, detail="嵌入水印失败")
            except Exception as e:
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(status_code=500, detail=f"水印处理失败: {str(e)}")
    
    # 生成缩略图
    thumbnail_name = f"{file_id}_thumb{file_ext}"
    thumbnail_path = os.path.join(THUMBNAIL_DIR, thumbnail_name)
    thumbnail_relative_path = None
    
    if generate_thumbnail(file_path, thumbnail_path):
        thumbnail_relative_path = thumbnail_name
    
    # 保存到数据库
    try:
        image = create_image(
            image_id=file_id,
            file_path=file_name,  # 只存储文件名，不存储完整路径
            thumbnail_path=thumbnail_relative_path,
            width=width,
            height=height,
            size=file_size,
            format=format_name,
            category=category,
            watermark_key_hash=final_watermark_key_hash,
            has_backup=final_has_backup
        )
        
        return {
            "code": 200,
            "message": "上传成功",
            "data": {
                "id": image.id,
                "url": f"{BASE_URL}/api/images/{image.id}/download",
                "thumbnailUrl": f"{BASE_URL}/api/images/{image.id}/thumbnail" if thumbnail_relative_path else None,
                "width": width,
                "height": height,
                "size": file_size,
                "format": format_name,
                "hasBackup": final_has_backup,
                "mode": mode
            }
        }
    except Exception as e:
        # 如果数据库保存失败，删除文件
        if os.path.exists(file_path):
            os.remove(file_path)
        if thumbnail_relative_path and os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

