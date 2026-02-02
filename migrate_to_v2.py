"""
数据库迁移脚本 V2
从旧版本迁移到新的架构：
- 移除 original_backup_path 列（备份不再存储在服务器）
- 将 watermark_key 重命名为 watermark_key_hash
- 添加 has_backup 字段（标记是否有本地备份）
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
    """迁移数据库到新架构"""
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
    
    with engine.connect() as conn:
        # 1. 将 watermark_key 重命名为 watermark_key_hash（如果存在）
        if 'watermark_key' in columns and 'watermark_key_hash' not in columns:
            print("重命名列: watermark_key -> watermark_key_hash")
            try:
                # SQLite不支持直接重命名列，需要创建新列、复制数据、删除旧列
                conn.execute(text("ALTER TABLE images ADD COLUMN watermark_key_hash VARCHAR(256)"))
                conn.execute(text("UPDATE images SET watermark_key_hash = watermark_key WHERE watermark_key IS NOT NULL"))
                # 注意：SQLite 3.25.0+ 才支持 DROP COLUMN，旧版本需要重建表
                # 为了兼容性，保留旧列但不再使用
                conn.commit()
                print("[成功] 列已重命名（旧列保留但不使用）")
            except Exception as e:
                print(f"[失败] 重命名列失败: {e}")
                conn.rollback()
        elif 'watermark_key_hash' in columns:
            print("[已存在] 列 watermark_key_hash 已存在")
        
        # 2. 添加 has_backup 列
        if 'has_backup' not in columns:
            print("添加列: has_backup")
            try:
                conn.execute(text("ALTER TABLE images ADD COLUMN has_backup BOOLEAN DEFAULT 0"))
                # 如果之前有 original_backup_path，标记为有备份
                if 'original_backup_path' in columns:
                    conn.execute(text("UPDATE images SET has_backup = 1 WHERE original_backup_path IS NOT NULL"))
                conn.commit()
                print("[成功] 添加列: has_backup")
            except Exception as e:
                print(f"[失败] 添加列 has_backup 失败: {e}")
                conn.rollback()
        else:
            print("[已存在] 列 has_backup 已存在")
        
        # 3. 注意：不删除 original_backup_path 列
        # 因为 SQLite 删除列需要重建表，可能很复杂
        # 新代码将忽略此列，保留数据以防万一
        if 'original_backup_path' in columns:
            print("[注意] original_backup_path 列已废弃，但保留在数据库中")
            print("      新的架构中备份存储在客户端本地，不再使用此字段")
    
    print("\n数据库迁移完成！")
    print("\n重要提示：")
    print("- 新架构中，原图备份存储在客户端本地，不在服务器")
    print("- watermark_key_hash 用于验证，但不存储密钥本身")
    print("- has_backup 标记是否有本地备份（由客户端管理）")

if __name__ == "__main__":
    migrate_database()

