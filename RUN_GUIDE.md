# 后端服务运行指南

## 一、启动后端服务

### 方式1：使用批处理脚本（推荐，Windows）

#### 启动所有服务（一键启动）
```bash
# 双击运行或在命令行执行
start_all_services.bat
```

这会启动三个服务，每个服务在独立的命令行窗口中运行：
- **主服务**：端口 8000 - 图像查询和下载
- **上传服务**：端口 8001 - 图像上传
- **检测服务**：端口 8002 - 篡改检测

#### 单独启动服务
```bash
# 启动主服务
start_server.bat

# 启动上传服务
start_upload.bat

# 启动检测服务（需要手动运行）
python tamper_detection.py
```

### 方式2：手动启动（跨平台）

#### 1. 安装依赖
```bash
cd ImageTamperRecovery_Backend
pip install -r requirements.txt
```

#### 2. 启动服务

**终端1 - 主服务（端口8000）**
```bash
python main.py
```

**终端2 - 上传服务（端口8001）**
```bash
python upload_image.py
```

**终端3 - 检测服务（端口8002）**
```bash
python tamper_detection.py
```

### 方式3：使用uvicorn（生产环境推荐）

```bash
# 主服务
uvicorn main:app --host 0.0.0.0 --port 8000

# 上传服务
uvicorn upload_image:app --host 0.0.0.0 --port 8001

# 检测服务
uvicorn tamper_detection:app --host 0.0.0.0 --port 8002
```

## 二、获取电脑IP地址（用于安卓设备连接）

### Windows系统

#### 方法1：使用命令行
```bash
# 打开命令提示符（CMD）或PowerShell，执行：
ipconfig

# 查找"无线局域网适配器 WLAN"或"以太网适配器"下的"IPv4 地址"
# 例如：192.168.137.1 或 192.168.0.103
```

#### 方法2：查看网络设置
1. 打开"设置" → "网络和Internet" → "WLAN" 或 "以太网"
2. 点击当前连接的网络
3. 查看"IPv4 地址"

#### 方法3：如果使用热点
1. 打开"设置" → "网络和Internet" → "移动热点"
2. 查看"网络名称"和"网络密码"
3. 在命令提示符中执行 `ipconfig`，查找"本地连接"或"无线局域网适配器 本地连接*"下的IP地址
4. **热点IP通常是 192.168.137.1**（Windows默认热点IP）

### Linux/Mac系统
```bash
# Linux
ip addr show
# 或
ifconfig

# Mac
ifconfig | grep "inet "
```

## 三、配置安卓端BaseURI

### 1. 获取电脑IP地址
假设你的电脑热点IP是：`192.168.137.1`

### 2. 修改安卓端配置

打开文件：`undergraduate-grad-project/TamperRecovery/app/src/main/java/com/bl2617/tamperrecovery/network/NetworkModule.kt`

修改 `BASE_URL`：
```kotlin
// 将原来的
private const val BASE_URL = "http://192.168.0.103:8000/"

// 改为你的电脑IP（热点IP）
private const val BASE_URL = "http://192.168.137.1:8000/"
```

**注意**：
- 确保IP地址正确（使用上面获取的IP）
- 端口号要与后端服务端口一致（主服务是8000）
- URL末尾必须有斜杠 `/`

### 3. 配置多个服务端口（如果需要）

如果你的服务分别运行在不同端口，需要配置：

```kotlin
object NetworkModule {
    // 主服务（图像查询、下载）
    private const val BASE_URL = "http://192.168.137.1:8000/"
    
    // 上传服务（如果需要单独配置）
    private const val UPLOAD_BASE_URL = "http://192.168.137.1:8001/"
    
    // 检测服务（如果需要单独配置）
    private const val DETECT_BASE_URL = "http://192.168.137.1:8002/"
    
    // ... 其他代码
}
```

## 四、验证连接

### 1. 检查后端服务是否运行
在浏览器中访问：
- http://192.168.137.1:8000/docs （主服务API文档）
- http://192.168.137.1:8001/docs （上传服务API文档）
- http://192.168.137.1:8002/docs （检测服务API文档）

如果能打开Swagger文档页面，说明服务运行正常。

### 2. 检查防火墙设置

**Windows防火墙**：
1. 打开"Windows Defender 防火墙"
2. 点击"高级设置"
3. 选择"入站规则" → "新建规则"
4. 选择"端口" → 下一步
5. 选择"TCP"，输入端口：`8000, 8001, 8002`
6. 选择"允许连接"
7. 应用到所有配置文件

或者临时关闭防火墙进行测试。

### 3. 在安卓设备上测试
1. 确保安卓设备连接到电脑的热点
2. 在安卓设备上打开浏览器，访问：`http://192.168.137.1:8000/`
3. 如果能看到API信息，说明网络连接正常

## 五、常见问题

### 问题1：安卓设备无法连接后端
**解决方案**：
- 检查电脑和手机是否在同一网络（热点）
- 检查防火墙是否允许端口访问
- 检查IP地址是否正确
- 尝试在手机浏览器中直接访问 `http://IP:8000/`

### 问题2：连接超时
**解决方案**：
- 检查后端服务是否正在运行
- 检查端口是否被占用：`netstat -ano | findstr :8000`
- 尝试重启后端服务

### 问题3：IP地址经常变化
**解决方案**：
- 在Windows热点设置中，可以设置固定的IP地址
- 或者使用环境变量配置BASE_URL，方便修改

### 问题4：端口冲突
**解决方案**：
- 检查端口占用：`netstat -ano | findstr :8000`
- 修改 `config.py` 中的端口配置
- 或使用环境变量：`set PORT=8000`

## 六、环境变量配置（可选）

### Windows
```bash
# 设置BASE_URL
set BASE_URL=http://192.168.137.1:8000

# 设置端口
set PORT=8000

# 然后启动服务
python main.py
```

### Linux/Mac
```bash
export BASE_URL=http://192.168.137.1:8000
export PORT=8000
python main.py
```

## 七、快速测试命令

### 测试主服务
```bash
curl http://192.168.137.1:8000/
```

### 测试上传服务
```bash
curl http://192.168.137.1:8001/
```

### 测试检测服务
```bash
curl http://192.168.137.1:8002/
```

## 八、生产环境部署建议

1. **使用HTTPS**：参考 `HTTPS_CONFIG.md`
2. **使用反向代理**：Nginx或Apache
3. **配置环境变量**：不要硬编码IP地址
4. **使用域名**：配置DNS解析
5. **监控和日志**：配置日志系统





