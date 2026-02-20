"""
数据库迁移脚本：添加检测结果表和分块差异表
"""
from sqlalchemy import create_engine, inspect
from app.models.models import Base, DetectionResult, TamperedBlock
import os

# 数据库文件路径
DATABASE_URL = "sqlite:///./image_tamper_recovery.db"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


def migrate_database():
    """执行数据库迁移"""
    print("开始数据库迁移...")
    
    # 检查表是否已存在
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # 创建新表
    if "detection_results" not in existing_tables:
        print("创建 detection_results 表...")
        DetectionResult.__table__.create(bind=engine, checkfirst=True)
        print("[OK] detection_results 表创建成功")
    else:
        print("[OK] detection_results 表已存在")
    
    if "tampered_blocks" not in existing_tables:
        print("创建 tampered_blocks 表...")
        TamperedBlock.__table__.create(bind=engine, checkfirst=True)
        print("[OK] tampered_blocks 表创建成功")
    else:
        print("[OK] tampered_blocks 表已存在")
    
    print("\n数据库迁移完成！")


if __name__ == "__main__":
    migrate_database()

