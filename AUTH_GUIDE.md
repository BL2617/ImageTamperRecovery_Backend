# 认证系统使用指南

## 问题诊断：403 Forbidden

### 问题原因

当前端访问后端时出现 **403 Forbidden** 错误，原因是：

1. **后端的图片相关接口需要认证**（JWT Token）
2. **前端请求时没有携带认证 Token**
3. **Android 应用缺少登录界面**

### 解决方案总结

我已经完成了以下修复：

#### 1. 后端修复

- ✅ 修复了 `TokenResponse` 模型，添加了 `code` 和 `message` 字段
- ✅ 使用 Pydantic 的 `Field` 和别名支持驼峰命名（`accessToken`, `tokenType`）
- ✅ 确保认证 API 返回统一的响应格式
- ✅ 添加了测试脚本 `test_auth.py`

#### 2. Android 端修复

- ✅ 创建了 `AuthViewModel` 管理认证状态
- ✅ 创建了 `LoginScreen` 登录/注册界面
- ✅ 修改了 `MainActivity`，根据认证状态显示不同界面
- ✅ 修改了 `ImageViewModel`，在创建 `ImageRepository` 时传递 token
- ✅ 修改了 `ImageRepository`，支持在请求中携带 token

---

## 使用流程

### 1. 启动后端服务

```bash
# 方式1：使用批处理脚本（推荐）
cd ImageTamperRecovery_Backend
start_all_services.bat

# 方式2：手动启动主服务
python main.py
```

### 2. 创建测试账号

**方式A：使用测试脚本**

```bash
cd ImageTamperRecovery_Backend
python test_auth.py
```

这会自动创建一个测试账号：
- 用户名: `testuser`
- 密码: `Test123456`
- 邮箱: `testuser@example.com`

**方式B：使用 API 文档**

1. 访问 `http://localhost:8000/docs`
2. 找到 `/api/auth/register` 接口
3. 点击 "Try it out"
4. 输入用户信息并执行

**方式C：使用 curl**

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "testuser@example.com",
    "password": "Test123456"
  }'
```

### 3. 在 Android 应用中登录

1. **启动 Android 应用**
   - 应用会自动显示登录界面

2. **输入账号信息**
   - 用户名: `testuser`
   - 密码: `Test123456`

3. **点击登录**
   - 成功后会自动跳转到图片列表界面
   - Token 会被自动保存到本地

### 4. 验证认证是否工作

登录成功后，所有需要认证的 API 都会自动携带 Token：

- ✅ 获取图片列表: `GET /api/images`
- ✅ 获取图片详情: `GET /api/images/{id}`
- ✅ 下载图片: `GET /api/images/{id}/download`
- ✅ 上传图片: `POST /api/upload`
- ✅ 篡改检测: `POST /api/tamper-detection`

---

## API 接口说明

### 认证相关接口

#### 1. 用户注册
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "testuser",
  "email": "testuser@example.com",
  "password": "Test123456",
  "device_id": "android_device_001"  // 可选
}
```

**成功响应**:
```json
{
  "code": 200,
  "message": "注册成功",
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tokenType": "bearer",
  "user": {
    "id": "uuid",
    "username": "testuser",
    "email": "testuser@example.com",
    "isActive": true,
    "isAdmin": false,
    "createdAt": "2026-01-21T12:00:00"
  }
}
```

#### 2. 用户登录
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "testuser",
  "password": "Test123456",
  "device_id": "android_device_001"  // 可选
}
```

**成功响应**: 同注册接口

#### 3. 获取当前用户信息
```http
GET /api/auth/me
Authorization: Bearer <token>
```

#### 4. 退出登录
```http
POST /api/auth/logout
Authorization: Bearer <token>
```

#### 5. 获取操作日志
```http
GET /api/auth/logs?page=1&pageSize=20
Authorization: Bearer <token>
```

---

## 常见问题

### Q1: 登录成功但仍然出现 403

**原因**: Token 没有正确保存或传递

**解决方案**:
1. 检查 `AuthManager.saveToken()` 是否被调用
2. 检查 `ImageRepository` 是否接收到 token
3. 查看网络日志，确认请求头中是否包含 `Authorization: Bearer <token>`

### Q2: Token 过期怎么办

**默认配置**: Token 有效期为 7 天

**解决方案**:
- 用户需要重新登录
- 未来可以实现 Token 自动刷新机制

### Q3: 忘记密码怎么办

**当前版本**: 暂不支持密码找回

**临时方案**:
- 使用数据库工具直接修改密码
- 或重新注册新账号

### Q4: 如何修改 Token 有效期

编辑 `ImageTamperRecovery_Backend/app/utils/auth.py`:

```python
# 默认是 7 天
ACCESS_TOKEN_EXPIRE_DAYS = 7

# 修改为你想要的天数
ACCESS_TOKEN_EXPIRE_DAYS = 30  # 30 天
```

---

## 数据库说明

### 用户表 (users)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String | 用户唯一标识 (UUID) |
| username | String | 用户名（唯一） |
| email | String | 邮箱（唯一） |
| hashed_password | String | 加密后的密码 |
| is_active | Boolean | 是否激活 |
| is_admin | Boolean | 是否管理员 |
| device_id | String | 设备 ID（用于跨设备同步） |
| created_at | DateTime | 创建时间 |

### 操作日志表 (operation_logs)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String | 日志唯一标识 (UUID) |
| user_id | String | 用户 ID（外键） |
| operation_type | String | 操作类型 |
| operation_desc | String | 操作描述 |
| timestamp | DateTime | 操作时间 |
| ip_address | String | IP 地址 |
| device_info | String | 设备信息 |
| image_id | String | 相关图片 ID（可选） |

---

## 安全建议

### 生产环境部署

1. **启用 HTTPS**
   - 参考 `HTTPS_CONFIG.md` 配置 SSL 证书
   - 不要在生产环境使用 HTTP

2. **修改密钥**
   - 修改 `app/utils/auth.py` 中的 `SECRET_KEY`
   - 使用强随机密钥：`openssl rand -hex 32`

3. **配置 CORS**
   - 修改 `main.py` 中的 `allow_origins`
   - 只允许你的 Android 应用域名

4. **数据库备份**
   - 定期备份 SQLite 数据库文件
   - 或迁移到 PostgreSQL/MySQL

5. **日志监控**
   - 监控 `operation_logs` 表
   - 及时发现异常操作

---

## 开发调试

### 查看网络请求日志

Android 端已配置 `HttpLoggingInterceptor`，在 Logcat 中可以看到：

```
D/OkHttp: --> POST http://192.168.137.1:8000/api/auth/login
D/OkHttp: Content-Type: application/json
D/OkHttp: {"username":"testuser","password":"Test123456"}
D/OkHttp: --> END POST
D/OkHttp: <-- 200 OK http://192.168.137.1:8000/api/auth/login
D/OkHttp: {"code":200,"message":"登录成功","accessToken":"..."}
```

### 后端日志

启动后端时会显示所有请求：

```
INFO:     192.168.137.1:44006 - "POST /api/auth/login HTTP/1.1" 200 OK
INFO:     192.168.137.1:44007 - "GET /api/images?page=1&pageSize=20 HTTP/1.1" 200 OK
```

---

## 下一步优化

- [ ] 添加 Token 自动刷新机制
- [ ] 实现密码找回功能（邮件验证）
- [ ] 添加双因素认证（2FA）
- [ ] 实现记住登录状态（Refresh Token）
- [ ] 添加用户头像上传功能
- [ ] 实现跨设备数据同步
- [ ] 添加账号注销功能

---

**最后更新**: 2026-01-21



