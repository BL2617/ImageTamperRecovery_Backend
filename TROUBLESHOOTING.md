# 问题排查指南

## 500 Internal Server Error - `/api/detection/compare`

### 可能的原因和解决方案

#### 1. 数据库表未创建
**问题**: `detection_results` 或 `tampered_blocks` 表不存在

**解决方案**:
```bash
cd ImageTamperRecovery_Backend
python migrate_add_detection_tables.py
```

或者确保 `main.py` 中的 `init_db()` 函数能正确创建所有表（包括检测相关的表）。

#### 2. created_at 字段序列化问题
**问题**: datetime 对象无法正确序列化为 JSON

**解决方案**: 已修复，`created_at` 字段现在会自动转换为 ISO 格式字符串。

#### 3. 图片文件路径问题
**问题**: 原图文件不存在或路径错误

**检查**:
- 确保原图已正确上传到服务器
- 检查 `UPLOAD_DIR` 配置是否正确
- 验证原图文件是否存在于指定路径

#### 4. 分块比对处理大量块时出错
**问题**: 如果图片很大，会产生大量块，可能导致内存或处理时间问题

**解决方案**: 
- 检查服务器日志，查看具体错误信息
- 可以尝试减小 `block_size` 参数
- 检查是否有足够的内存

### 调试步骤

1. **查看详细错误日志**:
   现在代码已经添加了详细的错误日志，检查后端控制台输出，会显示完整的错误堆栈。

2. **检查数据库**:
   ```bash
   sqlite3 image_tamper_recovery.db
   .tables
   # 应该看到 detection_results 和 tampered_blocks 表
   ```

3. **测试接口**:
   使用 curl 或 Postman 测试接口，查看详细错误信息：
   ```bash
   curl -X POST "http://localhost:8000/api/detection/compare" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "original_image_id=YOUR_IMAGE_ID" \
     -F "file=@test_image.jpg" \
     -F "block_size=64" \
     -F "threshold=0.1"
   ```

4. **检查文件权限**:
   确保服务器有权限读取原图文件和写入临时文件。

### 常见错误信息

- `原图不存在或无权限访问`: 检查原图ID是否正确，以及是否属于当前用户
- `原图文件不存在`: 检查文件是否在 `UPLOAD_DIR` 目录中
- `检测失败: ...`: 查看详细错误堆栈，定位具体问题

### 已修复的问题

✅ `created_at` 字段序列化问题 - 已修复，现在会自动转换为字符串
✅ 错误日志 - 已添加详细的错误堆栈输出

