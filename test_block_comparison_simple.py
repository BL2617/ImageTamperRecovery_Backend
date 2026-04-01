"""
简单测试分块比对检测功能
"""
import os
import sys
from app.services.block_comparison import compare_images_by_blocks

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 查找测试图片
test_image_path = None
for root, dirs, files in os.walk(os.path.dirname(__file__)):
    for file in files:
        if file.lower().endswith(('.jpg', '.jpeg', '.png')) and 'test_tampered' not in file:
            test_image_path = os.path.join(root, file)
            break
    if test_image_path:
        break

if not test_image_path:
    print("未找到测试图片，请放置一张测试图片在项目目录中")
    sys.exit(1)

print(f"使用测试图片: {test_image_path}")

# 创建一个简单的被篡改的测试图片
tampered_image_path = os.path.join(os.path.dirname(__file__), "test_tampered_simple.jpg")

# 复制原始图片并进行简单篡改
from PIL import Image as PILImage
import numpy as np

# 打开原始图片
img = PILImage.open(test_image_path)
if img.mode != 'RGB':
    img = img.convert('RGB')

# 转换为numpy数组
img_array = np.array(img)

# 在图片角落添加一个红色方块作为篡改
height, width = img_array.shape[:2]
block_size = 50

# 添加红色方块到左上角
img_array[0:block_size, 0:block_size, 0] = 255  # R通道
img_array[0:block_size, 0:block_size, 1] = 0     # G通道
img_array[0:block_size, 0:block_size, 2] = 0     # B通道

# 保存被篡改的图片
tampered_img = PILImage.fromarray(img_array)
tampered_img.save(tampered_image_path)
print(f"创建被篡改的测试图片: {tampered_image_path}")

try:
    print("\n开始测试分块比对检测功能...")
    
    # 执行分块比对检测
    result, tamper_mask = compare_images_by_blocks(
        test_image_path,
        tampered_image_path,
        block_size=64
    )
    
    print(f"检测结果:")
    print(f"- 是否被篡改: {result.is_tampered}")
    print(f"- 篡改比例: {result.tamper_ratio}")
    print(f"- 被篡改的块数: {len(result.tampered_blocks)}")
    
    if result.tampered_blocks:
        print(f"\n被篡改的块信息:")
        for i, block in enumerate(result.tampered_blocks[:3]):  # 只显示前3个
            print(f"块 {i+1}:")
            print(f"  - 索引: {block.get('block_index', 'N/A')}")
            print(f"  - 位置: ({block.get('x', 'N/A')}, {block.get('y', 'N/A')})")
            print(f"  - 大小: {block.get('width', 'N/A')}x{block.get('height', 'N/A')}")
            print(f"  - 有原始块数据: {'original_block_data' in block}")
    
    print("\n测试完成")
except Exception as e:
    print(f"\n测试失败: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    # 清理临时文件
    try:
        if os.path.exists(tampered_image_path):
            os.unlink(tampered_image_path)
    except:
        pass