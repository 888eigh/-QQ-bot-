@echo off
REM run.bat: 在 Windows 上启动前先检查并安装 Python 依赖（使用当前系统的 python）
python scripts\check_requirements.py
if %ERRORLEVEL% NEQ 0 (
  echo 依赖检查或安装返回错误，按任意键继续或关闭...
  pause
)
nREM 如果存在已打包的 exe，优先运行 exe
if exist dist\QQ-bot.exe (
  echo 发现 dist\QQ-bot.exe，优先运行该可执行文件
  start "QQ-bot" "dist\QQ-bot.exe" %*
  goto :eof
)
nREM 否则用当前 python 解释器直接运行项目
python main.py %*
