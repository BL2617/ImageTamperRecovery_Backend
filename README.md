# 图像篡改检测与恢复系统 - 后端

## 系统概述

本系统提供完整的图像篡改检测与恢复功能，包括账号系统、图像管理、篡改定位与恢复、安全防护等核心模块。

## 主要功能模块

### 1. 账号系统
- 用户注册、登录、退出登录
- JWT Token认证
- 跨设备数据同步（通过设备ID）
- 操作日志记录
- 后台管理功能（管理员）

### 2. 图像管理
- 图像上传（支持水印嵌入）
- 本地存储和云端存储
- AES加密存储
- 图像列表查询（分页、分类筛选）
- 图像下载

### 3. 篡改定位与恢复
- **有原图情况**：
  - 轻量化传统图像篡改定位检测算法（LSB水印）
  - 增量传输（仅传输篡改区域数据）
  - 局部恢复技术
- **无原图情况**：
  - PSCC-Net模型盲检测（暂未实现）

### 4. 安全防护
- HTTPS安全协议（支持配置）
- AES对称加密算法（本地和云端存储）
- JWT Token认证
- 密码加密存储（bcrypt）

## 技术栈

- **框架**: FastAPI
- **数据库**: SQLite（可扩展为PostgreSQL/MySQL）
- **ORM**: SQLAlchemy
- **认证**: JWT (python-jose)
- **加密**: cryptography (Fernet/AES)
- **图像处理**: Pillow, NumPy

## 项目结构

```
ImageTamperRecovery_Backend/
├── main.py                 # 主应用（图像查询和下载）
├── upload_image.py          # 图像上传服务
├── tamper_detection.py      # 篡改检测服务
├── app/                     # 应用主包
│   ├── api/                 # API路由
│   │   ├── __init__.py
│   │   └── auth_api.py      # 账号系统API
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   └── models.py        # 所有数据模型定义
│   ├── services/            # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── user_service.py  # 用户服务
│   │   └── image_service.py # 图像服务
│   └── utils/               # 工具类
│       ├── __init__.py
│       ├── auth.py          # 认证工具
│       ├── config.py        # 配置文件
│       ├── database.py      # 数据库操作
│       ├── encryption.py    # 加密工具
│       └── watermark.py    # 水印算法
├── client_watermark_tool.py # 客户端水印工具示例
├── client_recovery_tool.py  # 客户端恢复工具示例
├── upload_image_client.py   # 上传客户端工具
├── migrate_db.py            # 数据库迁移脚本
├── migrate_to_v2.py         # V2迁移脚本
├── requirements.txt         # 依赖列表
├── README.md                # 项目说明
├── HTTPS_CONFIG.md          # HTTPS配置说明
└── QUICKSTART.md            # 快速开始指南
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

编辑 `config.py` 或设置环境变量：
- `BASE_URL`: API基础URL
- `DATABASE_URL`: 数据库连接字符串
- `SECRET_KEY`: JWT密钥（生产环境必须修改）

### 3. 启动服务

#### 方式1：分别启动各个服务

```bash
# 主服务（图像查询和下载）
python main.py

# 上传服务
python upload_image.py

# 检测服务
python tamper_detection.py
```

#### 方式2：使用批处理脚本（Windows）

```bash
start_all_services.bat
```

### 4. API文档

启动服务后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API接口

### 账号系统 (`/api/auth`)

- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 退出登录
- `GET /api/auth/me` - 获取当前用户信息
- `GET /api/auth/logs` - 获取操作日志

### 图像管理 (`/api/images`)

- `GET /api/images` - 获取图像列表（需要登录）
- `GET /api/images/{image_id}` - 获取图像信息（需要登录）
- `GET /api/images/{image_id}/download` - 下载图像（需要登录）
- `GET /api/images/{image_id}/thumbnail` - 获取缩略图

### 图像上传 (`/api/upload`)

- `POST /api/upload` - 上传图像（需要登录）
  - 支持参数：
    - `file`: 图像文件
    - `category`: 分类（可选）
    - `key`: 水印密钥（可选）
    - `encrypt_key`: 加密密钥（可选）

### 篡改检测 (`/api/detect`)

- `POST /api/detect` - 检测图像篡改（需要登录）
- `POST /api/detect/{image_id}` - 检测服务器上的图像（需要登录）
- `POST /api/images/{image_id}/incremental-transfer` - 增量传输（需要登录）
- `POST /api/images/{image_id}/recover-region` - 局部恢复（需要登录）

## 安全配置

### HTTPS配置

详见 `HTTPS_CONFIG.md`

### 加密存储

- 使用AES对称加密算法
- 密钥派生使用PBKDF2（100,000次迭代）
- 支持本地和云端加密存储

## 数据库模型

### User（用户）
- id, username, email, hashed_password
- is_active, is_admin
- device_id（用于跨设备同步）

### Image（图像）
- id, user_id, file_path, thumbnail_path
- width, height, size, format, category
- watermark_key_hash, has_backup
- encrypted_data（AES加密数据）
- created_at

### OperationLog（操作日志）
- id, user_id, operation_type, operation_desc
- image_id, ip_address, device_info
- created_at

## 开发说明

### 添加新功能

1. 在 `models.py` 中定义数据模型
2. 在 `database.py` 中添加数据库操作
3. 在相应的服务文件中添加业务逻辑
4. 在API文件中添加路由

### 测试

使用Postman或curl测试API，或参考 `client_watermark_tool.py` 和 `client_recovery_tool.py` 中的示例。

## 许可证

MIT License
