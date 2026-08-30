# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 - QQ Bot
在 Windows 上执行: 双击 一键打包.exe.bat
"""
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 项目根目录
project_root = os.path.abspath('.')

# 收集 nonebot 相关的所有子模块（避免运行时找不到适配器/插件）
hiddenimports = []
hiddenimports += collect_submodules('nonebot')
hiddenimports += collect_submodules('nonebot.adapters.onebot')
hiddenimports += collect_submodules('nonebot.drivers')
hiddenimports += collect_submodules('pydantic')
hiddenimports += ['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
                  'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
                  'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
                  'uvicorn.lifespan', 'uvicorn.lifespan.on']

# 数据文件：配置、插件、文档、资源目录
datas = [
    (os.path.join(project_root, 'config', 'docs', 'commands.json'), 'config/docs'),
    (os.path.join(project_root, 'config', 'config.json'), 'config'),
    (os.path.join(project_root, 'config', 'default_config.json'), 'config'),
    (os.path.join(project_root, 'plugins'), 'plugins'),
    (os.path.join(project_root, 'core'), 'core'),
    (os.path.join(project_root, 'gui'), 'gui'),
    (os.path.join(project_root, 'text'), 'text'),
    (os.path.join(project_root, 'picture'), 'picture'),
    (os.path.join(project_root, 'emotional'), 'emotional'),
    (os.path.join(project_root, 'pyproject.toml'), '.'),
    (os.path.join(project_root, '.env'), '.'),
    (os.path.join(project_root, '.env.dev'), '.'),
    (os.path.join(project_root, 'boring.txt'), '.'),
    (os.path.join(project_root, 'requirements.txt'), '.'),
]

a = Analysis(
    ['bot.py'],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='QQBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
