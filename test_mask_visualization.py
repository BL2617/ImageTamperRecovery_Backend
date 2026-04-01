"""
测试掩码可视化效果，确保红色标记明显
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

# 在中心创建一个矩形篡改区域
center_x, center_y = width // 2, height // 2
rect_width, rect_height = width // 4, height // 4
tamper_mask[center_y - rect_height//2:center_y + rect_height//2, 
            center_x - rect_width//2:center_x + rect_width//2] = 0.8

print(f"创建的掩码形状: {tamper_mask.shape}")
print(f"掩码最大值: {np.max(tamper_mask)}")
print(f"掩码最小值: {np.min(tamper_mask)}")
print(f"掩码中大于 0.3 的像素数: {np.sum(tamper_mask > 0.3)}")

# 测试可视化功能
output_path = os.path.join(os.path.dirname(__file__), "test_mask_visualization.jpg")

try:
    print("\n开始测试掩码可视化功能...")
    visualize_tamper_mask(test_image_path, tamper_mask, output_path)
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
    
    print(f"\n可视化图片分析:")
    print(f"- 图片尺寸: {vis_array.shape}")
    print(f"- 红色区域像素数: {red_pixels}")
    print(f"- 红色区域占比: {red_pixels / (height * width) * 100:.2f}%")
    
    if red_pixels > 1000:
        print("✅ 成功: 可视化图片包含明显的红色标记区域")
    else:
        print("❌ 失败: 可视化图片红色标记不明显")
    
    print("\n测试完成")
except Exception as e:
    print(f"\n测试失败: {str(e)}")
    import traceback
    traceback.print_exc()