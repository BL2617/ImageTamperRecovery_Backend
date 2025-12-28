# 快速开始指南

## 1. 安装依赖

```bash
pip install -r requirements.txt
```

## 2. 启动主服务

```bash
python main.py
```

或者使用批处理文件（Windows）：
```bash
start_server.bat
```

服务将在 `http://localhost:8000` 启动。

## 3. 访问 API 文档

打开浏览器访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 4. 上传测试图片（可选）

启动上传服务（在另一个终端）：
```bash
python upload_image.py
```

或者使用批处理文件：
```bash
start_upload.bat
```

上传服务将在 `http://localhost:8001` 启动。

然后使用以下方式上传图片：

### 使用 curl：
```bash
curl -X POST "http://localhost:8001/api/upload" \
  -F "file=@your_image.jpg" \
  -F "category=测试"
```

### 使用 Python 脚本：
```python
import requests

url = "http://localhost:8001/api/upload"
files = {"file": open("your_image.jpg", "rb")}
data = {"category": "测试"}

response = requests.post(url, files=files, data=data)
print(response.json())
```

## 5. 测试 API

运行测试脚本：
```bash
python test_api.py
```

## 6. 配置 Android 客户端

在 Android 项目的 `NetworkModule.kt` 中，将 `BASE_URL` 修改为：
```kotlin
private const val BASE_URL = "http://your-server-ip:8000/"
```

如果 Android 设备和服务端在同一网络，可以使用：
- 本地网络 IP（如：`http://192.168.1.100:8000/`）
- 或者使用 `10.0.2.2`（Android 模拟器访问本地主机的特殊地址）

## 常见问题

### 1. 端口被占用
如果 8000 端口被占用，可以修改 `config.py` 中的 `PORT` 配置。

### 2. 跨域问题
如果遇到跨域问题，检查 `main.py` 中的 CORS 配置。

### 3. 图片无法下载
确保 `uploads/` 目录存在，并且有读取权限。

### 4. 数据库错误
删除 `image_tamper_recovery.db` 文件，重新启动服务会自动创建新的数据库。

## 下一步

- 查看 `README.md` 了解完整的 API 文档
- 根据需要修改 `config.py` 中的配置
- 添加身份验证和授权（生产环境必需）
- 配置 HTTPS（生产环境推荐）

