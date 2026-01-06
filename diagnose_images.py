"""
诊断脚本：检查图片加载问题
"""
import os
import sqlite3
from config import UPLOAD_DIR, THUMBNAIL_DIR, BASE_URL

def diagnose():
    """诊断图片加载问题"""
    print("=" * 60)
    print("图片加载问题诊断")
    print("=" * 60)
    
    # 1. 检查目录
    print("\n1. 检查目录结构：")
    print(f"   UPLOAD_DIR: {UPLOAD_DIR} (存在: {os.path.exists(UPLOAD_DIR)})")
    print(f"   THUMBNAIL_DIR: {THUMBNAIL_DIR} (存在: {os.path.exists(THUMBNAIL_DIR)})")
    
    if os.path.exists(UPLOAD_DIR):
        files = [f for f in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, f))]
        print(f"   上传目录中的文件数: {len(files)}")
        if files:
            print(f"   示例文件: {files[0]}")
    
    # 2. 检查数据库记录
    print("\n2. 检查数据库记录：")
    db_path = "image_tamper_recovery.db"
    if not os.path.exists(db_path):
        print(f"   ✗ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM images")
        count = cursor.fetchone()[0]
        print(f"   数据库中的图片记录数: {count}")
        
        if count > 0:
            cursor.execute("SELECT id, file_path, thumbnail_path FROM images LIMIT 5")
            records = cursor.fetchall()
            print("\n   前5条记录：")
            for record in records:
                image_id, file_path, thumbnail_path = record
                full_path = os.path.join(UPLOAD_DIR, file_path)
                file_exists = os.path.exists(full_path)
                
                print(f"\n   ID: {image_id}")
                print(f"   数据库中的 file_path: {file_path}")
                print(f"   完整路径: {full_path}")
                print(f"   文件是否存在: {file_exists}")
                
                if thumbnail_path:
                    thumb_full_path = os.path.join(THUMBNAIL_DIR, thumbnail_path)
                    thumb_exists = os.path.exists(thumb_full_path)
                    print(f"   缩略图路径: {thumbnail_path}")
                    print(f"   缩略图完整路径: {thumb_full_path}")
                    print(f"   缩略图是否存在: {thumb_exists}")
                
                # 生成URL
                image_url = f"{BASE_URL}/api/images/{image_id}/download"
                print(f"   图片URL: {image_url}")
                
    except Exception as e:
        print(f"   ✗ 数据库查询错误: {e}")
    finally:
        conn.close()
    
    # 3. 检查配置
    print("\n3. 检查配置：")
    print(f"   BASE_URL: {BASE_URL}")
    print(f"   (注意：如果前端在远程访问，BASE_URL应该是服务器IP，如 http://192.168.x.x:8000)")
    
    # 4. 检查文件路径问题
    print("\n4. 检查潜在问题：")
    print("   - 如果BASE_URL是localhost但前端在远程，需要改为服务器IP")
    print("   - 确保服务器防火墙允许8000端口")
    print("   - 检查文件权限")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    diagnose()

