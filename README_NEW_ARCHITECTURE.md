# 图片篡改检测定位与恢复系统 - V2 架构

## 🎯 新架构设计理念

### 核心改进

1. **本地备份，云端分发**
   - 原图备份存储在客户端本地，不在服务器
   - 服务器只存储带水印的图片（用于分发）
   - 提高安全性，降低泄露风险

2. **客户端优先**
   - 推荐在客户端嵌入水印和加密备份
   - 服务器提供可选的水印嵌入服务（兼容性）
   - 客户端工具支持离线操作

3. **灵活检测**
   - 可以检测任意来源的图片（不依赖服务器存储）
   - 支持验证下载的图片、传输的图片等
   - 适用于版权保护和证据保全场景

## 📋 应用场景

### 场景1：本地图片保护与云端分发验证（推荐）

```
1. 用户A在本地对原始图片嵌入水印（使用个人密钥）
2. 在本地加密备份原图（存储在本地或用户自己的云盘）
3. 将带水印的图片上传到公共平台/发送给他人

4. 用户B从平台下载/接收图片
5. 使用密钥验证图片是否被篡改
6. 查看篡改位置可视化

7. 用户A如果发现图片被篡改，使用本地备份恢复原始图片
```

### 场景2：版权保护/证据保全

```
1. 摄影师/创作者拍摄/创作图片后，立即嵌入水印
2. 本地加密备份原图
3. 将带水印的图片发布到平台（社交媒体、图库等）
4. 定期验证平台上的图片是否被恶意修改
5. 如果发现篡改，使用本地备份维权
```

### 场景3：重要文件传输验证

```
1. 发送方对重要图片嵌入水印并本地备份
2. 通过邮件/网盘等发送图片
3. 接收方接收后验证图片完整性
4. 如果被篡改，通知发送方恢复
```

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    本地端（客户端）                        │
├─────────────────────────────────────────────────────────┤
│ 1. 原始图片                                              │
│ 2. 嵌入水印（使用密钥）→ 带水印图片                      │
│ 3. 加密备份原图 → 备份文件（本地存储）                    │
│ 4. 上传带水印图片到服务器                                 │
└─────────────────────────────────────────────────────────┘
                        ↓ 上传
┌─────────────────────────────────────────────────────────┐
│                    服务器端                               │
├─────────────────────────────────────────────────────────┤
│ - 存储带水印的图片（用于分发）                            │
│ - 不存储备份（备份在用户本地）                            │
│ - 提供图片查询、下载服务                                  │
│ - 提供篡改检测服务                                        │
└─────────────────────────────────────────────────────────┘
                        ↓ 下载
┌─────────────────────────────────────────────────────────┐
│                    客户端/接收方                          │
├─────────────────────────────────────────────────────────┤
│ 5. 下载图片                                              │
│ 6. 使用密钥检测是否被篡改                                 │
│ 7. 查看篡改位置可视化                                     │
│ 8. 如果被篡改，使用本地备份恢复                           │
└─────────────────────────────────────────────────────────┘
```

## 🔧 数据库模型

### Image 表结构

```python
- id: 图片ID（主键）
- file_path: 带水印的图片路径（存储在服务器）
- thumbnail_path: 缩略图路径
- width, height: 图片尺寸
- size: 文件大小
- format: 图片格式
- category: 分类
- watermark_key_hash: 密钥哈希值（用于验证，不存储密钥本身）
- has_backup: 是否有本地备份（True/False，由客户端管理）
- created_at: 创建时间
```

**重要变化：**
- ❌ 移除 `original_backup_path`（备份不再存储在服务器）
- ✅ 添加 `has_backup`（标记是否有本地备份）
- ✅ `watermark_key_hash` 替代 `watermark_key`（更明确的命名）

## 📡 API 接口

### 1. 上传图片（支持两种模式）

```
POST /api/upload
Content-Type: multipart/form-data

参数：
- file: 图片文件（必需）
- mode: "client" 或 "server"（可选，默认"server"）
- category: 图片分类（可选）

模式1（mode="server"）：服务器嵌入水印
- key: 用户密钥（必需）

模式2（mode="client"）：客户端已嵌入水印（推荐）
- watermark_key_hash: 密钥的SHA256哈希值（必需）
- has_backup: 是否有本地备份（True/False）

响应：
{
  "code": 200,
  "message": "上传成功",
  "data": {
    "id": "图片ID",
    "url": "下载URL",
    "thumbnailUrl": "缩略图URL",
    "hasBackup": true/false,
    "mode": "client"/"server"
  }
}
```

### 2. 检测篡改（推荐：检测任意图片）

```
POST /api/detect
Content-Type: multipart/form-data

参数：
- file: 待检测的图片文件（可以是下载的图片）
- key: 用户密钥

响应：
{
  "code": 200,
  "message": "检测完成",
  "data": {
    "isTampered": true/false,
    "tamperRatio": 0.05,
    "tamperRatioPercent": 5.0,
    "visualization": "data:image/jpeg;base64,..."
  }
}
```

### 3. 检测服务器上的图片

```
POST /api/detect/{image_id}
Content-Type: application/x-www-form-urlencoded

参数：
- key: 用户密钥

响应：
{
  "code": 200,
  "message": "检测完成",
  "data": {
    "isTampered": true/false,
    "tamperRatio": 0.05,
    "tamperRatioPercent": 5.0,
    "visualizationUrl": "可视化图片URL"
  }
}
```

### 4. 获取可视化图片

```
GET /api/images/{image_id}/tamper-vis

返回：篡改位置可视化图片
```

## 🛠️ 客户端工具

### 1. 水印嵌入工具（推荐使用）

```bash
python client_watermark_tool.py <原始图片> <水印输出> <备份输出> <密钥>

示例：
python client_watermark_tool.py photo.jpg photo_wm.jpg photo_backup.enc my_key

输出：
- photo_wm.jpg: 带水印的图片（上传到服务器）
- photo_backup.enc: 加密的备份文件（保留在本地）
- 密钥哈希值（用于上传时验证）
```

### 2. 本地恢复工具

```bash
python client_recovery_tool.py <加密备份文件> <恢复输出> <密钥>

示例：
python client_recovery_tool.py photo_backup.enc recovered.jpg my_key

输出：
- recovered.jpg: 恢复的原始图片
```

## 📝 使用流程示例

### 流程1：客户端嵌入模式（推荐）

```python
# 1. 在客户端嵌入水印和备份
from client_watermark_tool import process_image_local

success, key_hash = process_image_local(
    "original.jpg",
    "watermarked.jpg",
    "backup.encrypted",
    "my_secret_key"
)

# 2. 上传带水印的图片到服务器
import requests
files = {"file": open("watermarked.jpg", "rb")}
data = {
    "mode": "client",
    "watermark_key_hash": key_hash,
    "has_backup": True,
    "category": "照片"
}
response = requests.post("http://server:8001/api/upload", files=files, data=data)

# 3. 从服务器下载图片后检测
files = {"file": open("downloaded.jpg", "rb")}
data = {"key": "my_secret_key"}
response = requests.post("http://server:8002/api/detect", files=files, data=data)

# 4. 如果被篡改，使用本地备份恢复
from client_recovery_tool import recover_image_local
recover_image_local("backup.encrypted", "recovered.jpg", "my_secret_key")
```

### 流程2：服务器嵌入模式（兼容性）

```python
# 1. 上传原图，服务器嵌入水印
import requests
files = {"file": open("original.jpg", "rb")}
data = {
    "mode": "server",
    "key": "my_secret_key",
    "category": "照片"
}
response = requests.post("http://server:8001/api/upload", files=files, data=data)

# 注意：此模式下，备份需要客户端自己处理
# 服务器不会存储备份（新架构）
```

## 🔒 安全性说明

1. **密钥安全**
   - 密钥不会存储在服务器
   - 只存储密钥的SHA256哈希值，用于验证
   - 密钥由用户自己保管

2. **备份安全**
   - 备份文件存储在客户端本地
   - 使用Fernet对称加密保护备份
   - 服务器不存储备份，降低泄露风险

3. **水印不可见**
   - LSB嵌入对图像质量影响极小
   - 人眼无法察觉水印存在
   - 适合版权保护和证据保全

## 🚀 启动服务

### 主服务（查询和下载）

```bash
python main.py
# 端口：8000
```

### 上传服务

```bash
python upload_image.py
# 端口：8001
```

### 检测服务

```bash
python tamper_detection.py
# 端口：8002
```

### 一键启动所有服务

```bash
# Windows
start_all_services.bat

# Linux/Mac
./start_all_services.sh
```

## 📊 对比：旧架构 vs 新架构

| 特性 | 旧架构 | 新架构 |
|------|--------|--------|
| 备份存储 | 服务器 | 客户端本地 ✅ |
| 安全性 | 中 | 高 ✅ |
| 应用场景 | 有限 | 广泛 ✅ |
| 逻辑合理性 | 较低 | 高 ✅ |
| 客户端工具 | 无 | 提供 ✅ |
| 离线支持 | 否 | 是 ✅ |

## 🎓 最佳实践

1. **优先使用客户端工具**
   - 在客户端嵌入水印和备份
   - 提高安全性，降低服务器负担

2. **妥善保管密钥和备份**
   - 密钥和备份文件不要丢失
   - 考虑使用云盘等安全存储备份

3. **定期验证图片**
   - 定期检测平台上的图片是否被篡改
   - 及时发现问题并采取措施

4. **备份策略**
   - 重要图片建议多个备份
   - 备份文件加密存储

## 📚 相关文档

- [API文档](README.md) - 详细的API接口说明
- [快速开始](QUICKSTART.md) - 快速上手指南
- [技术文档](README_TAMPER.md) - 技术实现细节

