"""
图片传输后端主应用
提供图片信息查询、列表获取、下载和上传功能
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Path, Request, Depends, File, UploadFile, Form
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import os
import io
import uuid
from datetime import datetime
from PIL import Image as PILImage
from sqlalchemy.orm import Session

from app.models.models import ImageData, ImageResponse, ImageListResponse, ImageListData, Image as ImageModel
from app.utils.database import init_db, get_db, get_image_by_id, get_image_list, get_image_file_path
from app.utils.config import UPLOAD_DIR, THUMBNAIL_DIR
from app.utils.auth import get_current_user
from app.services.image_service import create_image_with_encryption
from app.api.auth_api import router as auth_router
from app.api.detection_api import router as detection_router
from app.api.recovery_api import router as recovery_router

# 确保目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMBNAIL_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    init_db()
    yield
    # 关闭时清理资源（如果需要）


app = FastAPI(
    title="图片传输后端API",
    description="为Android客户端提供图片查询和下载服务",
    version="1.0.0",
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

# 注册路由
app.include_router(auth_router)
app.include_router(detection_router)
app.include_router(recovery_router)


def generate_thumbnail(image_path: str, thumbnail_path: str, max_size: int = 300):
    """生成缩略图"""
    try:
        with PILImage.open(image_path) as img:
            img.thumbnail((max_size, max_size), PILImage.Resampling.LANCZOS)
            img.save(thumbnail_path, optimize=True, quality=85)
        return True
    except Exception as e:
        print(f"生成缩略图失败: {e}")
        return False


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
    request: Request = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取单张图片信息（通过ID，只能获取当前用户的图片）
    
    - **image_id**: 图片的唯一标识符
    """
    image = db.query(ImageModel).filter(
        ImageModel.id == image_id,
        ImageModel.user_id == current_user.id
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    # 使用请求的 base_url 动态生成 URL
    base_url = str(request.base_url).rstrip('/')
    image_url = f"{base_url}/api/images/{image_id}/download"
    thumbnail_url = f"{base_url}/api/images/{image_id}/thumbnail" if image.thumbnail_path else None
    
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
    request: Request = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取图片列表（只返回当前用户的图片）
    
    - **page**: 页码，从1开始
    - **pageSize**: 每页数量，最大100
    - **category**: 图片分类（可选）
    """
    images, total = get_image_list(page, pageSize, category, user_id=current_user.id)
    
    # 使用请求的 base_url 动态生成 URL
    base_url = str(request.base_url).rstrip('/')
    
    image_list = []
    for image in images:
        image_url = f"{base_url}/api/images/{image.id}/download"
        thumbnail_url = f"{base_url}/api/images/{image.id}/thumbnail" if image.thumbnail_path else None
        
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
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    下载图片（通过图片ID，只能下载当前用户的图片）
    
    - **image_id**: 图片的唯一标识符
    """
    image = db.query(ImageModel).filter(
        ImageModel.id == image_id,
        ImageModel.user_id == current_user.id
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    file_path = os.path.join(UPLOAD_DIR, image.file_path)
    if not os.path.exists(file_path):
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
    media_type = media_type_map.get(image.format.lower() if image.format else "", "application/octet-stream")
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=os.path.basename(file_path)
    )


@app.get("/api/images/{image_id}/thumbnail")
async def get_thumbnail(
    image_id: str = Path(..., description="图片ID"),
    db: Session = Depends(get_db)
):
    """
    获取缩略图（不需要登录）
    
    - **image_id**: 图片的唯一标识符
    """
    image = db.query(ImageModel).filter(ImageModel.id == image_id).first()
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
    media_type = media_type_map.get(image.format.lower() if image.format else "", "image/jpeg")
    
    return FileResponse(
        path=thumbnail_path,
        media_type=media_type,
        filename=os.path.basename(thumbnail_path)
    )


@app.post("/api/upload", response_model=ImageResponse)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    key: Optional[str] = Form(None),
    encryptKey: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传图片
    
    - **file**: 图片文件
    - **category**: 图片分类（可选）
    - **key**: 水印密钥（可选）
    - **encryptKey**: 加密密钥（可选）
    """
    try:
        # 验证文件类型
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
            raise HTTPException(status_code=400, detail="不支持的文件格式")
        
        # 读取文件内容
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="文件为空")
        
        # 生成唯一ID
        image_id = str(uuid.uuid4())
        file_name = f"{image_id}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        # 保存文件
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        
        # 获取图片信息
        try:
            with PILImage.open(file_path) as img:
                width, height = img.size
                format_name = img.format.lower() if img.format else file_ext[1:]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"无法读取图片信息: {str(e)}")
        
        # 生成缩略图
        thumbnail_name = f"{image_id}_thumb.{format_name}"
        thumbnail_path = os.path.join(THUMBNAIL_DIR, thumbnail_name)
        generate_thumbnail(file_path, thumbnail_path)
        
        # 创建图片记录（使用 image_service 处理加密等逻辑）
        image = create_image_with_encryption(
            db=db,
            file_path=file_name,
            thumbnail_path=thumbnail_name,
            width=width,
            height=height,
            size=len(file_bytes),
            format=format_name,
            category=category,
            user_id=current_user.id,
            watermark_key=key,
            encrypt_key=encryptKey
        )
        
        # 使用请求的 base_url 动态生成 URL
        base_url = str(request.base_url).rstrip('/')
        image_url = f"{base_url}/api/images/{image.id}/download"
        thumbnail_url = f"{base_url}/api/images/{image.id}/thumbnail"
        
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
            message="上传成功",
            data=image_data
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
