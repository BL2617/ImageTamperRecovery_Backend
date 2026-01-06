@echo off
echo 启动所有后端服务...
echo.

echo [1/3] 启动主服务 (端口 8000)...
start "主服务" cmd /k "python main.py"

timeout /t 2 /nobreak >nul

echo [2/3] 启动上传服务 (端口 8001)...
start "上传服务" cmd /k "python upload_image.py"

timeout /t 2 /nobreak >nul

echo [3/3] 启动检测服务 (端口 8002)...
start "检测服务" cmd /k "python tamper_detection.py"

echo.
echo 所有服务已启动！
echo 主服务: http://localhost:8000
echo 上传服务: http://localhost:8001
echo 检测服务: http://localhost:8002
echo.
pause



