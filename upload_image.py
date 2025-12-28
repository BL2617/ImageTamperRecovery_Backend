"""
图片上传工具脚本
用于测试和初始化数据，可以上传图片到服务器
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from PIL import Image as PILImage
from datetime import datetime

from models import Image
from database import create_image, init_db
from config import UPLOAD_DIR, THUMBNAIL_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE, BASE_URL

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


@app.post("/api/upload")
async def upload_image(
    file: UploadFile = File(...),
    category: str = None
):
    """
    上传图片
    
    - **file**: 图片文件
    - **category**: 图片分类（可选）
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
        # 如果无法读取图片信息，删除文件
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"无法读取图片信息: {str(e)}")
    
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
            category=category
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

