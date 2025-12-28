"""
数据模型定义
包含数据库模型和API响应模型
"""
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

Base = declarative_base()


class Image(Base):
    """图片数据库模型"""
    __tablename__ = "images"
    
    id = Column(String(64), primary_key=True, index=True)
    file_path = Column(String(512), nullable=False)  # 文件存储路径
    thumbnail_path = Column(String(512), nullable=True)  # 缩略图路径
    width = Column(Integer, nullable=True)  # 图片宽度
    height = Column(Integer, nullable=True)  # 图片高度
    size = Column(BigInteger, nullable=True)  # 文件大小（字节）
    format = Column(String(10), nullable=True)  # 图片格式（jpg, png等）
    category = Column(String(50), nullable=True)  # 图片分类
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间


# API响应模型
class ImageData(BaseModel):
    """图片数据模型（API响应）"""
    id: Optional[str] = None
    url: str
    thumbnailUrl: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size: Optional[int] = None
    format: Optional[str] = None
    timestamp: Optional[int] = None  # 时间戳（毫秒）
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "abc123",
                "url": "http://localhost:8000/api/images/abc123/download",
                "thumbnailUrl": "http://localhost:8000/api/images/abc123/thumbnail",
                "width": 1920,
                "height": 1080,
                "size": 1024000,
                "format": "jpg",
                "timestamp": 1703779200000
            }
        }


class ImageResponse(BaseModel):
    """单张图片响应模型"""
    code: int
    message: str
    data: Optional[ImageData] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "id": "abc123",
                    "url": "http://localhost:8000/api/images/abc123/download",
                    "thumbnailUrl": "http://localhost:8000/api/images/abc123/thumbnail",
                    "width": 1920,
                    "height": 1080,
                    "size": 1024000,
                    "format": "jpg",
                    "timestamp": 1703779200000
                }
            }
        }


class ImageListData(BaseModel):
    """图片列表数据模型"""
    images: list[ImageData]
    total: int
    page: int
    pageSize: int


class ImageListResponse(BaseModel):
    """图片列表响应模型"""
    code: int
    message: str
    data: Optional[ImageListData] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "images": [
                        {
                            "id": "abc123",
                            "url": "http://localhost:8000/api/images/abc123/download",
                            "thumbnailUrl": "http://localhost:8000/api/images/abc123/thumbnail",
                            "width": 1920,
                            "height": 1080,
                            "size": 1024000,
                            "format": "jpg",
                            "timestamp": 1703779200000
                        }
                    ],
                    "total": 100,
                    "page": 1,
                    "pageSize": 20
                }
            }
        }

