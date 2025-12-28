"""
图片传输后端主应用
提供图片信息查询、列表获取和下载功能
"""
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import os
import io
from datetime import datetime

from models import ImageData, ImageResponse, ImageListResponse, ImageListData
from database import init_db, get_image_by_id, get_image_list, get_image_file_path
from config import BASE_URL

app = FastAPI(
    title="图片传输后端API",
    description="为Android客户端提供图片查询和下载服务",
    version="1.0.0"
)

# 配置CORS，允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 图片存储目录
UPLOAD_DIR = "uploads"
THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, "thumbnails")

# 确保目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(THUMBNAIL_DIR, exist_ok=True)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    init_db()


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
    image_id: str = Path(..., description="图片ID")
):
    """
    获取单张图片信息（通过ID）
    
    - **image_id**: 图片的唯一标识符
    """
    image = get_image_by_id(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    
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
    category: Optional[str] = Query(None, description="图片分类（可选）")
):
    """
    获取图片列表
    
    - **page**: 页码，从1开始
    - **pageSize**: 每页数量，最大100
    - **category**: 图片分类（可选）
    """
    images, total = get_image_list(page, pageSize, category)
    
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
    image_id: str = Path(..., description="图片ID")
):
    """
    下载图片（通过图片ID）
    
    - **image_id**: 图片的唯一标识符
    """
    image = get_image_by_id(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    
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

