# PSCC-Net 推理封装

这是 PSCC-Net 图像篡改检测模型的最小推理封装，专门为后端服务设计。

## 目录结构

```
pscc_net/
├── __init__.py          # 包初始化文件
├── model.py             # 推理封装主文件
├── models/              # 模型定义文件
│   ├── seg_hrnet.py
│   ├── seg_hrnet_config.py
│   ├── NLCDetection.py
│   ├── detection_head.py
│   └── hrnet_w18_small_v2.pth  # HRNet 预训练权重
└── checkpoint/          # 模型权重文件
    ├── HRNet_checkpoint/
    │   └── HRNet.pth
    ├── NLCDetection_checkpoint/
    │   └── NLCDetection.pth
    └── DetectionHead_checkpoint/
        └── DetectionHead.pth
```

## 使用方法

### 基本使用

```python
from pscc_net import get_model_instance

# 获取模型实例
model = get_model_instance(
    checkpoint_dir="pscc_net/checkpoint",  # 权重文件目录
    use_gpu=True  # 是否使用GPU
)

# 加载模型（首次调用时自动加载）
model.load_models()

# 进行检测
is_tampered, confidence, tamper_mask = model.predict(
    image_path="path/to/image.jpg",
    confidence_threshold=0.5
)
```

### 高级使用

```python
from pscc_net import PSCCNetInference

# 创建推理实例
inference = PSCCNetInference(
    checkpoint_dir="pscc_net/checkpoint",
    use_gpu=True
)

# 加载模型
inference.load_models()

# 检测（保持原始尺寸）
is_tampered, confidence, mask = inference.predict_with_original_size(
    image_path="path/to/image.jpg",
    confidence_threshold=0.5
)

# 检测（自动缩放大图）
is_tampered, confidence, mask = inference.predict(
    image_path="path/to/image.jpg",
    confidence_threshold=0.5,
    max_size=1024  # 最大尺寸，超过会自动缩放
)
```

## 返回值说明

- `is_tampered`: 布尔值，表示是否检测到篡改
- `confidence`: 浮点数 (0-1)，表示篡改的置信度
- `tamper_mask`: numpy 数组，形状为 [H, W]，值在 0-1 之间，表示每个像素的篡改概率

## 注意事项

1. 首次调用 `predict()` 或 `predict_with_original_size()` 时会自动加载模型，也可以手动调用 `load_models()` 提前加载
2. 如果图像尺寸过大，建议使用 `predict()` 并设置合适的 `max_size` 参数以避免内存不足
3. 确保已安装所有依赖：`torch`, `numpy`, `PIL`, `imageio`, `scipy`（可选，用于连通域分析）

## 与后端集成

在后端服务中，通过 `app.services.model_detection` 模块使用：

```python
from app.services.model_detection import detect_with_model

is_tampered, tamper_ratio, tampered_regions, tamper_mask = detect_with_model(
    image_path="path/to/image.jpg",
    confidence_threshold=0.5
)
```

配置在 `app.utils.config` 中：
- `PSCC_NET_CHECKPOINT_DIR`: 权重文件目录
- `PSCC_NET_USE_GPU`: 是否使用GPU





