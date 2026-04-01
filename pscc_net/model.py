"""
PSCC-Net 模型推理封装
提供简洁的接口用于图像篡改检测
"""
import os
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
import imageio.v2 as imageio

# 导入模型组件
from .models import get_seg_model, get_hrnet_cfg, NLCDetection, DetectionHead


class PSCCNetInference:
    """
    PSCC-Net 推理类
    封装了模型加载和推理的完整流程
    """
    
    def __init__(self, checkpoint_dir=None, use_gpu=True):
        """
        初始化推理类
        
        Args:
            checkpoint_dir: 权重文件目录（默认为当前目录下的 checkpoint）
            use_gpu: 是否使用GPU（默认True）
        """
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        if checkpoint_dir is None:
            checkpoint_dir = os.path.join(current_dir, "checkpoint")
        
        self.checkpoint_dir = checkpoint_dir
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.device = torch.device('cuda:0' if self.use_gpu else 'cpu')
        
        # 模型组件
        self.fenet = None
        self.segnet = None
        self.clsnet = None
        self.model = None
        
        # 配置参数
        self.args = {
            'crop_size': [256, 256]
        }
        
        print(f"[PSCC-Net] 设备: {self.device}")
        print(f"[PSCC-Net] 权重目录: {self.checkpoint_dir}")
    
    def _load_network_weight(self, net, checkpoint_dir, name):
        """加载网络权重"""
        weight_path = os.path.join(checkpoint_dir, f'{name}.pth')
        if not os.path.exists(weight_path):
            raise FileNotFoundError(f'权重文件不存在: {weight_path}')
        
        net_state_dict = torch.load(weight_path, map_location=self.device)
        
        # 处理DataParallel的键名
        if isinstance(net, nn.DataParallel):
            if not any(k.startswith('module.') for k in net_state_dict.keys()):
                net_state_dict = {'module.' + k: v for k, v in net_state_dict.items()}
        else:
            if any(k.startswith('module.') for k in net_state_dict.keys()):
                net_state_dict = {k.replace('module.', ''): v for k, v in net_state_dict.items()}
        
        net.load_state_dict(net_state_dict, strict=False)
        print(f'[PSCC-Net] {name} 权重加载成功')
    
    def load_models(self):
        """加载所有模型组件"""
        if self.model is not None:
            return  # 已经加载过了
        
        print("[PSCC-Net] 开始加载模型...")
        
        # 1. 加载特征提取网络 (HRNet)
        print("[PSCC-Net] 加载 HRNet...")
        fenet_cfg = get_hrnet_cfg()
        # 更新预训练权重路径为绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        hrnet_pretrained_path = os.path.join(current_dir, "models", "hrnet_w18_small_v2.pth")
        if os.path.exists(hrnet_pretrained_path):
            fenet_cfg.PRETRAINED = hrnet_pretrained_path
        else:
            print(f"[PSCC-Net] 警告: HRNet 预训练权重文件不存在: {hrnet_pretrained_path}")
        self.fenet = get_seg_model(fenet_cfg)
        self.fenet = self.fenet.to(self.device)
        if self.use_gpu:
            self.fenet = nn.DataParallel(self.fenet, device_ids=[0])
        
        fenet_checkpoint_dir = os.path.join(self.checkpoint_dir, "HRNet_checkpoint")
        self._load_network_weight(self.fenet, fenet_checkpoint_dir, "HRNet")
        
        # 2. 加载定位网络 (NLCDetection)
        print("[PSCC-Net] 加载 NLCDetection...")
        self.segnet = NLCDetection(self.args)
        self.segnet = self.segnet.to(self.device)
        if self.use_gpu:
            self.segnet = nn.DataParallel(self.segnet, device_ids=[0])
        
        segnet_checkpoint_dir = os.path.join(self.checkpoint_dir, "NLCDetection_checkpoint")
        self._load_network_weight(self.segnet, segnet_checkpoint_dir, "NLCDetection")
        
        # 3. 加载分类网络 (DetectionHead)
        print("[PSCC-Net] 加载 DetectionHead...")
        self.clsnet = DetectionHead(self.args)
        self.clsnet = self.clsnet.to(self.device)
        if self.use_gpu:
            self.clsnet = nn.DataParallel(self.clsnet, device_ids=[0])
        
        clsnet_checkpoint_dir = os.path.join(self.checkpoint_dir, "DetectionHead_checkpoint")
        self._load_network_weight(self.clsnet, clsnet_checkpoint_dir, "DetectionHead")
        
        # 设置为评估模式
        self.fenet.eval()
        self.segnet.eval()
        self.clsnet.eval()
        
        self.model = {
            'fenet': self.fenet,
            'segnet': self.segnet,
            'clsnet': self.clsnet
        }
        
        print("[PSCC-Net] 所有模型加载完成")
    
    def _load_image(self, image_path, max_size=1024):
        """
        加载和预处理图像
        
        Args:
            image_path: 图像路径
            max_size: 最大尺寸（宽度或高度的最大值），超过此尺寸会自动缩放
        
        Returns:
            image_tensor: 图像tensor [1, C, H, W]
            original_shape: 原始尺寸 (H, W)
            processed_shape: 处理后的尺寸 (H, W)
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f'图像文件不存在: {image_path}')
        
        image = imageio.imread(image_path)
        
        # 处理RGBA图像
        if len(image.shape) == 3 and image.shape[-1] == 4:
            rgb = np.zeros((image.shape[0], image.shape[1], 3), dtype='float32')
            r, g, b, a = image[:, :, 0], image[:, :, 1], image[:, :, 2], image[:, :, 3]
            a = a.astype('float32') / 255.0
            rgb[:, :, 0] = r * a + (1.0 - a) * 255
            rgb[:, :, 1] = g * a + (1.0 - a) * 255
            rgb[:, :, 2] = b * a + (1.0 - a) * 255
            image = rgb.astype('uint8')
        
        # 保存原始尺寸
        original_shape = image.shape[:2]  # (H, W)
        
        # 如果图像太大，进行缩放
        h, w = original_shape
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            new_h, new_w = int(h * scale), int(w * scale)
            
            pil_image = Image.fromarray(image)
            pil_image = pil_image.resize((new_w, new_h), Image.LANCZOS)
            image = np.array(pil_image)
        
        # 转换为tensor: [C, H, W]
        image_tensor = torch.from_numpy(image.astype(np.float32) / 255.0).permute(2, 0, 1)
        # 添加batch维度: [1, C, H, W]
        image_tensor = image_tensor.unsqueeze(0)
        
        return image_tensor, original_shape, image.shape[:2]
    
    def predict(self, image_path, confidence_threshold=0.5, max_size=1024):
        """
        对图像进行篡改检测
        
        Args:
            image_path: 图像路径
            confidence_threshold: 置信度阈值（默认0.5）
            max_size: 图像最大尺寸，超过会自动缩放（默认1024）
        
        Returns:
            is_tampered: 是否被篡改 (bool)
            confidence: 篡改置信度 (float, 0-1)
            tamper_mask: 篡改掩码 (numpy array, shape: [H, W], 值在0-1之间)
        """
        if self.model is None:
            self.load_models()
        
        # 加载图像
        image_tensor, original_shape, processed_shape = self._load_image(image_path, max_size)
        image_tensor = image_tensor.to(self.device)
        
        # 推理
        with torch.no_grad():
            # 特征提取
            feat = self.fenet(image_tensor)
            
            # 定位
            pred_mask = self.segnet(feat)[0]
            pred_mask = F.interpolate(
                pred_mask, 
                size=(image_tensor.size(2), image_tensor.size(3)), 
                mode='bilinear', 
                align_corners=True
            )
            
            # 分类
            pred_logit = self.clsnet(feat)
        
        # 处理分类结果
        sm = nn.Softmax(dim=1)
        pred_logit = sm(pred_logit)
        prob_authentic = pred_logit[0, 0].item()
        prob_forged = pred_logit[0, 1].item()
        
        is_tampered = prob_forged > confidence_threshold
        
        # 获取定位掩码
        mask = pred_mask[0, 0].cpu().numpy()  # [H, W]
        
        # 如果处理后的尺寸与原始尺寸不同，需要将掩码缩放回原始尺寸
        if processed_shape != original_shape:
            mask_pil = Image.fromarray((mask * 255).astype(np.uint8))
            mask_pil = mask_pil.resize((original_shape[1], original_shape[0]), Image.BILINEAR)
            mask = np.array(mask_pil) / 255.0
        
        confidence = prob_forged
        
        return is_tampered, confidence, mask
    
    def predict_with_original_size(self, image_path, confidence_threshold=0.5):
        """
        对图像进行篡改检测，保持原始尺寸
        
        Args:
            image_path: 图像路径
            confidence_threshold: 置信度阈值（默认0.5）
        
        Returns:
            is_tampered: 是否被篡改 (bool)
            confidence: 篡改置信度 (float, 0-1)
            tamper_mask: 篡改掩码 (numpy array, shape: [H, W], 值在0-1之间)
        """
        # 使用较大的max_size以保持原始尺寸（如果内存允许）
        return self.predict(image_path, confidence_threshold, max_size=2048)


def get_model_instance(checkpoint_dir=None, use_gpu=True, model_path=None):
    """
    获取模型实例的便捷函数
    
    Args:
        checkpoint_dir: 权重文件目录
        use_gpu: 是否使用GPU
        model_path: 已废弃，保留以兼容旧代码
    
    Returns:
        PSCCNetInference 实例
    """
    return PSCCNetInference(checkpoint_dir=checkpoint_dir, use_gpu=use_gpu)

