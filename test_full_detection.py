"""
测试完整的模型检测流程，包括可视化
"""
import os
import sys
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.detection_service import perform_model_detection
from app.models.models import Base

# 创建临时数据库
db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
db_url = f"sqlite:///{db_file.name}"

# 创建数据库引擎和会话
engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建表结构
Base.metadata.create_all(bind=engine)

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

try:
    print("开始测试完整的模型检测流程...")
    db = SessionLocal()
    
    # 执行模型检测
    result = perform_model_detection(
        db=db,
        user_id="test_user",
        image_path=test_image_path
    )
    
    print(f"检测结果:")
    print(f"- ID: {result.id}")
    print(f"- 检测类型: {result.detection_type}")
    print(f"- 是否被篡改: {result.is_tampered}")
    print(f"- 篡改比例: {result.tamper_ratio}")
    print(f"- 置信度: {result.confidence}")
    print(f"- 可视化路径: {result.visualization_path}")
    print(f"- 创建时间: {result.created_at}")
    
    # 检查可视化图片是否生成
    if result.visualization_path:
        vis_full_path = os.path.join(os.path.dirname(__file__), "uploads", result.visualization_path)
        if os.path.exists(vis_full_path):
            print(f"可视化图片生成成功: {vis_full_path}")
            print(f"图片大小: {os.path.getsize(vis_full_path)} 字节")
        else:
            print(f"可视化图片文件不存在: {vis_full_path}")
    else:
        print("未生成可视化图片")
    
    print("测试完成")
except Exception as e:
    print(f"测试失败: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
    # 清理临时数据库
    try:
        os.unlink(db_file.name)
    except:
        pass