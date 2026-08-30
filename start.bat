@echo off
chcp 65001 >nul
title QQ Bot 启动器
echo ========================================
echo   QQ Bot 启动器
echo ========================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

:: 检查依赖
echo [1/3] 检查依赖...
python -c "import nonebot" >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖，请稍候...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
)

:: 检查配置
echo [2/3] 检查配置...
if not exist "config\config.json" (
    echo [错误] 配置文件不存在
    pause
    exit /b 1
)

:: 启动Bot
echo [3/3] 启动 Bot...
echo.
echo ========================================
echo   Bot 启动中，请勿关闭此窗口
echo   WebSocket: ws://127.0.0.1:8081/onebot/v11/ws
echo ========================================
echo.

python bot.py

pause
