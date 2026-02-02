"""
账号系统API
提供用户注册、登录、退出登录等功能
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import Optional

from app.models.models import User, UserRegister, UserLogin, TokenResponse, UserInfo, OperationLogListResponse, OperationLogData
from app.utils.database import SessionLocal
from app.utils.auth import get_current_user, get_current_admin_user, create_access_token
from app.services.user_service import (
    create_user, authenticate_user, get_user_by_id,
    update_user_device, create_operation_log, get_operation_logs
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    if request.client:
        return request.client.host
    return "unknown"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    - **username**: 用户名
    - **email**: 邮箱
    - **password**: 密码
    - **device_id**: 设备ID（可选，用于跨设备同步）
    """
    try:
        user = create_user(
            db=db,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            device_id=user_data.device_id
        )
        
        # 创建访问令牌
        access_token = create_access_token(data={"sub": user.username})
        
        # 记录操作日志
        create_operation_log(
            db=db,
            user_id=user.id,
            operation_type="register",
            operation_desc=f"用户注册: {user.username}",
            ip_address=get_client_ip(request),
            device_info=user_data.device_id
        )
        
        return TokenResponse(
            access_token=access_token,
            user=UserInfo(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                is_admin=user.is_admin,
                created_at=user.created_at
            )
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    - **device_id**: 设备ID（可选，用于跨设备同步）
    """
    user = authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # 更新设备ID（用于跨设备同步）
    if user_data.device_id:
        update_user_device(db, user.id, user_data.device_id)
    
    # 创建访问令牌
    access_token = create_access_token(data={"sub": user.username})
    
    # 记录操作日志
    create_operation_log(
        db=db,
        user_id=user.id,
        operation_type="login",
        operation_desc=f"用户登录: {user.username}",
        ip_address=get_client_ip(request),
        device_info=user_data.device_id
    )
    
    return TokenResponse(
        access_token=access_token,
        user=UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at
        )
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    退出登录
    """
    # 记录操作日志
    create_operation_log(
        db=db,
        user_id=current_user.id,
        operation_type="logout",
        operation_desc=f"用户退出登录: {current_user.username}",
        ip_address=get_client_ip(request)
    )
    
    return {
        "code": 200,
        "message": "退出登录成功"
    }


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户信息
    """
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at
    )


@router.get("/logs", response_model=OperationLogListResponse)
async def get_user_logs(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的操作日志
    """
    logs, total = get_operation_logs(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size
    )
    
    log_data = [
        OperationLogData(
            id=log.id,
            operation_type=log.operation_type,
            operation_desc=log.operation_desc,
            image_id=log.image_id,
            ip_address=log.ip_address,
            device_info=log.device_info,
            created_at=log.created_at
        )
        for log in logs
    ]
    
    return OperationLogListResponse(
        code=200,
        message="获取成功",
        data=log_data,
        total=total,
        page=page,
        pageSize=page_size
    )


@router.get("/admin/logs", response_model=OperationLogListResponse)
async def get_all_logs(
    page: int = 1,
    page_size: int = 50,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    获取所有操作日志（管理员）
    """
    logs, total = get_operation_logs(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size
    )
    
    log_data = [
        OperationLogData(
            id=log.id,
            operation_type=log.operation_type,
            operation_desc=log.operation_desc,
            image_id=log.image_id,
            ip_address=log.ip_address,
            device_info=log.device_info,
            created_at=log.created_at
        )
        for log in logs
    ]
    
    return OperationLogListResponse(
        code=200,
        message="获取成功",
        data=log_data,
        total=total,
        page=page,
        pageSize=page_size
    )

