"""
配置文件
"""
import os

# 服务器配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./image_tamper_recovery.db")

# 文件存储配置
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, "thumbnails")

# API基础URL（用于生成图片URL）
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# 允许的文件格式
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# 最大文件大小（字节），默认10MB
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))

