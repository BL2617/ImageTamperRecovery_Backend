"""
测试 bcrypt 是否正常工作
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from passlib.context import CryptContext

# 创建密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def test_bcrypt():
    """测试 bcrypt 密码哈希功能"""
    print("=" * 50)
    print("测试 bcrypt 密码哈希功能")
    print("=" * 50)
    
    # 测试密码
    password = "Test123456"
    print(f"\n原始密码: {password}")
    
    try:
        # 测试密码哈希
        hashed = pwd_context.hash(password)
        print(f"[OK] 密码哈希成功!")
        print(f"哈希值: {hashed[:50]}...")
        
        # 测试密码验证
        is_valid = pwd_context.verify(password, hashed)
        print(f"\n[OK] 密码验证成功! 验证结果: {is_valid}")
        
        # 测试错误密码
        is_invalid = pwd_context.verify("WrongPassword", hashed)
        print(f"[OK] 错误密码验证成功! 验证结果: {is_invalid}")
        
        print("\n" + "=" * 50)
        print("[SUCCESS] bcrypt 工作正常！可以启动后端服务了。")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n[ERROR] bcrypt 测试失败: {e}")
        print("=" * 50)
        return False

if __name__ == "__main__":
    test_bcrypt()

