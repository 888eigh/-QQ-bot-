@echo off
chcp 65001 >nul
title QQ Bot - 一键打包为 .exe
cd /d "%~dp0"

echo ========================================
echo   QQ Bot - 一键打包为 .exe
echo ========================================
echo.

:: 检查 Python
echo [检查] Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

:: 安装项目依赖
echo [1/5] 安装项目依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
if errorlevel 1 (
    echo [警告] 清华源安装失败，尝试官方源...
    pip install -r requirements.txt
)
echo.

:: 安装 PyInstaller
echo [2/5] 安装 PyInstaller...
pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple/
if errorlevel 1 (
    pip install pyinstaller
)
echo.

:: 安装 websockets（uvicorn WebSocket 支持）
echo [3/5] 安装 WebSocket 支持...
pip install websockets -i https://pypi.tuna.tsinghua.edu.cn/simple/
echo.

:: 清理旧的打包文件
echo [4/5] 清理旧的打包文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.

:: 执行打包
echo [5/5] 开始打包（可能需要 1-3 分钟）...
pyinstaller qq_bot.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [错误] 打包失败！请查看上方错误信息。
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ✅ 打包完成！
echo   可执行文件: dist\QQBot.exe
echo ========================================
echo.
echo 使用方法:
echo   1. 将 dist\QQBot.exe 复制到任意目录
echo   2. 首次运行会自动生成 config/ logs/ data/ 目录
echo   3. 编辑 config\config.json 填入 API Key
echo   4. 配置 NapCat 反向 WebSocket 地址
echo   5. 双击 QQBot.exe 启动
echo.
echo 注意:
echo   - 打包后的 exe 只能在相同或更高版本的 Windows 上运行
echo   - 首次启动较慢，请耐心等待
echo   - 如遇杀毒软件误报，请添加信任
echo.
pause
