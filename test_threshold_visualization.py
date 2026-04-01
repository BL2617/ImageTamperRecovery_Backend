"""
测试不同可视化阈值的效果
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
        if file.lower().endswith(('.jpg', '.jpeg', '.png')) and 'test_visualization' not in file:
            test_image_path = os.path.join(root, file)
            break
    if test_image_path:
        break

if not test_image_path:
    print("未找到测试图片，请放置一张测试图片在项目目录中")
    sys.exit(1)

print(f"使用测试图片: {test_image_path}")

# 打开图片获取尺寸
img = PILImage.open(test_image_path)
width, height = img.size

# 创建一个中心有篡改区域的掩码（模拟模型输出）
tamper_mask = np.zeros((height, width), dtype=np.float32)

# 在中心创建一个矩形篡改区域，边缘带有渐变效果
center_x, center_y = width // 2, height // 2
rect_width, rect_height = width // 4, height // 4

# 创建带有渐变边缘的篡改区域
for y in range(center_y - rect_height//2, center_y + rect_height//2):
    for x in range(center_x - rect_width//2, center_x + rect_width//2):
        # 计算到中心的距离
        dx = abs(x - center_x) / (rect_width//2)
        dy = abs(y - center_y) / (rect_height//2)
        distance = max(dx, dy)
        
        # 根据距离设置掩码值（中心为1.0，边缘逐渐减小到0）
        if distance < 0.8:
            tamper_mask[y, x] = 1.0
        elif distance < 1.0:
            # 渐变过渡
            tamper_mask[y, x] = 1.0 - (distance - 0.8) / 0.2

print(f"创建的掩码形状: {tamper_mask.shape}")
print(f"掩码最大值: {np.max(tamper_mask)}")
print(f"掩码最小值: {np.min(tamper_mask)}")
print(f"掩码中大于 0.3 的像素数: {np.sum(tamper_mask > 0.3)}")
print(f"掩码中大于 0.5 的像素数: {np.sum(tamper_mask > 0.5)}")
print(f"掩码中大于 0.7 的像素数: {np.sum(tamper_mask > 0.7)}")

# 测试不同阈值的可视化效果
thresholds = [0.3, 0.5, 0.7]

for threshold in thresholds:
    output_path = os.path.join(os.path.dirname(__file__), f"test_threshold_{threshold}_visualization.jpg")
    
    try:
        print(f"\n开始测试阈值 {threshold} 的可视化功能...")
        visualize_tamper_mask(test_image_path, tamper_mask, output_path, threshold=threshold)
        print(f"可视化图片生成成功: {output_path}")
        print(f"图片大小: {os.path.getsize(output_path)} 字节")
        
        # 检查生成的图片
        vis_img = PILImage.open(output_path)
        vis_array = np.array(vis_img)
        
        # 检查红色通道是否有明显的红色区域
        red_channel = vis_array[:, :, 0]
        green_channel = vis_array[:, :, 1]
        blue_channel = vis_array[:, :, 2]
        
        # 计算红色区域（红色通道值远大于绿色和蓝色）
        red_regions = np.where((red_channel > 200) & (green_channel < 100) & (blue_channel < 100), 1, 0)
        red_pixels = np.sum(red_regions)
        
        print(f"红色区域像素数: {red_pixels}")
        print(f"红色区域占比: {red_pixels / (height * width) * 100:.2f}%")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

print("\n测试完成")