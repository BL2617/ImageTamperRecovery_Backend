# 403 Forbidden 调试指南

## 问题症状

```
INFO: ... "POST /api/auth/register HTTP/1.1" 200 OK
INFO: ... "GET /api/images?page=1&pageSize=20 HTTP/1.1" 403 Forbidden
```

注册/登录成功，但访问图片列表失败。

## 已实施的修复

### 1. ✅ 后端修复
- 修复了 TokenResponse 的 JSON 序列化（使用 `accessToken` 而不是 `access_token`）
- 统一了注册端点的 HTTP 状态码（200 而不是 201）
- 使用新的 lifespan 事件处理器

### 2. ✅ Android 端修复
- MainActivity: 当 authState 改变时重新创建 ImageViewModel
- 添加了详细的日志输出

## 调试步骤

### 1. 重启后端
```powershell
# 停止当前后端（Ctrl+C）
python main.py
```

### 2. 清除 Android 应用数据
在 Android Studio 或设备上：
- 进入设置 -> 应用 -> TamperRecovery
- 点击"清除数据"或"存储" -> "清除数据"
- 或卸载重新安装应用

### 3. 查看 Logcat 日志

在 Android Studio 的 Logcat 中搜索以下标签：

#### 注册流程日志
```
AuthViewModel: Register response code: xxx
AuthViewModel: Register response body: ...
AuthViewModel: TokenResponse code: 200
AuthViewModel: TokenResponse accessToken: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
AuthViewModel: Token saved: ...
AuthViewModel: User info saved: testuser
AuthViewModel: Auth state set to Authenticated
```

#### ImageViewModel 创建日志
```
ImageViewModel: ImageViewModel created with token: present (eyJhbGciOiJIUzI1NiIs...)
```

#### 网络请求日志
```
OkHttp: --> GET /api/images?page=1&pageSize=20
OkHttp: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
OkHttp: <-- 200 OK
```

### 4. 验证 Token 是否正确传递

#### 后端日志应该显示
```
INFO: ... "GET /api/images?page=1&pageSize=20 HTTP/1.1" 200 OK
```

## 常见问题

### Q1: Logcat 显示 "Token saved" 但 ImageViewModel token 是 null

**原因**: ImageViewModel 在 Token 保存之前就被创建了

**解决方案**: ✅ 已修复 - MainActivity 现在会在 authState 改变时重新创建 ImageViewModel

### Q2: 后端仍然返回 403

**可能原因**:
1. Token 没有被添加到请求头
2. Token 格式错误（缺少 "Bearer " 前缀）
3. Token 已过期

**检查方法**:
- 查看 OkHttp 日志，确认请求头包含 `Authorization: Bearer xxx`
- 在后端添加日志输出接收到的 Authorization 头

### Q3: Android 端解析 JSON 失败

**检查**:
- TokenResponse 的字段名是否匹配（accessToken vs access_token）
- Gson 是否正确配置

## 测试用例

### 完整的注册到访问图片流程

1. **启动应用**
   - 显示登录界面

2. **注册新账号**
   - 用户名：`testuser2`
   - 邮箱：`test2@example.com`
   - 密码：`Test123456`

3. **观察日志**
   ```
   AuthViewModel: Token saved: eyJ...
   AuthViewModel: Auth state set to Authenticated
   MainActivity: Auth state changed
   ImageViewModel: ImageViewModel created with token: present (eyJ...)
   ImageViewModel: Loading image list
   OkHttp: --> GET /api/images?page=1&pageSize=20
   OkHttp: Authorization: Bearer eyJ...
   OkHttp: <-- 200 OK
   ```

4. **预期结果**
   - ✅ 自动跳转到图片列表界面
   - ✅ 后端返回 200 OK
   - ✅ 显示图片列表（可能为空）

## 手动测试 Token

### 使用 curl 测试

1. **先注册获取 token**:
```bash
curl -X POST http://192.168.137.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser3","email":"test3@example.com","password":"Test123456"}'
```

复制返回的 `accessToken`

2. **使用 token 访问图片列表**:
```bash
curl -X GET "http://192.168.137.1:8000/api/images?page=1&pageSize=20" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

应该返回 200 OK 和图片列表（可能为空）。

## 如果问题仍然存在

### 方案A: 检查 SharedPreferences

添加调试代码：
```kotlin
val token = AuthManager.getToken(context)
Log.d("DEBUG", "Retrieved token from SharedPreferences: $token")
```

### 方案B: 强制重新创建 ImageViewModel

在 MainApp 中添加一个 key：
```kotlin
val imageViewModel = remember(authState, token) { 
    ImageViewModel(context)
}
```

### 方案C: 检查 NetworkModule

确认 AuthInterceptor 正确添加了 Authorization 头：
```kotlin
val authInterceptor = okhttp3.Interceptor { chain ->
    val token = AuthManager.getToken(context)
    Log.d("AuthInterceptor", "Adding token to request: $token")
    val request = chain.request().newBuilder()
        .addHeader("Authorization", "Bearer $token")
        .build()
    chain.proceed(request)
}
```

---

**最后更新**: 2026-01-21



