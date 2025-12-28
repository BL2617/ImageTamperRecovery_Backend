# 图片传输后端 API

这是一个基于 FastAPI 的图片传输后端服务，为 Android 客户端提供图片查询和下载功能。

## 功能特性

- ✅ 获取单张图片信息（通过ID）
- ✅ 获取图片列表（支持分页和分类筛选）
- ✅ 下载图片（通过ID）
- ✅ 获取缩略图
- ✅ 图片上传功能（用于测试和初始化数据）
- ✅ SQLite 数据库存储图片元数据
- ✅ 本地文件系统存储图片文件

## 项目结构

```
ImageTamperRecovery_Backend/
├── main.py              # 主应用文件（提供查询和下载API）
├── upload_image.py      # 图片上传服务（用于测试）
├── models.py            # 数据模型定义
├── database.py          # 数据库操作
├── config.py            # 配置文件
├── requirements.txt     # Python依赖
├── README.md            # 项目说明
├── uploads/             # 图片存储目录（自动创建）
│   └── thumbnails/      # 缩略图存储目录（自动创建）
└── image_tamper_recovery.db  # SQLite数据库文件（自动创建）
```

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行主服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 3. 运行上传服务（可选，用于测试）

```bash
python upload_image.py
```

上传服务将在 `http://localhost:8001` 启动。

## API 接口

### 1. 获取单张图片信息

```
GET /api/images/{image_id}
```

**响应示例：**
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "id": "abc123",
    "url": "http://localhost:8000/api/images/abc123/download",
    "thumbnailUrl": "http://localhost:8000/api/images/abc123/thumbnail",
    "width": 1920,
    "height": 1080,
    "size": 1024000,
    "format": "jpg",
    "timestamp": 1703779200000
  }
}
```

### 2. 获取图片列表

```
GET /api/images?page=1&pageSize=20&category=风景
```

**查询参数：**
- `page`: 页码，从1开始（默认：1）
- `pageSize`: 每页数量（默认：20，最大：100）
- `category`: 图片分类（可选）

**响应示例：**
```json
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "images": [
      {
        "id": "abc123",
        "url": "http://localhost:8000/api/images/abc123/download",
        "thumbnailUrl": "http://localhost:8000/api/images/abc123/thumbnail",
        "width": 1920,
        "height": 1080,
        "size": 1024000,
        "format": "jpg",
        "timestamp": 1703779200000
      }
    ],
    "total": 100,
    "page": 1,
    "pageSize": 20
  }
}
```

### 3. 下载图片

```
GET /api/images/{image_id}/download
```

返回图片的二进制数据。

### 4. 获取缩略图

```
GET /api/images/{image_id}/thumbnail
```

返回缩略图的二进制数据。

### 5. 上传图片（测试用）

```
POST /api/upload
Content-Type: multipart/form-data

file: [图片文件]
category: [可选，图片分类]
```

**响应示例：**
```json
{
  "code": 200,
  "message": "上传成功",
  "data": {
    "id": "abc123",
    "url": "http://localhost:8000/api/images/abc123/download",
    "thumbnailUrl": "http://localhost:8000/api/images/abc123/thumbnail",
    "width": 1920,
    "height": 1080,
    "size": 1024000,
    "format": "jpg"
  }
}
```

## API 文档

启动服务后，可以访问以下地址查看自动生成的 API 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 数据库

项目使用 SQLite 数据库存储图片元数据。数据库文件 `image_tamper_recovery.db` 会在首次运行时自动创建。

**images 表结构：**
- `id`: 图片ID（主键）
- `file_path`: 文件存储路径
- `thumbnail_path`: 缩略图路径
- `width`: 图片宽度
- `height`: 图片高度
- `size`: 文件大小（字节）
- `format`: 图片格式
- `category`: 图片分类
- `created_at`: 创建时间

## 配置

可以通过环境变量或修改 `config.py` 来配置：

- `HOST`: 服务器主机（默认：0.0.0.0）
- `PORT`: 服务器端口（默认：8000）
- `BASE_URL`: API基础URL（用于生成图片URL）
- `UPLOAD_DIR`: 图片存储目录（默认：uploads）
- `MAX_FILE_SIZE`: 最大文件大小（默认：10MB）

## 注意事项

1. 生产环境建议：
   - 修改 CORS 配置，限制允许的域名
   - 使用更安全的数据库（如 PostgreSQL）
   - 配置 HTTPS
   - 添加身份验证和授权
   - 设置合适的文件大小限制

2. 图片存储：
   - 原图存储在 `uploads/` 目录
   - 缩略图存储在 `uploads/thumbnails/` 目录
   - 数据库只存储文件路径和元数据，不存储二进制数据

3. 支持的图片格式：
   - JPG/JPEG
   - PNG
   - GIF
   - WebP
   - BMP

## 开发

### 添加新功能

1. 在 `models.py` 中定义数据模型
2. 在 `database.py` 中添加数据库操作
3. 在 `main.py` 中添加 API 路由

### 测试

可以使用以下工具测试 API：
- Postman
- curl
- Swagger UI（访问 `/docs`）

## 许可证

MIT License

