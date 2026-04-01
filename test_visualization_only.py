"""
专门测试可视化功能
"""
import os
import sys
import numpy as np
from PIL import Image as PILImage
from app.services.model_detection import visualize_tamper_mask

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

# 创建一个模拟的篡改掩码
img = PILImage.open(test_image_path)
width, height = img.size

# 创建一个中心有篡改区域的掩码
tamper_mask = np.zeros((height, width), dtype=np.float32)

# 在中心创建一个矩形篡改区域
center_x, center_y = width // 2, height // 2
rect_width, rect_height = width // 4, height // 4
tamper_mask[center_y - rect_height//2:center_y + rect_height//2, 
            center_x - rect_width//2:center_x + rect_width//2] = 0.8

print(f"创建的掩码形状: {tamper_mask.shape}")
print(f"掩码最大值: {np.max(tamper_mask)}")
print(f"掩码最小值: {np.min(tamper_mask)}")

# 测试可视化功能
output_path = os.path.join(os.path.dirname(__file__), "test_visualization.jpg")

try:
    print("开始测试可视化功能...")
    visualize_tamper_mask(test_image_path, tamper_mask, output_path)
    print(f"可视化图片生成成功: {output_path}")
    print(f"图片大小: {os.path.getsize(output_path)} 字节")
    print("测试完成")
except Exception as e:
    print(f"测试失败: {str(e)}")
    import traceback
    traceback.print_exc()