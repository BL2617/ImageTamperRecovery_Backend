# 后端API接口文档

## 基础信息

- **Base URL**: `http://localhost:8000`
- **认证方式**: Bearer Token (JWT)
- **API文档**: `http://localhost:8000/docs` (Swagger UI)

---

## 一、认证相关接口 (`/api/auth`)

### 1.1 用户注册
```
POST /api/auth/register
Content-Type: application/json

Request Body:
{
  "username": "string",
  "email": "string",
  "password": "string",
  "device_id": "string (可选)"
}

Response:
{
  "access_token": "string",
  "token_type": "bearer",
  "user": {
    "id": "string",
    "username": "string",
    "email": "string",
    "is_active": true,
    "is_admin": false,
    "created_at": "datetime"
  }
}
```

### 1.2 用户登录
```
POST /api/auth/login
Content-Type: application/json

Request Body:
{
  "username": "string",
  "password": "string",
  "device_id": "string (可选)"
}

Response: 同注册接口
```

### 1.3 退出登录
```
POST /api/auth/logout
Headers: Authorization: Bearer {token}

Response:
{
  "code": 200,
  "message": "退出登录成功"
}
```

### 1.4 获取当前用户信息
```
GET /api/auth/me
Headers: Authorization: Bearer {token}

Response:
{
  "id": "string",
  "username": "string",
  "email": "string",
  "is_active": true,
  "is_admin": false,
  "created_at": "datetime"
}
```

### 1.5 获取操作日志
```
GET /api/auth/logs?page=1&page_size=20
Headers: Authorization: Bearer {token}

Response:
{
  "code": 200,
  "message": "获取成功",
  "data": [...],
  "total": 100,
  "page": 1,
  "pageSize": 20
}
```

---

## 二、图片管理接口 (`/api/images`)

### 2.1 获取图片列表
```
GET /api/images?page=1&pageSize=20&category=string(可选)
Headers: Authorization: Bearer {token}

Response:
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "images": [
      {
        "id": "string",
        "url": "string",
        "thumbnailUrl": "string",
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

### 2.2 获取单张图片信息
```
GET /api/images/{image_id}
Headers: Authorization: Bearer {token}

Response:
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "id": "string",
    "url": "string",
    "thumbnailUrl": "string",
    "width": 1920,
    "height": 1080,
    "size": 1024000,
    "format": "jpg",
    "timestamp": 1703779200000
  }
}
```

### 2.3 下载图片
```
GET /api/images/{image_id}/download
Headers: Authorization: Bearer {token}

Response: 图片二进制数据
```

### 2.4 获取缩略图
```
GET /api/images/{image_id}/thumbnail
(不需要登录)

Response: 缩略图二进制数据
```

### 2.5 上传图片
```
POST /api/upload
Content-Type: multipart/form-data
Headers: Authorization: Bearer {token}

Form Data:
- file: 图片文件
- category: string (可选)
- key: string (可选，水印密钥)
- encryptKey: string (可选，加密密钥)

Response:
{
  "code": 200,
  "message": "上传成功",
  "data": {
    "id": "string",
    "url": "string",
    "thumbnailUrl": "string",
    "width": 1920,
    "height": 1080,
    "size": 1024000,
    "format": "jpg",
    "timestamp": 1703779200000
  }
}
```

---

## 三、检测相关接口 (`/api/detection`)

### 3.1 LSB水印检测（方式1）
```
POST /api/detection/lsb
Content-Type: multipart/form-data
Headers: Authorization: Bearer {token}

Form Data:
- file: 待检测的图片文件
- key: 用户密钥（用于生成和验证水印）

Response:
{
  "code": 200,
  "message": "检测完成",
  "data": {
    "id": "string",
    "detection_type": "lsb",
    "original_image_id": null,
    "detected_image_id": null,
    "is_tampered": true,
    "tamper_ratio": "0.1234",
    "tamper_ratio_percent": 12.34,
    "confidence": null,
    "tampered_regions": [
      {
        "x": 0,
        "y": 0,
        "width": 1920,
        "height": 1080,
        "confidence": 0.1234
      }
    ],
    "visualization_url": "string",
    "created_at": "datetime"
  }
}
```

### 3.2 分块比对检测（方式2）
```
POST /api/detection/compare
Content-Type: multipart/form-data
Headers: Authorization: Bearer {token}

Form Data:
- original_image_id: 原图ID（从已上传的图片列表中选择）
- file: 待检测的图片文件
- block_size: int (默认64)
- threshold: float (默认0.1，差异阈值)

Response:
{
  "code": 200,
  "message": "检测完成",
  "data": {
    "id": "string",
    "detection_type": "compare",
    "original_image_id": "string",
    "detected_image_id": null,
    "is_tampered": true,
    "tamper_ratio": "0.1234",
    "tamper_ratio_percent": 12.34,
    "confidence": null,
    "tampered_regions": [...],
    "visualization_url": "string",
    "created_at": "datetime"
  },
  "blocks": [
    {
      "block_index": 0,
      "x": 0,
      "y": 0,
      "width": 64,
      "height": 64,
      "is_tampered": true,
      "difference_ratio": 0.15
    }
  ]
}
```

### 3.3 模型检测（方式3）
```
POST /api/detection/model
Content-Type: multipart/form-data
Headers: Authorization: Bearer {token}

Form Data:
- file: 待检测的图片文件
- confidence_threshold: float (默认0.5)

Response:
{
  "code": 200,
  "message": "检测完成",
  "data": {
    "id": "string",
    "detection_type": "model",
    "original_image_id": null,
    "detected_image_id": null,
    "is_tampered": true,
    "tamper_ratio": "0.1234",
    "tamper_ratio_percent": 12.34,
    "confidence": "0.1234",
    "tampered_regions": [...],
    "visualization_url": "string",
    "created_at": "datetime"
  }
}
```

### 3.4 获取可视化图片
```
GET /api/detection/visualization/{detection_result_id}
Headers: Authorization: Bearer {token}

Response: 标注了篡改区域的可视化图片（二进制数据）
```

---

## 四、恢复相关接口 (`/api/recovery`)

### 4.1 获取被篡改的块信息
```
GET /api/recovery/blocks/{detection_result_id}
Headers: Authorization: Bearer {token}

Response:
{
  "code": 200,
  "message": "获取成功",
  "data": [
    {
      "block_index": 0,
      "x": 0,
      "y": 0,
      "width": 64,
      "height": 64,
      "has_original_data": true
    }
  ]
}
```

### 4.2 恢复被篡改的块
```
POST /api/recovery/restore-blocks
Content-Type: application/json
Headers: Authorization: Bearer {token}

Request Body:
{
  "detection_result_id": "string",
  "block_indices": [0, 1, 2]
}

Response:
{
  "code": 200,
  "message": "获取恢复数据成功",
  "data": [
    {
      "block_index": 0,
      "x": 0,
      "y": 0,
      "width": 64,
      "height": 64,
      "block_data": "base64编码的PNG数据"
    }
  ]
}
```

---

## 错误响应格式

所有接口在出错时返回：
```json
{
  "detail": "错误信息"
}
```

常见HTTP状态码：
- `200`: 成功
- `400`: 请求参数错误
- `401`: 未授权（需要登录）
- `403`: 无权限
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 使用示例

### 完整流程示例：上传图片并检测

1. **登录**
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'
```

2. **上传图片**
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -H "Authorization: Bearer {token}" \
  -F "file=@image.jpg" \
  -F "category=测试"
```

3. **LSB检测**
```bash
curl -X POST "http://localhost:8000/api/detection/lsb" \
  -H "Authorization: Bearer {token}" \
  -F "file=@test_image.jpg" \
  -F "key=my_secret_key"
```

4. **分块比对检测**
```bash
curl -X POST "http://localhost:8000/api/detection/compare" \
  -H "Authorization: Bearer {token}" \
  -F "original_image_id={image_id}" \
  -F "file=@test_image.jpg" \
  -F "block_size=64" \
  -F "threshold=0.1"
```

5. **模型检测**
```bash
curl -X POST "http://localhost:8000/api/detection/model" \
  -H "Authorization: Bearer {token}" \
  -F "file=@test_image.jpg" \
  -F "confidence_threshold=0.5"
```

