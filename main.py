"""
图片传输后端主应用
提供图片信息查询、列表获取和下载功能
整合账号系统、图像管理、篡改检测等功能
"""
from fastapi import FastAPI, HTTPException, Query, Path, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, List
import os
import io
import uuid
import hashlib
from datetime import datetime
from PIL import Image as PILImage

from app.models.models import ImageData, ImageResponse, ImageListResponse, ImageListData, User, Image
from app.utils.database import init_db, get_image_by_id, get_image_list, get_image_file_path, SessionLocal
from app.utils.config import BASE_URL, UPLOAD_DIR, THUMBNAIL_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from app.utils.auth import get_current_user, get_current_active_user
from app.utils.watermark import embed_watermark
from app.api.auth_api import router as auth_router
from app.services.image_service import create_image_with_encryption
from app.services.user_service import create_operation_log


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    init_db()
    yield
    # 关闭时的清理工作（如果需要）


app = FastAPI(
    title="图像篡改检测与恢复系统API",
    description="提供账号系统、图像管理、篡改定位与恢复等功能",
    version="2.0.0",
    lifespan=lifespan
)

# 配置CORS，允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保目录存在（使用配置文件中的路径）
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMBNAIL_DIR, exist_ok=True)


# 注册账号系统路由
app.include_router(auth_router)


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_thumbnail(image_path: str, thumbnail_path: str, max_size: tuple = (200, 200)):
    """生成缩略图"""
    try:
        with PILImage.open(image_path) as img:
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
    width = None
    height = None
    format_name = None
    file_size = None
    try:
        with PILImage.open(file_path) as img:
            width, height = img.size
            format_name = img.format.lower() if img.format else file_ext[1:]
        file_size = os.path.getsize(file_path)
    except Exception as e:
        # 如果无法读取图片信息，删除文件
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
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
        
        # 构建响应数据
        image_data = ImageData(
            id=image.id,
            url=f"{BASE_URL}/api/images/{image.id}/download",
            thumbnailUrl=f"{BASE_URL}/api/images/{image.id}/thumbnail" if thumbnail_relative_path else None,
            width=width,
            height=height,
            size=file_size,
            format=format_name,
            timestamp=int(image.created_at.timestamp() * 1000) if image.created_at else None
        )
        
        return ImageResponse(
            code=200,
            message="上传成功",
            data=image_data
        )
    except Exception as e:
        # 如果数据库保存失败，删除文件
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        try:
            if thumbnail_relative_path and os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "message": "图片传输后端API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/images/{image_id}", response_model=ImageResponse)
async def get_image_by_id_endpoint(
    image_id: str = Path(..., description="图片ID"),
    current_user: Optional[User] = Depends(get_current_active_user)
):
    """
    获取单张图片信息（通过ID，需要登录）
    只能获取当前用户的图片
    
    - **image_id**: 图片的唯一标识符
    """
    image = get_image_by_id(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    # 检查是否是当前用户的图片
    if image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该图片")
    
    # 构建完整的URL
    image_url = f"{BASE_URL}/api/images/{image_id}/download"
    thumbnail_url = f"{BASE_URL}/api/images/{image_id}/thumbnail" if image.thumbnail_path else None
    
    image_data = ImageData(
        id=image.id,
        url=image_url,
        thumbnailUrl=thumbnail_url,
        width=image.width,
        height=image.height,
        size=image.size,
        format=image.format,
        timestamp=int(image.created_at.timestamp() * 1000) if image.created_at else None
    )
    
    return ImageResponse(
        code=200,
        message="获取成功",
        data=image_data
    )


@app.get("/api/images", response_model=ImageListResponse)
async def get_image_list_endpoint(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    pageSize: int = Query(20, ge=1, le=100, description="每页数量"),
    category: Optional[str] = Query(None, description="图片分类（可选）"),
    current_user: Optional[User] = Depends(get_current_active_user)
):
    """
    获取图片列表（需要登录）
    只返回当前用户的图片
    
    - **page**: 页码，从1开始
    - **pageSize**: 每页数量，最大100
    - **category**: 图片分类（可选）
    """
    # 只获取当前用户的图片
    from app.utils.database import SessionLocal
    db = SessionLocal()
    try:
        from sqlalchemy import and_
        from app.models.models import Image
        query = db.query(Image).filter(Image.user_id == current_user.id)
        
        if category:
            query = query.filter(Image.category == category)
        
        total = query.count()
        offset = (page - 1) * pageSize
        images = query.order_by(Image.created_at.desc()).offset(offset).limit(pageSize).all()
    finally:
        db.close()
    
    image_list = []
    for image in images:
        image_url = f"{BASE_URL}/api/images/{image.id}/download"
        thumbnail_url = f"{BASE_URL}/api/images/{image.id}/thumbnail" if image.thumbnail_path else None
        
        image_data = ImageData(
            id=image.id,
            url=image_url,
            thumbnailUrl=thumbnail_url,
            width=image.width,
            height=image.height,
            size=image.size,
            format=image.format,
            timestamp=int(image.created_at.timestamp() * 1000) if image.created_at else None
        )
        image_list.append(image_data)
    
    return ImageListResponse(
        code=200,
        message="获取成功",
        data=ImageListData(
            images=image_list,
            total=total,
            page=page,
            pageSize=pageSize
        )
    )


@app.get("/api/images/{image_id}/download")
async def download_image_by_id(
    image_id: str = Path(..., description="图片ID"),
    current_user: Optional[User] = Depends(get_current_active_user)
):
    """
    下载图片（通过图片ID，需要登录）
    只能下载当前用户的图片
    
    - **image_id**: 图片的唯一标识符
    """
    image = get_image_by_id(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    # 检查是否是当前用户的图片
    if image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该图片")
    
    file_path = get_image_file_path(image_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="图片文件不存在")
    
    # 构建完整路径
    full_path = os.path.join(UPLOAD_DIR, file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="图片文件不存在")
    
    # 确定媒体类型
    media_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "bmp": "image/bmp"
    }
    media_type = media_type_map.get(image.format.lower(), "application/octet-stream")
    
    return FileResponse(
        path=full_path,
        media_type=media_type,
        filename=os.path.basename(full_path)
    )


@app.get("/api/images/{image_id}/thumbnail")
async def get_thumbnail(
    image_id: str = Path(..., description="图片ID")
):
    """
    获取缩略图
    
    - **image_id**: 图片的唯一标识符
    """
    image = get_image_by_id(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    if not image.thumbnail_path:
        raise HTTPException(status_code=404, detail="缩略图不存在")
    
    thumbnail_path = os.path.join(THUMBNAIL_DIR, image.thumbnail_path)
    if not os.path.exists(thumbnail_path):
        raise HTTPException(status_code=404, detail="缩略图文件不存在")
    
    media_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp"
    }
    media_type = media_type_map.get(image.format.lower(), "image/jpeg")
    
    return FileResponse(
        path=thumbnail_path,
        media_type=media_type,
        filename=os.path.basename(thumbnail_path)
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

