# LSB检测问题修复说明

## 问题1：Seed must be between 0 and 2**32 - 1

### 问题描述
```
检测失败: Seed must be between 0 and 2**32 - 1
```

### 原因分析
- `numpy.random.seed()` 要求seed值必须在 0 到 2^32-1 之间
- 原代码使用 `int.from_bytes(key_hash[:8], 'big')` 可能生成超过32位的整数
- 使用全局的 `np.random.seed()` 可能影响其他代码

### 修复方案
修改 `app/utils/watermark.py` 中的 `generate_watermark_sequence` 函数：

**修改前：**
```python
seed = int.from_bytes(key_hash[:8], 'big')
np.random.seed(seed)
watermark = np.random.randint(0, 2, size=(height, width), dtype=np.uint8)
```

**修改后：**
```python
# 使用前4个字节（32位）来生成seed
seed = int.from_bytes(key_hash[:4], 'big') % (2**32)

# 创建新的随机数生成器，避免影响全局状态
rng = np.random.RandomState(seed)

# 生成随机水印位（0或1）
watermark = rng.randint(0, 2, size=(height, width), dtype=np.uint8)
```

**改进点：**
1. 使用前4个字节（32位）而不是8个字节
2. 使用 `% (2**32)` 确保seed在有效范围内
3. 使用 `RandomState` 而不是全局的 `np.random.seed()`，避免影响其他代码

---

## 问题2：可视化失败 - boolean index维度不匹配

### 问题描述
```
可视化失败: boolean index did not match indexed array along dimension 0; 
dimension is 2400 but corresponding boolean dimension is 1
```

### 原因分析
- 掩码可能是1维数组，但图片是2维的
- 掩码尺寸可能与图片尺寸不匹配
- 布尔索引时维度不匹配导致错误

### 修复方案
修改 `app/utils/watermark.py` 中的 `visualize_tampering` 函数：

**主要改进：**
1. **维度检查**：确保掩码是2维的
2. **尺寸匹配**：如果尺寸不匹配，自动调整掩码尺寸
3. **错误处理**：提供详细的错误信息

**关键代码：**
```python
# 确保掩码是二维的且尺寸匹配
if len(tamper_mask.shape) != 2:
    # 如果掩码是1维的，尝试重塑
    if len(tamper_mask.shape) == 1:
        if tamper_mask.size == height * width:
            tamper_mask = tamper_mask.reshape((height, width))
        else:
            raise ValueError(f"掩码尺寸不匹配")

# 确保掩码尺寸与图片匹配
if tamper_mask.shape != (height, width):
    # 使用PIL调整尺寸
    mask_pil = PILImage.fromarray((tamper_mask * 255).astype(np.uint8))
    mask_resized = mask_pil.resize((width, height), PILImage.NEAREST)
    tamper_mask = np.array(mask_resized) / 255.0
    tamper_mask = (tamper_mask > 0.5).astype(np.uint8)
```

---

## 问题3：可视化图片404错误

### 问题描述
```
INFO: 192.168.5.38:47496 - "GET /api/detection/visualization/bc464c42-54f4-4da4-9cf1-aca7bcb5f5cf HTTP/1.1" 404 Not Found
```

### 原因分析
- 可视化文件可能因为之前的错误而没有成功创建
- 路径存储或读取可能有问题

### 修复方案
修改 `app/services/lsb_detection.py` 中的 `detect_lsb_watermark` 函数：

**主要改进：**
1. **错误隔离**：可视化失败不影响检测结果
2. **文件验证**：创建后验证文件是否存在
3. **目录检查**：确保上传目录存在

**关键代码：**
```python
if save_visualization and tamper_mask is not None:
    try:
        vis_filename = f"lsb_vis_{uuid.uuid4()}.jpg"
        visualization_path_full = os.path.join(UPLOAD_DIR, vis_filename)
        
        # 确保目录存在
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # 生成可视化
        visualize_tampering(image_path, tamper_mask, visualization_path_full)
        
        # 验证文件是否成功创建
        if os.path.exists(visualization_path_full):
            visualization_path = vis_filename
        else:
            print(f"警告: 可视化文件创建失败")
    except Exception as vis_error:
        # 可视化失败不影响检测结果
        print(f"可视化生成失败: {str(vis_error)}")
        visualization_path = None
```

---

## 测试建议

### 测试LSB检测（空密钥）
```bash
curl -X POST "http://localhost:8000/api/detection/lsb" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_image.jpg" \
  -F "key="
```

### 测试LSB检测（有密钥）
```bash
curl -X POST "http://localhost:8000/api/detection/lsb" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_image.jpg" \
  -F "key=my_secret_key"
```

### 测试可视化图片
```bash
curl -X GET "http://localhost:8000/api/detection/visualization/{detection_result_id}" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output visualization.jpg
```

---

## 修复后的行为

1. **Seed问题**：
   - ✅ 不再出现 "Seed must be between 0 and 2**32 - 1" 错误
   - ✅ 使用独立的随机数生成器，不影响其他代码
   - ✅ 支持空密钥（空字符串）

2. **可视化问题**：
   - ✅ 自动处理掩码维度不匹配
   - ✅ 自动调整掩码尺寸以匹配图片
   - ✅ 提供详细的错误信息便于调试

3. **404错误**：
   - ✅ 可视化失败不影响检测结果
   - ✅ 文件创建后验证存在性
   - ✅ 提供清晰的错误提示

---

## 相关文件

- `app/utils/watermark.py` - 水印生成和检测函数
- `app/services/lsb_detection.py` - LSB检测服务
- `app/api/detection_api.py` - 检测API接口

---

## 注意事项

1. **空密钥**：
   - 空密钥会生成基于空字符串的固定哈希
   - 如果图片没有使用相同的空密钥嵌入水印，检测结果可能不准确
   - 建议用户使用非空密钥以获得更好的安全性

2. **掩码处理**：
   - 如果掩码维度或尺寸不匹配，系统会自动调整
   - 调整使用最近邻插值，保持掩码的离散性

3. **错误处理**：
   - 可视化失败不会导致整个检测失败
   - 检测结果仍然会返回，只是没有可视化图片


