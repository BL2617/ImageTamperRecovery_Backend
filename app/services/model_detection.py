"""
模型检测服务
方式3：使用 PSCC-Net 模型检测可能被修改的区域
"""
from typing import Tuple, Optional
import numpy as np
from PIL import Image as PILImage
import os
import uuid
import sys

from app.utils.config import UPLOAD_DIR, PSCC_NET_MODEL_PATH, PSCC_NET_USE_GPU

# 添加 PSCC-Net 到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
pscc_net_dir = os.path.join(backend_dir, "PSCC-Net")
if os.path.exists(pscc_net_dir):
    sys.path.insert(0, backend_dir)

# 尝试导入 PSCC-Net
# 注意：由于模块名包含连字符，需要使用 importlib 或直接导入
PSCC_NET_AVAILABLE = False
get_model_instance = None
PSCCNetInference = None

try:
    # 首先检查 torch 是否可用（避免在 Windows 上因为 DLL 问题导致整个模块加载失败）
    try:
        import torch
        TORCH_AVAILABLE = True
    except Exception as torch_error:
        TORCH_AVAILABLE = False
        print(f"警告: PyTorch 不可用，PSCC-Net 将使用占位实现")
        print(f"提示: 如果需要在 Windows 上使用 PSCC-Net，请安装 Visual C++ Redistributable")
        print(f"下载地址: https://aka.ms/vs/17/release/vc_redist.x64.exe")
        print(f"错误详情: {str(torch_error)}")
    
    if TORCH_AVAILABLE:
        # 方法1：尝试直接导入（如果 PSCC-Net 被正确安装为包）
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "pscc_net_model", 
            os.path.join(pscc_net_dir, "model.py")
        )
        if spec and spec.loader:
            pscc_net_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pscc_net_module)
            get_model_instance = pscc_net_module.get_model_instance
            PSCCNetInference = pscc_net_module.PSCCNetInference
            PSCC_NET_AVAILABLE = True
            print("成功加载 PSCC-Net 模型模块")
        else:
            raise ImportError("无法加载 PSCC-Net 模块")
    else:
        # PyTorch 不可用，跳过 PSCC-Net 加载
        PSCC_NET_AVAILABLE = False
        
except Exception as e:
    # 捕获所有其他错误（包括 torch 导入后的错误）
    error_msg = str(e)
    if "DLL" in error_msg or "c10.dll" in error_msg or "vc_redist" in error_msg.lower():
        print(f"警告: PSCC-Net 模块加载失败（可能是 Windows DLL 问题），将使用占位实现")
        print(f"提示: 请安装 Visual C++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x64.exe")
    else:
        print(f"警告: PSCC-Net 模块加载失败，将使用占位实现: {error_msg}")
    PSCC_NET_AVAILABLE = False
    get_model_instance = None
    PSCCNetInference = None


def detect_with_model(
    image_path: str,
    confidence_threshold: float = 0.5,
    save_visualization: bool = True
) -> Tuple[bool, float, list, Optional[np.ndarray]]:
    """
    使用 PSCC-Net 模型检测图片是否被篡改
    
    Args:
        image_path: 待检测图片路径
        confidence_threshold: 置信度阈值（默认0.5）
        save_visualization: 是否保存可视化图片
    
    Returns:
        (是否被篡改, 篡改比例, 篡改区域列表, 篡改掩码)
    """
    try:
        # 打开图片获取尺寸
        img = PILImage.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        width, height = img.size
        
        # 如果 PSCC-Net 可用，使用它进行检测
        if PSCC_NET_AVAILABLE and get_model_instance is not None:
            try:
                # 获取模型实例
                model = get_model_instance(model_path=PSCC_NET_MODEL_PATH)
                
                # 进行预测（使用原始尺寸）
                is_tampered, confidence, tamper_mask = model.predict_with_original_size(
                    image_path,
                    confidence_threshold=confidence_threshold
                )
                
                # 计算篡改比例
                if tamper_mask is not None and tamper_mask.size > 0:
                    # 确保掩码是二维的
                    if len(tamper_mask.shape) == 2:
                        tamper_ratio = float(np.sum(tamper_mask > 0.5)) / (width * height)
                    else:
                        tamper_ratio = 0.0
                else:
                    tamper_ratio = 0.0
                
                # 生成篡改区域列表
                tampered_regions = []
                if is_tampered and tamper_mask is not None and tamper_mask.size > 0:
                    # 确保掩码是二维的
                    if len(tamper_mask.shape) != 2:
                        # 如果是3D，取第一个通道或转换为2D
                        if len(tamper_mask.shape) == 3:
                            tamper_mask = tamper_mask[:, :, 0] if tamper_mask.shape[2] == 1 else np.mean(tamper_mask, axis=2)
                        else:
                            print(f"警告: 掩码维度不正确: {tamper_mask.shape}")
                            tamper_mask = None
                    
                    if tamper_mask is not None:
                        # 找到所有篡改区域（连通组件）
                        try:
                            from scipy import ndimage
                            # 二值化掩码
                            binary_mask = (tamper_mask > 0.5).astype(np.uint8)
                            
                            # 找到连通组件
                            labeled_mask, num_features = ndimage.label(binary_mask)
                            
                            # 为每个连通组件创建一个区域
                            for i in range(1, num_features + 1):
                                coords = np.where(labeled_mask == i)
                                if len(coords[0]) > 0:
                                    y_min, y_max = int(np.min(coords[0])), int(np.max(coords[0]))
                                    x_min, x_max = int(np.min(coords[1])), int(np.max(coords[1]))
                                    
                                    # 计算该区域的置信度（使用掩码的平均值）
                                    region_mask = (labeled_mask == i)
                                    region_confidence = float(np.mean(tamper_mask[region_mask])) if np.any(region_mask) else float(confidence)
                                    
                                    region = {
                                        'x': x_min,
                                        'y': y_min,
                                        'width': x_max - x_min + 1,
                                        'height': y_max - y_min + 1,
                                        'confidence': region_confidence
                                    }
                                    tampered_regions.append(region)
                        except ImportError:
                            # 如果没有 scipy，使用简单的边界框
                            if np.any(tamper_mask > 0.5):
                                coords = np.where(tamper_mask > 0.5)
                                y_min, y_max = int(np.min(coords[0])), int(np.max(coords[0]))
                                x_min, x_max = int(np.min(coords[1])), int(np.max(coords[1]))
                                
                                region = {
                                    'x': x_min,
                                    'y': y_min,
                                    'width': x_max - x_min + 1,
                                    'height': y_max - y_min + 1,
                                    'confidence': float(confidence)
                                }
                                tampered_regions.append(region)
                
                return is_tampered, tamper_ratio, tampered_regions, tamper_mask
                
            except Exception as e:
                import traceback
                error_msg = f"PSCC-Net 检测失败: {str(e)}\n{traceback.format_exc()}"
                print(error_msg)
                # 如果模型检测失败，回退到占位实现
                return _fallback_detection(image_path, width, height)
        else:
            # PSCC-Net 不可用，使用占位实现
            return _fallback_detection(image_path, width, height)
            
    except Exception as e:
        raise Exception(f"模型检测失败: {str(e)}")


def _fallback_detection(image_path: str, width: int, height: int) -> Tuple[bool, float, list, Optional[np.ndarray]]:
    """
    占位检测实现（当 PSCC-Net 不可用时使用）
    
    Args:
        image_path: 图片路径
        width: 图片宽度
        height: 图片高度
    
    Returns:
        (是否被篡改, 篡改比例, 篡改区域列表, 篡改掩码)
    """
    # 占位实现：返回未检测到篡改
    is_tampered = False
    tamper_ratio = 0.0
    tampered_regions = []
    tamper_mask = None
    
    return is_tampered, tamper_ratio, tampered_regions, tamper_mask


def visualize_tamper_mask(
    image_path: str,
    tamper_mask: np.ndarray,
    output_path: str,
    alpha: float = 0.5
):
    """
    可视化篡改掩码
    
    Args:
        image_path: 原始图片路径
        tamper_mask: 篡改掩码（0-1之间的浮点数数组）
        output_path: 输出图片路径
        alpha: 掩码透明度（0-1）
    """
    try:
        # 打开原始图片
        img = PILImage.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        img_array = np.array(img)
        
        # 确保掩码尺寸匹配
        if tamper_mask.shape[:2] != img_array.shape[:2]:
            mask_pil = PILImage.fromarray((tamper_mask * 255).astype(np.uint8))
            mask_resized = mask_pil.resize((img_array.shape[1], img_array.shape[0]), PILImage.BILINEAR)
            tamper_mask = np.array(mask_resized) / 255.0
        
        # 创建红色掩码
        red_mask = np.zeros_like(img_array)
        red_mask[:, :, 0] = 255  # 红色通道
        
        # 将掩码应用到图片上
        mask_3d = np.stack([tamper_mask] * 3, axis=2)
        overlay = img_array * (1 - mask_3d * alpha) + red_mask * (mask_3d * alpha)
        overlay = np.clip(overlay, 0, 255).astype(np.uint8)
        
        # 保存可视化图片
        vis_img = PILImage.fromarray(overlay)
        vis_img.save(output_path, quality=95)
        
    except Exception as e:
        raise Exception(f"可视化失败: {str(e)}")
