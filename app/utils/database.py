"""
数据库操作模块
提供图片的增删改查功能
"""
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from app.models.models import Base, Image
import os
import hashlib
import uuid

# 数据库文件路径
DATABASE_URL = "sqlite:///./image_tamper_recovery.db"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite需要这个参数
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建表"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_image_by_id(image_id: str) -> Image | None:
    """根据ID获取图片"""
    db = SessionLocal()
    try:
        return db.query(Image).filter(Image.id == image_id).first()
    finally:
        db.close()


def get_image_list(page: int = 1, page_size: int = 20, category: str = None, user_id: str = None) -> tuple[list[Image], int]:
    """
    获取图片列表
    
    Args:
        page: 页码，从1开始
        page_size: 每页数量
        category: 分类筛选（可选）
        user_id: 用户ID（可选，如果提供则只返回该用户的图片）
    
    Returns:
        (图片列表, 总数)
    """
    db = SessionLocal()
    try:
        query = db.query(Image)
        
        # 用户筛选（必须）
        if user_id:
            query = query.filter(Image.user_id == user_id)
        else:
            # 如果没有提供 user_id，只返回没有关联用户的图片（兼容旧数据）
            query = query.filter(Image.user_id.is_(None))
        
        # 分类筛选
        if category:
            query = query.filter(Image.category == category)
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        offset = (page - 1) * page_size
        images = query.order_by(desc(Image.created_at)).offset(offset).limit(page_size).all()
        
        return images, total
    finally:
        db.close()


def create_image(
    file_path: str,
    thumbnail_path: str = None,
    width: int = None,
    height: int = None,
    size: int = None,
    format: str = None,
    category: str = None,
    image_id: str = None,
    watermark_key_hash: str = None,
    has_backup: bool = False
) -> Image:
    """
    创建图片记录
    
    Args:
        file_path: 带水印的图片文件路径（存储在服务器，用于分发）
        thumbnail_path: 缩略图路径
        width: 宽度
        height: 高度
        size: 文件大小
        format: 格式
        category: 分类
        image_id: 图片ID（如果不提供则自动生成）
        watermark_key_hash: 水印密钥的哈希值（用于验证，不存储密钥本身）
        has_backup: 是否有本地备份（备份存储在客户端，不在服务器）
    
    Returns:
        创建的Image对象
    """
    db = SessionLocal()
    try:
        if not image_id:
            # 生成唯一ID（基于文件路径的哈希值）
            image_id = hashlib.md5(file_path.encode()).hexdigest()
        
        image = Image(
            id=image_id,
            file_path=file_path,
            thumbnail_path=thumbnail_path,
            width=width,
            height=height,
            size=size,
            format=format,
            category=category,
            watermark_key_hash=watermark_key_hash,
            has_backup=has_backup
        )
        
        db.add(image)
        db.commit()
        db.refresh(image)
        return image
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_image_file_path(image_id: str) -> str | None:
    """获取图片文件路径"""
    image = get_image_by_id(image_id)
    if image:
        return image.file_path
    return None


def delete_image(image_id: str) -> bool:
    """删除图片记录"""
    db = SessionLocal()
    try:
        image = db.query(Image).filter(Image.id == image_id).first()
        if image:
            db.delete(image)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

