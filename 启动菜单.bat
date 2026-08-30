@echo off
chcp 65001 >nul
title QQ Bot 启动菜单
cd /d "%~dp0"

:menu
cls
echo ========================================
echo        QQ Bot 启动菜单
echo ========================================
echo.
echo   [1] 启动机器人（Bot）
echo   [2] 打开图形管理界面（GUI）
echo   [3] 启动机器人 + 图形界面
echo   [4] 退出
echo.
echo ========================================
set /p choice=请选择 (1-4): 

if "%choice%"=="1" goto start_bot
if "%choice%"=="2" goto start_gui
if "%choice%"=="3" goto start_both
if "%choice%"=="4" goto end
goto menu

:start_bot
echo.
echo 正在启动机器人...
call start.bat
goto end

:start_gui
echo.
echo 正在打开图形管理界面...
call 启动图形界面.bat
goto end

:start_both
echo.
echo 正在启动机器人和图形界面...
start "QQ Bot" cmd /k call start.bat
timeout /t 3 /nobreak >nul
call 启动图形界面.bat
goto end

:end
