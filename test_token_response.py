"""
测试 TokenResponse 的 JSON 序列化
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.models.models import TokenResponse, UserInfo
from datetime import datetime
import json

# 创建测试响应
token_response = TokenResponse(
    code=200,
    message="注册成功",
    access_token="test_token_12345",
    token_type="bearer",
    user=UserInfo(
        id="user123",
        username="testuser",
        email="test@example.com",
        is_active=True,
        is_admin=False,
        created_at=datetime.now()
    )
)

# 序列化为 JSON
json_str = token_response.model_dump_json(by_alias=True)
print("TokenResponse JSON 输出：")
print(json_str)

# 解析回来看看
parsed = json.loads(json_str)
print("\n解析后的字典：")
print(json.dumps(parsed, indent=2, ensure_ascii=False))

# 检查字段
print("\n字段检查：")
print(f"code: {parsed.get('code')}")
print(f"message: {parsed.get('message')}")
print(f"accessToken: {parsed.get('accessToken')}")  # Android 期望的字段名
print(f"access_token: {parsed.get('access_token')}")  # Python 字段名
print(f"tokenType: {parsed.get('tokenType')}")



