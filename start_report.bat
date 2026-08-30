@echo off
chcp 65001 >nul
title QQ Bot 每小时报告守护进程
echo ========================================
echo   QQ Bot 每小时报告守护进程
echo ========================================
echo.
echo 每小时整点自动生成运行报告并发送到邮箱
echo 邮箱: backedcmd@163.com
echo.
echo 此窗口请保持开启，关闭则停止报告推送
echo ========================================
echo.

python report_daemon_windows.py

pause
