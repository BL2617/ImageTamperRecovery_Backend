# 快速启动指南

## 一、启动后端服务（3个步骤）

### 步骤1：安装依赖
```bash
cd ImageTamperRecovery_Backend
pip install -r requirements.txt
```

### 步骤2：启动所有服务
**Windows用户**：双击 `start_all_services.bat`

**或手动启动**（需要3个终端窗口）：
```bash
# 终端1
python main.py

# 终端2  
python upload_image.py

# 终端3
python tamper_detection.py
```

### 步骤3：验证服务运行
在浏览器访问：http://localhost:8000/docs

## 二、配置安卓端连接

### 1. 获取电脑IP地址

**如果使用热点连接**：
- Windows热点默认IP通常是：`192.168.137.1`
- 在命令行执行 `ipconfig`，查找"本地连接"下的IPv4地址

**如果使用同一WiFi**：
- 在命令行执行 `ipconfig`
- 查找"无线局域网适配器 WLAN"下的IPv4地址
- 例如：`192.168.0.103` 或 `192.168.1.100`

### 2. 修改安卓端BaseURL

打开文件：
```
undergraduate-grad-project/TamperRecovery/app/src/main/java/com/bl2617/tamperrecovery/network/NetworkModule.kt
```

修改第22行的 `BASE_URL`：
```kotlin
// 热点连接（推荐）
private const val BASE_URL = "http://192.168.137.1:8000/"

// 或同一WiFi连接
private const val BASE_URL = "http://192.168.0.103:8000/"
```

**重要提示**：
- 将 `192.168.137.1` 替换为你实际的IP地址
- URL末尾必须有斜杠 `/`
- 端口号 `8000` 要与后端主服务端口一致

### 3. 配置防火墙（重要！）

**Windows防火墙设置**：
1. 打开"Windows Defender 防火墙"
2. 点击"高级设置"
3. 选择"入站规则" → "新建规则"
4. 选择"端口" → 下一步
5. 选择"TCP"，输入端口：`8000, 8001, 8002`
6. 选择"允许连接" → 完成

**或临时关闭防火墙测试**（不推荐）

## 三、测试连接

### 1. 在电脑上测试
```bash
# 测试主服务
curl http://localhost:8000/

# 测试上传服务
curl http://localhost:8001/

# 测试检测服务
curl http://localhost:8002/
```

### 2. 在安卓设备上测试
1. 确保设备连接到电脑热点或同一WiFi
2. 在设备浏览器访问：`http://192.168.137.1:8000/`
3. 如果能看到API信息，说明连接成功

## 四、常见问题排查

### ❌ 问题：安卓设备无法连接
**检查清单**：
- [ ] 后端服务是否正在运行？
- [ ] 电脑和手机是否在同一网络？
- [ ] 防火墙是否允许端口访问？
- [ ] IP地址是否正确？
- [ ] URL末尾是否有斜杠 `/`？

### ❌ 问题：连接超时
**解决方案**：
```bash
# 检查端口是否被占用
netstat -ano | findstr :8000

# 如果被占用，修改端口或关闭占用进程
```

### ❌ 问题：IP地址找不到
**解决方案**：
```bash
# Windows
ipconfig

# 查找"IPv4 地址"，通常热点是 192.168.137.1
```

## 五、服务端口说明

| 服务 | 端口 | 功能 |
|------|------|------|
| 主服务 | 8000 | 图像查询、下载、账号系统 |
| 上传服务 | 8001 | 图像上传 |
| 检测服务 | 8002 | 篡改检测、增量传输、局部恢复 |

## 六、完整示例

假设你的电脑IP是 `192.168.137.1`（热点）：

1. **启动后端**：
   ```bash
   # 双击 start_all_services.bat
   # 或手动启动3个服务
   ```

2. **修改安卓端**：
   ```kotlin
   private const val BASE_URL = "http://192.168.137.1:8000/"
   ```

3. **测试连接**：
   - 手机浏览器访问：`http://192.168.137.1:8000/`
   - 应该能看到API信息

4. **运行安卓应用**：
   - 编译并运行安卓应用
   - 应该能正常连接后端

## 七、详细文档

更多详细信息请参考：
- `RUN_GUIDE.md` - 完整运行指南
- `README.md` - 项目说明文档
- `HTTPS_CONFIG.md` - HTTPS配置（生产环境）





