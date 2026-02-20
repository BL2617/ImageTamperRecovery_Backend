"""
恢复API路由
用于方式2的分块恢复功能
"""
from fastapi import APIRouter, HTTPException, Path, Depends, Body
from sqlalchemy.orm import Session
from typing import List

from app.models.models import (
    RestoreBlocksRequest, RestoreBlocksResponse, RestoreBlockData
)
from app.utils.database import get_db
from app.utils.auth import get_current_user
from app.models.models import DetectionResult, TamperedBlock

router = APIRouter(prefix="/api/recovery", tags=["恢复"])


@router.post("/restore-blocks", response_model=RestoreBlocksResponse)
async def restore_blocks(
    request: RestoreBlocksRequest = Body(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    恢复被篡改的块（方式2的恢复功能）
    
    根据检测结果ID和块索引列表，返回原始块数据。
    客户端可以使用这些数据恢复被篡改的区域。
    
    - **detection_result_id**: 检测结果ID
    - **block_indices**: 要恢复的块索引列表
    """
    # 验证检测结果是否存在且属于当前用户
    detection_result = db.query(DetectionResult).filter(
        DetectionResult.id == request.detection_result_id,
        DetectionResult.user_id == current_user.id,
        DetectionResult.detection_type == "compare"  # 只有方式2支持恢复
    ).first()
    
    if not detection_result:
        raise HTTPException(
            status_code=404,
            detail="检测结果不存在、无权限访问或检测类型不支持恢复"
        )
    
    # 查询被篡改的块
    tampered_blocks = db.query(TamperedBlock).filter(
        TamperedBlock.detection_result_id == request.detection_result_id,
        TamperedBlock.block_index.in_(request.block_indices)
    ).all()
    
    if not tampered_blocks:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的块数据"
        )
    
    # 构建响应数据
    blocks_data = []
    for block in tampered_blocks:
        if block.original_block_data:
            blocks_data.append(RestoreBlockData(
                block_index=block.block_index,
                x=block.x,
                y=block.y,
                width=block.width,
                height=block.height,
                block_data=block.original_block_data
            ))
    
    return RestoreBlocksResponse(
        code=200,
        message="获取恢复数据成功",
        data=blocks_data
    )


@router.get("/blocks/{detection_result_id}")
async def get_tampered_blocks(
    detection_result_id: str = Path(..., description="检测结果ID"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取检测结果中所有被篡改的块信息
    
    - **detection_result_id**: 检测结果ID
    """
    # 验证检测结果是否存在且属于当前用户
    detection_result = db.query(DetectionResult).filter(
        DetectionResult.id == detection_result_id,
        DetectionResult.user_id == current_user.id,
        DetectionResult.detection_type == "compare"
    ).first()
    
    if not detection_result:
        raise HTTPException(
            status_code=404,
            detail="检测结果不存在或无权限访问"
        )
    
    # 查询所有被篡改的块
    tampered_blocks = db.query(TamperedBlock).filter(
        TamperedBlock.detection_result_id == detection_result_id
    ).all()
    
    blocks_data = []
    for block in tampered_blocks:
        blocks_data.append({
            "block_index": block.block_index,
            "x": block.x,
            "y": block.y,
            "width": block.width,
            "height": block.height,
            "has_original_data": block.original_block_data is not None
        })
    
    return {
        "code": 200,
        "message": "获取成功",
        "data": blocks_data
    }

