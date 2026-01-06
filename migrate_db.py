"""
数据库迁移脚本
添加缺失的列：original_backup_path 和 watermark_key
"""
from sqlalchemy import create_engine, inspect, text
from models import Base, Image

# 数据库文件路径
DATABASE_URL = "sqlite:///./image_tamper_recovery.db"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

def migrate_database():
    """迁移数据库，添加缺失的列"""
    inspector = inspect(engine)
    
    # 检查 images 表是否存在
    if 'images' not in inspector.get_table_names():
        print("表 images 不存在，创建新表...")
        Base.metadata.create_all(bind=engine)
        print("表创建完成！")
        return
    
    # 获取现有列
    columns = [col['name'] for col in inspector.get_columns('images')]
    print(f"当前表的列: {columns}")
    
    # 检查并添加缺失的列
    with engine.connect() as conn:
        # 添加 original_backup_path 列
        if 'original_backup_path' not in columns:
            print("添加列: original_backup_path")
            try:
                conn.execute(text("ALTER TABLE images ADD COLUMN original_backup_path VARCHAR(512)"))
                conn.commit()
                print("[成功] 添加列: original_backup_path")
            except Exception as e:
                print(f"[失败] 添加列 original_backup_path 失败: {e}")
                conn.rollback()
        else:
            print("[已存在] 列 original_backup_path 已存在")
        
        # 添加 watermark_key 列
        if 'watermark_key' not in columns:
            print("添加列: watermark_key")
            try:
                conn.execute(text("ALTER TABLE images ADD COLUMN watermark_key VARCHAR(256)"))
                conn.commit()
                print("[成功] 添加列: watermark_key")
            except Exception as e:
                print(f"[失败] 添加列 watermark_key 失败: {e}")
                conn.rollback()
        else:
            print("[已存在] 列 watermark_key 已存在")
    
    print("\n数据库迁移完成！")

if __name__ == "__main__":
    migrate_database()

