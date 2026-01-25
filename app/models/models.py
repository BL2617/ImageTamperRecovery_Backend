"""
数据模型定义
包含数据库模型和API响应模型
"""
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

Base = declarative_base()


class User(Base):
    """用户数据库模型"""
    __tablename__ = "users"
    
    id = Column(String(64), primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    device_id = Column(String(255), nullable=True)  # 设备ID，用于跨设备同步
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    images = relationship("Image", back_populates="owner", cascade="all, delete-orphan")
    operation_logs = relationship("OperationLog", back_populates="user", cascade="all, delete-orphan")


class Image(Base):
    """图片数据库模型
    
    设计说明：
    - file_path: 存储带水印的图片路径（用于分发）
    - 不存储原图备份（备份在客户端本地）
    - watermark_key_hash: 存储密钥哈希，用于验证但不存储密钥本身
    - has_backup: 标记是否有本地备份（客户端管理）
    """
    __tablename__ = "images"
    
    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=True, index=True)  # 关联用户
    file_path = Column(String(512), nullable=False)  # 带水印的图片存储路径
    thumbnail_path = Column(String(512), nullable=True)  # 缩略图路径
    width = Column(Integer, nullable=True)  # 图片宽度
    height = Column(Integer, nullable=True)  # 图片高度
    size = Column(BigInteger, nullable=True)  # 文件大小（字节）
    format = Column(String(10), nullable=True)  # 图片格式（jpg, png等）
    category = Column(String(50), nullable=True)  # 图片分类
    watermark_key_hash = Column(String(256), nullable=True)  # 水印密钥哈希值（用于验证）
    has_backup = Column(Boolean, default=False, nullable=False)  # 是否有本地备份（不在服务器）
    encrypted_data = Column(Text, nullable=True)  # AES加密后的图像数据（base64）
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    
    # 关系
    owner = relationship("User", back_populates="images")


class OperationLog(Base):
    """操作日志数据库模型"""
    __tablename__ = "operation_logs"
    
    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    operation_type = Column(String(50), nullable=False)  # 操作类型：login, logout, upload, detect, recover等
    operation_desc = Column(String(500), nullable=True)  # 操作描述
    image_id = Column(String(64), nullable=True)  # 关联的图片ID（如果有）
    ip_address = Column(String(50), nullable=True)  # IP地址
    device_info = Column(String(200), nullable=True)  # 设备信息
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # 关系
    user = relationship("User", back_populates="operation_logs")


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


# 账号系统相关模型
class UserRegister(BaseModel):
    """用户注册模型"""
    username: str
    email: EmailStr
    password: str
    device_id: Optional[str] = None


class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: str
    device_id: Optional[str] = None


class UserInfo(BaseModel):
    """用户信息模型"""
    id: str
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    """Token响应模型"""
    code: int = 200
    message: str = "成功"
    access_token: str = Field(alias="accessToken", serialization_alias="accessToken")
    token_type: str = Field(default="bearer", alias="tokenType", serialization_alias="tokenType")
    user: Optional[UserInfo] = None
    
    model_config = {
        "populate_by_name": True,  # 允许使用字段名或别名
    }


class OperationLogData(BaseModel):
    """操作日志数据模型"""
    id: str
    operation_type: str
    operation_desc: Optional[str] = None
    image_id: Optional[str] = None
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    created_at: datetime


class OperationLogListResponse(BaseModel):
    """操作日志列表响应模型"""
    code: int
    message: str
    data: Optional[List[OperationLogData]] = None
    total: Optional[int] = None
    page: Optional[int] = None
    pageSize: Optional[int] = None

