"""
用户服务模块
提供用户相关的业务逻辑
"""
import hashlib
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, Tuple

from app.models.models import User, OperationLog
from app.utils.auth import get_password_hash, verify_password, create_access_token
from datetime import datetime


def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    device_id: Optional[str] = None,
    is_admin: bool = False
) -> User:
    """创建用户"""
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == username).first():
        raise ValueError("用户名已存在")
    
    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == email).first():
        raise ValueError("邮箱已被注册")
    
    # 创建用户
    user_id = hashlib.md5(f"{username}{email}{uuid.uuid4()}".encode()).hexdigest()
    hashed_password = get_password_hash(password)
    
    user = User(
        id=user_id,
        username=username,
        email=email,
        hashed_password=hashed_password,
        device_id=device_id,
        is_admin=is_admin,
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """验证用户"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """根据ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """根据用户名获取用户"""
    return db.query(User).filter(User.username == username).first()


def update_user_device(db: Session, user_id: str, device_id: str) -> bool:
    """更新用户设备ID（用于跨设备同步）"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    user.device_id = device_id
    db.commit()
    return True


def create_operation_log(
    db: Session,
    user_id: str,
    operation_type: str,
    operation_desc: Optional[str] = None,
    image_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    device_info: Optional[str] = None
) -> OperationLog:
    """创建操作日志"""
    log_id = hashlib.md5(f"{user_id}{operation_type}{uuid.uuid4()}".encode()).hexdigest()
    
    log = OperationLog(
        id=log_id,
        user_id=user_id,
        operation_type=operation_type,
        operation_desc=operation_desc,
        image_id=image_id,
        ip_address=ip_address,
        device_info=device_info
    )
    
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return log


def get_operation_logs(
    db: Session,
    user_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Tuple[list[OperationLog], int]:
    """获取操作日志列表"""
    query = db.query(OperationLog)
    
    if user_id:
        query = query.filter(OperationLog.user_id == user_id)
    
    # 获取总数
    total = query.count()
    
    # 分页查询
    offset = (page - 1) * page_size
    logs = query.order_by(desc(OperationLog.created_at)).offset(offset).limit(page_size).all()
    
    return logs, total

