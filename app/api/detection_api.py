"""
检测API路由
提供三种检测方式的接口
"""
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Path, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid
import json
import tempfile

from app.models.models import (
    DetectionResponse, DetectionResultData, TamperedRegion,
    BlockComparisonResponse, BlockComparisonData
)
from app.utils.database import get_db
from app.utils.auth import get_current_user
from app.utils.config import UPLOAD_DIR
from app.services.detection_service import (
    perform_lsb_detection,
    perform_block_comparison,
    perform_model_detection,
    add_watermark
)
from app.models.models import Image as ImageModel

router = APIRouter(prefix="/api/detection", tags=["检测"])


def format_created_at(created_at_value):
    """格式化created_at字段为字符串"""
    if created_at_value and hasattr(created_at_value, 'isoformat'):
        return created_at_value.isoformat()
    return created_at_value


@router.post("/lsb", response_model=DetectionResponse)
async def detect_lsb(
    request: Request,
    file: UploadFile = File(..., description="待检测的图片文件"),
    key: str = Form("", description="用户密钥（用于生成和验证水印，可为空）"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    方式1：LSB水印检测
    
    检测图片中的自定义最低位是否符合自定义规则。
    支持本地和云端检测。
    无恢复选择。
    
    - **file**: 待检测的图片文件
    - **key**: 用户密钥
    """
    temp_path = None
    try:
        # 保存临时文件
        temp_filename = f"temp_{uuid.uuid4()}_{file.filename}"
        temp_path = os.path.join(UPLOAD_DIR, temp_filename)
        
        with open(temp_path, "wb") as f:
            contents = await file.read()
            f.write(contents)
        
        # 执行检测
        result = perform_lsb_detection(
            db=db,
            user_id=current_user.id,
            image_path=temp_path,
            key=key
        )
        
        # 构建响应数据
        base_url = str(request.base_url).rstrip('/')
        visualization_url = None
        if result.visualization_path:
            visualization_url = f"{base_url}/api/detection/visualization/{result.id}"
        
        # 解析篡改区域
        tampered_regions = None
        if result.tampered_regions:
            tampered_regions = json.loads(result.tampered_regions)
        
        tamper_ratio_percent = float(result.tamper_ratio) * 100 if result.tamper_ratio else 0.0
        
        result_data = DetectionResultData(
            id=result.id,
            detection_type=result.detection_type,
            original_image_id=result.original_image_id,
            detected_image_id=result.detected_image_id,
            is_tampered=result.is_tampered,
            tamper_ratio=result.tamper_ratio,
            tamper_ratio_percent=tamper_ratio_percent,
            confidence=result.confidence,
            tampered_regions=[TamperedRegion(**r) for r in tampered_regions] if tampered_regions else None,
            visualization_url=visualization_url,
            created_at=format_created_at(result.created_at)
        )
        
        return DetectionResponse(
            code=200,
            message="检测完成",
            data=result_data
        )
    except Exception as e:
        import traceback
        error_detail = f"检测失败: {str(e)}\n{traceback.format_exc()}"
        print(f"LSB检测错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")
    finally:
        # 清理临时文件
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


@router.post("/compare", response_model=BlockComparisonResponse)
async def detect_compare(
    request: Request,
    original_image_id: str = Form(..., description="原图ID（从已上传的图片列表中选择）"),
    file: UploadFile = File(..., description="待检测的图片文件"),
    block_size: int = Form(64, description="块大小（默认64）"),
    threshold: float = Form(0.1, description="差异阈值（默认0.1）"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    方式2：分块比对检测
    
    用户从已上传的图片列表中选择原图，然后上传待检测图片进行分块比对。
    若后续需要复原，可仅传输被更改的块。
    
    - **original_image_id**: 原图ID（从已上传的图片列表中选择）
    - **file**: 待检测的图片文件
    - **block_size**: 块大小（默认64x64）
    - **threshold**: 差异阈值（0-1），超过此阈值认为块被篡改
    """
    temp_path = None
    try:
        # 验证原图是否存在且属于当前用户
        original_image = db.query(ImageModel).filter(
            ImageModel.id == original_image_id,
            ImageModel.user_id == current_user.id
        ).first()
        
        if not original_image:
            raise HTTPException(status_code=404, detail="原图不存在或无权限访问")
        
        # 获取原图路径
        original_path = os.path.join(UPLOAD_DIR, original_image.file_path)
        if not os.path.exists(original_path):
            raise HTTPException(status_code=404, detail="原图文件不存在")
        
        # 保存待检测文件
        temp_filename = f"temp_{uuid.uuid4()}_{file.filename}"
        temp_path = os.path.join(UPLOAD_DIR, temp_filename)
        
        with open(temp_path, "wb") as f:
            contents = await file.read()
            f.write(contents)
        
        # 执行检测
        result, comparison_result = perform_block_comparison(
            db=db,
            user_id=current_user.id,
            original_image_path=original_path,
            detected_image_path=temp_path,
            original_image_id=original_image_id,
            block_size=block_size,
            threshold=threshold
        )
        
        # 构建响应数据
        base_url = str(request.base_url).rstrip('/')
        visualization_url = None
        if result.visualization_path:
            visualization_url = f"{base_url}/api/detection/visualization/{result.id}"
        
        # 解析篡改区域
        tampered_regions = None
        if result.tampered_regions:
            tampered_regions = json.loads(result.tampered_regions)
        
        tamper_ratio_percent = float(result.tamper_ratio) * 100 if result.tamper_ratio else 0.0
        
        result_data = DetectionResultData(
            id=result.id,
            detection_type=result.detection_type,
            original_image_id=result.original_image_id,
            detected_image_id=result.detected_image_id,
            is_tampered=result.is_tampered,
            tamper_ratio=result.tamper_ratio,
            tamper_ratio_percent=tamper_ratio_percent,
            confidence=result.confidence,
            tampered_regions=[TamperedRegion(**r) for r in tampered_regions] if tampered_regions else None,
            visualization_url=visualization_url,
            created_at=format_created_at(result.created_at)
        )
        
        # 构建块信息
        blocks_data = []
        for block in comparison_result.blocks:
            blocks_data.append(BlockComparisonData(
                block_index=block['block_index'],
                x=block['x'],
                y=block['y'],
                width=block['width'],
                height=block['height'],
                is_tampered=block['is_tampered'],
                difference_ratio=block.get('difference_ratio')
            ))
        
        return BlockComparisonResponse(
            code=200,
            message="检测完成",
            data=result_data,
            blocks=blocks_data
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"检测失败: {str(e)}\n{traceback.format_exc()}"
        print(f"分块比对检测错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")
    finally:
        # 清理临时文件
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


@router.post("/model", response_model=DetectionResponse)
async def detect_model(
    request: Request,
    file: UploadFile = File(..., description="待检测的图片文件"),
    confidence_threshold: float = Form(0.5, description="置信度阈值（默认0.5）"),
    visualization_threshold: float = Form(0.33, description="可视化阈值（默认0.3），大于此值的区域会被标记为红色"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    方式3：模型检测
    
    使用小模型检测可能被修改的区域。
    安卓端显示"正在检测中"。
    后端返回被篡改的块/被篡改可能性大于50%的区域，在安卓原图上进行可视化标注。
    
    - **file**: 待检测的图片文件
    - **confidence_threshold**: 置信度阈值（默认0.5）
    - **visualization_threshold**: 可视化阈值（默认0.3），大于此值的区域会被标记为红色
    """
    temp_path = None
    try:
        # 保存临时文件
        temp_filename = f"temp_{uuid.uuid4()}_{file.filename}"
        temp_path = os.path.join(UPLOAD_DIR, temp_filename)
        
        with open(temp_path, "wb") as f:
            contents = await file.read()
            f.write(contents)
        
        # 执行检测
        result = perform_model_detection(
            db=db,
            user_id=current_user.id,
            image_path=temp_path,
            confidence_threshold=confidence_threshold,
            visualization_threshold=visualization_threshold
        )
        
        # 构建响应数据
        base_url = str(request.base_url).rstrip('/')
        visualization_url = None
        if result.visualization_path:
            visualization_url = f"{base_url}/api/detection/visualization/{result.id}"
        
        # 解析篡改区域
        tampered_regions = None
        if result.tampered_regions:
            tampered_regions = json.loads(result.tampered_regions)
        
        tamper_ratio_percent = float(result.tamper_ratio) * 100 if result.tamper_ratio else 0.0
        
        result_data = DetectionResultData(
            id=result.id,
            detection_type=result.detection_type,
            original_image_id=result.original_image_id,
            detected_image_id=result.detected_image_id,
            is_tampered=result.is_tampered,
            tamper_ratio=result.tamper_ratio,
            tamper_ratio_percent=tamper_ratio_percent,
            confidence=result.confidence,
            tampered_regions=[TamperedRegion(**r) for r in tampered_regions] if tampered_regions else None,
            visualization_url=visualization_url,
            created_at=format_created_at(result.created_at)
        )
        
        return DetectionResponse(
            code=200,
            message="检测完成",
            data=result_data
        )
    except Exception as e:
        import traceback
        error_detail = f"检测失败: {str(e)}\n{traceback.format_exc()}"
        print(f"模型检测错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")
    finally:
        # 清理临时文件
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


@router.get("/visualization/{detection_result_id}")
async def get_visualization(
    detection_result_id: str = Path(..., description="检测结果ID"),
    db: Session = Depends(get_db)
):
    """
    获取检测结果的可视化图片
    
    - **detection_result_id**: 检测结果ID
    """
    from app.models.models import DetectionResult
    
    # 验证检测结果是否存在
    result = db.query(DetectionResult).filter(
        DetectionResult.id == detection_result_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="检测结果不存在或无权限访问")
    
    if not result.visualization_path:
        raise HTTPException(status_code=404, detail="可视化图片不存在")
    
    vis_path = os.path.join(UPLOAD_DIR, result.visualization_path)
    if not os.path.exists(vis_path):
        raise HTTPException(status_code=404, detail="可视化图片文件不存在")
    
    return FileResponse(
        path=vis_path,
        media_type="image/jpeg",
        filename=f"visualization_{detection_result_id}.jpg"
    )


@router.get("/recovery/{detection_result_id}")
async def get_recovery_data(
    detection_result_id: str = Path(..., description="检测结果ID"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取恢复数据（被篡改块的原始数据）
    
    - **detection_result_id**: 检测结果ID
    """
    from app.models.models import DetectionResult, TamperedBlock
    
    # 验证检测结果是否存在且属于当前用户
    result = db.query(DetectionResult).filter(
        DetectionResult.id == detection_result_id,
        DetectionResult.user_id == current_user.id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="检测结果不存在或无权限访问")
    
    if result.detection_type != "compare":
        raise HTTPException(status_code=400, detail="仅分块比对检测结果支持恢复功能")
    
    # 获取被篡改的块
    tampered_blocks = db.query(TamperedBlock).filter(
        TamperedBlock.detection_result_id == detection_result_id
    ).all()
    
    if not tampered_blocks:
        return {
            "code": 200,
            "message": "无需恢复，未检测到被篡改的块",
            "data": {
                "tampered_blocks": [],
                "total_blocks": 0
            }
        }
    
    # 构建恢复数据
    recovery_blocks = []
    for block in tampered_blocks:
        # 解析块数据
        block_data = {
            "block_index": block.block_index,
            "x": block.x,
            "y": block.y,
            "width": block.width,
            "height": block.height,
            "original_block_data": block.original_block_data
        }
        recovery_blocks.append(block_data)
    
    return {
        "code": 200,
        "message": "获取恢复数据成功",
        "data": {
            "tampered_blocks": recovery_blocks,
            "total_blocks": len(recovery_blocks)
        }
    }


@router.post("/watermark", response_model=DetectionResponse)
async def add_watermark_api(
    request: Request,
    file: UploadFile = File(..., description="待添加水印的图片文件"),
    watermark_text: str = Form(..., description="水印文本"),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    添加水印
    
    使用LSB算法为图片添加水印
    
    - **file**: 待添加水印的图片文件
    - **watermark_text**: 水印文本
    """
    temp_path = None
    try:
        # 保存临时文件
        temp_filename = f"temp_{uuid.uuid4()}_{file.filename}"
        temp_path = os.path.join(UPLOAD_DIR, temp_filename)
        
        with open(temp_path, "wb") as f:
            contents = await file.read()
            f.write(contents)
        
        # 执行添加水印
        result = add_watermark(
            db=db,
            user_id=current_user.id,
            image_path=temp_path,
            watermark_text=watermark_text
        )
        
        # 构建响应数据
        base_url = str(request.base_url).rstrip('/')
        visualization_url = None
        if result.visualization_path:
            visualization_url = f"{base_url}/api/detection/visualization/{result.id}"
        
        # 解析篡改区域
        tampered_regions = None
        if result.tampered_regions:
            tampered_regions = json.loads(result.tampered_regions)
        
        tamper_ratio_percent = float(result.tamper_ratio) * 100 if result.tamper_ratio else 0.0
        
        result_data = DetectionResultData(
            id=result.id,
            detection_type=result.detection_type,
            original_image_id=result.original_image_id,
            detected_image_id=result.detected_image_id,
            is_tampered=result.is_tampered,
            tamper_ratio=result.tamper_ratio,
            tamper_ratio_percent=tamper_ratio_percent,
            confidence=result.confidence,
            tampered_regions=[TamperedRegion(**r) for r in tampered_regions] if tampered_regions else None,
            visualization_url=visualization_url,
            created_at=format_created_at(result.created_at)
        )
        
        return DetectionResponse(
            code=200,
            message="添加水印完成",
            data=result_data
        )
    except Exception as e:
        import traceback
        error_detail = f"添加水印失败: {str(e)}\n{traceback.format_exc()}"
        print(f"添加水印错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"添加水印失败: {str(e)}")
    finally:
        # 清理临时文件
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


@router.get("/history")
async def get_detection_history(
    page: int = 1,
    page_size: int = 10,
    detection_type: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取检测历史
    
    - **page**: 页码（默认1）
    - **page_size**: 每页数量（默认10）
    - **detection_type**: 检测类型（可选，如lsb、model、compare、watermark）
    """
    from app.models.models import DetectionResult
    
    # 构建查询
    query = db.query(DetectionResult).filter(
        DetectionResult.user_id == current_user.id
    )
    
    # 按检测类型过滤
    if detection_type:
        query = query.filter(DetectionResult.detection_type == detection_type)
    
    # 按创建时间倒序排列
    query = query.order_by(DetectionResult.created_at.desc())
    
    # 计算总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()
    
    # 构建响应数据
    history_data = []
    for result in results:
        # 解析篡改区域
        tampered_regions = None
        if result.tampered_regions:
            import json
            tampered_regions = json.loads(result.tampered_regions)
        
        tamper_ratio_percent = float(result.tamper_ratio) * 100 if result.tamper_ratio else 0.0
        
        history_data.append({
            "id": result.id,
            "detection_type": result.detection_type,
            "original_image_id": result.original_image_id,
            "detected_image_id": result.detected_image_id,
            "is_tampered": result.is_tampered,
            "tamper_ratio": result.tamper_ratio,
            "tamper_ratio_percent": tamper_ratio_percent,
            "confidence": result.confidence,
            "created_at": format_created_at(result.created_at)
        })
    
    return {
        "code": 200,
        "message": "获取检测历史成功",
        "data": {
            "results": history_data,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    }

