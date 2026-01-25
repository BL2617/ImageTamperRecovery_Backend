"""
图片上传API
支持用户认证、水印嵌入、加密存储
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import hashlib
from PIL import Image as PILImage
from datetime import datetime
from typing import Optional

from app.models.models import Image, User
from app.utils.database import init_db, SessionLocal
from app.utils.config import UPLOAD_DIR, THUMBNAIL_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE, BASE_URL
from app.utils.auth import get_current_active_user
from app.utils.watermark import embed_watermark
from app.services.image_service import create_image_with_encryption
from app.services.user_service import create_operation_log

app = FastAPI(title="图片上传API")

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


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/api/upload")
async def upload_image(
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    key: Optional[str] = Form(None),  # 水印密钥（可选）
    encrypt_key: Optional[str] = Form(None),  # 加密密钥（可选）
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """
    上传图片（需要登录）
    支持水印嵌入和加密存储
    
    - **file**: 图片文件
    - **category**: 图片分类（可选）
    - **key**: 水印密钥（可选，如果提供则嵌入水印）
    - **encrypt_key**: 加密密钥（可选，如果提供则对图像进行AES加密存储）
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
    
    # 保存原始文件
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # 如果提供了水印密钥，嵌入水印
    watermark_key_hash = None
    if key:
        watermarked_path = os.path.join(UPLOAD_DIR, f"{file_id}_watermarked{file_ext}")
        if embed_watermark(file_path, watermarked_path, key):
            # 使用带水印的图片替换原图
            os.remove(file_path)
            os.rename(watermarked_path, file_path)
            watermark_key_hash = hashlib.sha256(key.encode()).hexdigest()
    
    # 获取图片信息
    try:
        img = PILImage.open(file_path)
        width, height = img.size
        format_name = img.format.lower() if img.format else file_ext[1:]
        file_size = os.path.getsize(file_path)
    except Exception as e:
        # 如果无法读取图片信息，删除文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"无法读取图片信息: {str(e)}")
    
    # 生成缩略图
    thumbnail_name = f"{file_id}_thumb{file_ext}"
    thumbnail_path = os.path.join(THUMBNAIL_DIR, thumbnail_name)
    thumbnail_relative_path = None
    
    if generate_thumbnail(file_path, thumbnail_path):
        thumbnail_relative_path = thumbnail_name
    
    # 保存到数据库（使用加密存储服务）
    try:
        image = create_image_with_encryption(
            db=db,
            file_path=file_name,
            user_id=current_user.id,
            thumbnail_path=thumbnail_relative_path,
            width=width,
            height=height,
            size=file_size,
            format=format_name,
            category=category,
            watermark_key_hash=watermark_key_hash,
            has_backup=False,  # 备份在客户端
            encrypt_key=encrypt_key
        )
        
        # 记录操作日志
        create_operation_log(
            db=db,
            user_id=current_user.id,
            operation_type="upload",
            operation_desc=f"上传图片: {file.filename}",
            image_id=image.id
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
                "format": format_name
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

