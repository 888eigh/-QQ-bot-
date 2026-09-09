@echo off
REM build_exe.bat: 使用 PyInstaller 生成 Windows 可执行文件（单文件或单文件夹模式视需求）
REM 使用前请确保已安装 Python 3.10+ 并激活虚拟环境（可选）
necho 安装/升级 PyInstaller...
%CD%\venv\Scripts\python -m pip install --upgrade pyinstaller 2>NUL || python -m pip install --upgrade pyinstaller
necho 生成可执行文件（onefile）...
REM 注意：根据项目资源路径调整 --add-data 参数 (src;dest 用分号分隔)
pyinstaller --onefile --name "QQ-bot" \
  --add-data "config;config" \
  --add-data "data;data" \
  --add-data "logs;logs" \
  main.py
necho 构建完成，输出位于 dist\QQ-bot.exe 或 dist\QQ-bot\necho 为了正确打包，请在构建后测试 dist 下的可执行文件是否能找到 config 和 data 等运行时资源。
pause
