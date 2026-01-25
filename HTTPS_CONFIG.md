# HTTPS配置说明

## 概述

为了保障数据传输安全，系统支持HTTPS协议。以下是配置HTTPS的说明。

## 方式1：使用uvicorn的SSL配置

### 生成SSL证书

```bash
# 使用openssl生成自签名证书（仅用于开发测试）
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

### 配置uvicorn使用HTTPS

修改启动脚本，添加SSL配置：

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem"
    )
```

## 方式2：使用反向代理（推荐生产环境）

### Nginx配置示例

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 方式3：使用环境变量配置

在`.env`文件中配置：

```env
SSL_KEYFILE=key.pem
SSL_CERTFILE=cert.pem
USE_HTTPS=true
```

在代码中读取：

```python
import os
from dotenv import load_dotenv

load_dotenv()

ssl_keyfile = os.getenv("SSL_KEYFILE")
ssl_certfile = os.getenv("SSL_CERTFILE")
use_https = os.getenv("USE_HTTPS", "false").lower() == "true"

if use_https and ssl_keyfile and ssl_certfile:
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile
    )
else:
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 注意事项

1. **生产环境**：必须使用由受信任的CA签发的证书（如Let's Encrypt）
2. **自签名证书**：仅用于开发测试，客户端会显示安全警告
3. **证书更新**：定期更新SSL证书，避免过期
4. **安全配置**：使用强加密算法（TLS 1.2+），禁用弱加密协议

## Android客户端配置

在Android应用中，需要配置网络安全策略以支持HTTPS：

1. 在`AndroidManifest.xml`中配置：
```xml
<application
    android:networkSecurityConfig="@xml/network_security_config"
    ...>
```

2. 在`res/xml/network_security_config.xml`中：
```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">your-domain.com</domain>
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </domain-config>
</network-security-config>
```





