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
import threading

from app.utils.config import UPLOAD_DIR, PSCC_NET_CHECKPOINT_DIR, PSCC_NET_USE_GPU

# 添加后端目录到路径，以便导入 pscc_net 包
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 尝试导入 PSCC-Net
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
        # 尝试导入 pscc_net 包
        try:
            import pscc_net
            get_model_instance = pscc_net.get_model_instance
            PSCCNetInference = pscc_net.PSCCNetInference
            PSCC_NET_AVAILABLE = True
            print("成功加载 PSCC-Net 模型模块")
        except ImportError as import_error:
            print(f"警告: 无法导入 pscc_net 包: {str(import_error)}")
            PSCC_NET_AVAILABLE = False
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

# 全局模型实例缓存（单例模式）
_model_instance = None
_model_lock = threading.Lock()


def preload_model():
    """
    预加载模型（可选，在服务启动时调用以提前加载模型）
    这样可以避免第一个请求时的延迟
    """
    global _model_instance
    if PSCC_NET_AVAILABLE and get_model_instance is not None:
        if _model_instance is None:
            with _model_lock:
                if _model_instance is None:
                    print("[模型检测] 预加载 PSCC-Net 模型...")
                    try:
                        _model_instance = get_model_instance(
                            checkpoint_dir=PSCC_NET_CHECKPOINT_DIR,
                            use_gpu=PSCC_NET_USE_GPU
                        )
                        _model_instance.load_models()
                        print("[模型检测] PSCC-Net 模型预加载完成")
                    except Exception as e:
                        print(f"[模型检测] 模型预加载失败: {str(e)}")
                        _model_instance = None


def detect_with_model(
    image_path: str,
    confidence_threshold: float = 0.5
) -> Tuple[bool, float, list, Optional[np.ndarray]]:
    """
    使用 PSCC-Net 模型检测图片是否被篡改
    
    Args:
        image_path: 待检测图片路径
        confidence_threshold: 置信度阈值（默认0.5）
    
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
                # 使用全局模型实例（单例模式，避免重复加载）
                global _model_instance
                
                if _model_instance is None:
                    # 使用线程锁确保只加载一次
                    with _model_lock:
                        # 双重检查，避免多线程重复加载
                        if _model_instance is None:
                            print("[模型检测] 首次加载 PSCC-Net 模型...")
                            _model_instance = get_model_instance(
                                checkpoint_dir=PSCC_NET_CHECKPOINT_DIR,
                                use_gpu=PSCC_NET_USE_GPU
                            )
                            # 加载模型
                            _model_instance.load_models()
                            print("[模型检测] PSCC-Net 模型加载完成，后续请求将复用此实例")
                
                model = _model_instance
                
                # 进行预测
                # 注意：为了避免极大图片在 CPU 上推理时间过长，这里限制最大边长（例如 1024）
                # 如果需要更高精度，可以适当调大 max_size，但会增加耗时
                print("[模型检测] 开始模型推理...")
                is_tampered, confidence, tamper_mask = model.predict(
                    image_path,
                    confidence_threshold=confidence_threshold,
                    max_size=1024
                )
                print("[模型检测] 模型推理完成")
                
                # 计算篡改比例
                if tamper_mask is not None and tamper_mask.size > 0:
                    # 确保掩码是二维的
                    if len(tamper_mask.shape) == 2:
                        # 使用较低的阈值来计算篡改比例，捕获更多潜在篡改区域
                        tamper_ratio = float(np.sum(tamper_mask > 0.3)) / (width * height)
                    else:
                        tamper_ratio = 0.0
                else:
                    tamper_ratio = 0.0
                
                # 改进分类逻辑：结合篡改比例和分类置信度
                # 如果篡改比例大于 0.5% 或者分类置信度大于 0.4，就认为图片被篡改
                improved_is_tampered = is_tampered or (tamper_ratio > 0.005) or (float(confidence) > 0.4)
                
                # 生成篡改区域列表
                tampered_regions = []
                if (improved_is_tampered or tamper_ratio > 0.001) and tamper_mask is not None and tamper_mask.size > 0:
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
                            # 使用较低的阈值来二值化掩码，捕获更多潜在篡改区域
                            binary_mask = (tamper_mask > 0.3).astype(np.uint8)
                            
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
                                    
                                    # 只添加面积大于一定阈值的区域，过滤噪声
                                    area = (x_max - x_min + 1) * (y_max - y_min + 1)
                                    if area > 100:  # 过滤小于 10x10 像素的区域
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
                            if np.any(tamper_mask > 0.3):
                                coords = np.where(tamper_mask > 0.3)
                                y_min, y_max = int(np.min(coords[0])), int(np.max(coords[0]))
                                x_min, x_max = int(np.min(coords[1])), int(np.max(coords[1]))
                                
                                # 只添加面积大于一定阈值的区域，过滤噪声
                                area = (x_max - x_min + 1) * (y_max - y_min + 1)
                                if area > 100:  # 过滤小于 10x10 像素的区域
                                    region = {
                                        'x': x_min,
                                        'y': y_min,
                                        'width': x_max - x_min + 1,
                                        'height': y_max - y_min + 1,
                                        'confidence': float(confidence)
                                    }
                                    tampered_regions.append(region)
                
                # 使用改进后的分类结果
                is_tampered = improved_is_tampered
                
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
    alpha: float = 0.5,
    threshold: float = 0.3
):
    """
    可视化篡改掩码
    
    Args:
        image_path: 原始图片路径
        tamper_mask: 篡改掩码（0-1之间的浮点数数组）
        output_path: 输出图片路径
        alpha: 掩码透明度（0-1）
        threshold: 掩码阈值（0-1），大于此值的区域会被标记为红色
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
        
        # 应用阈值处理，确保只有值大于阈值的区域才会被标记
        tamper_mask = (tamper_mask > threshold).astype(np.float32)
        
        # 创建红色掩码
        red_mask = np.zeros_like(img_array)
        red_mask[:, :, 0] = 255  # 红色通道
        
        # 创建只包含红色标记的热力图，不包含原图
        mask_3d = np.stack([tamper_mask] * 3, axis=2)
        overlay = np.zeros_like(img_array)  # 全黑背景
        overlay = overlay * (1 - mask_3d) + red_mask * mask_3d
        overlay = np.clip(overlay, 0, 255).astype(np.uint8)
        
        # 保存可视化图片
        vis_img = PILImage.fromarray(overlay)
        vis_img.save(output_path, quality=95)
        
    except Exception as e:
        raise Exception(f"可视化失败: {str(e)}")
