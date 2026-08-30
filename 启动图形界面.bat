@echo off
chcp 65001 >nul
title QQ Bot 图形管理界面
cd /d "%~dp0"

echo ========================================
echo   正在启动 QQ Bot 图形管理界面...
echo ========================================
echo.

python gui\app.py

if errorlevel 1 (
    echo.
    echo 启动失败，请检查 Python 是否已安装
    pause
)
