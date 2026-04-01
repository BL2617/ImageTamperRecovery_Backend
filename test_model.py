"""
测试模型检测功能
"""
import os
import sys
import numpy as np
from app.services.model_detection import detect_with_model, PSCC_NET_AVAILABLE, get_model_instance, PSCCNetInference

# 查找测试图片
test_image_path = None
for root, dirs, files in os.walk(os.path.dirname(__file__)):
    for file in files:
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            test_image_path = os.path.join(root, file)
            break
    if test_image_path:
        break

if not test_image_path:
    print("未找到测试图片，请放置一张测试图片在项目目录中")
    sys.exit(1)

print(f"使用测试图片: {test_image_path}")
print(f"PSCC_NET_AVAILABLE: {PSCC_NET_AVAILABLE}")
print(f"get_model_instance: {get_model_instance}")
print(f"PSCCNetInference: {PSCCNetInference}")

try:
    print("开始测试模型检测...")
    is_tampered, tamper_ratio, tampered_regions, tamper_mask = detect_with_model(test_image_path)
    print(f"检测结果:")
    print(f"- 是否被篡改: {is_tampered}")
    print(f"- 篡改比例: {tamper_ratio:.4f}")
    print(f"- 篡改区域数量: {len(tampered_regions) if tampered_regions else 0}")
    print(f"- 篡改掩码形状: {tamper_mask.shape if tamper_mask is not None else 'None'}")
    print("测试完成")
except Exception as e:
    print(f"测试失败: {str(e)}")
    import traceback
    traceback.print_exc()

# 直接测试 PSCC-Net 模型
print("\n直接测试 PSCC-Net 模型...")
try:
    if PSCC_NET_AVAILABLE and get_model_instance:
        print("尝试加载 PSCC-Net 模型...")
        model = get_model_instance()
        print("模型实例创建成功")
        model.load_models()
        print("模型加载成功")
        print("直接测试完成")
    else:
        print("PSCC-Net 不可用")
except Exception as e:
    print(f"直接测试失败: {str(e)}")
    import traceback
    traceback.print_exc()