"""检查并安装 Python 依赖的脚本

用法:
  python scripts/check_requirements.py

功能:
- 检查 Python 版本是否满足 (>=3.10)
- 读取根目录的 requirements.txt
- 检查并安装缺失的包（使用当前解释器的 pip）
- 返回 exit code 0 表示一切就绪，非 0 表示出错

注意: 在某些系统上需要管理员权限或启用虚拟环境来成功安装包。
"""
import sys
import subprocess
import os
from pathlib import Path

MIN_PYTHON = (3, 10)
REQ_FILE = Path(__file__).resolve().parent.parent / "requirements.txt"


def check_python_version():
    if sys.version_info < MIN_PYTHON:
        print(f"错误: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ 是必须的，当前: {sys.version.split()[0]}")
        return False
    print(f"Python 版本 OK: {sys.version.split()[0]}")
    return True


def read_requirements():
    if not REQ_FILE.exists():
        print("requirements.txt 未找到，跳过依赖安装")
        return []
    lines = []
    for ln in REQ_FILE.read_text(encoding='utf-8').splitlines():
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        lines.append(ln)
    return lines


def is_package_installed(package: str) -> bool:
    # 简单检查：尝试导入包对应的模块名（取包名的第一个标识符）
    name = package.split(';')[0].split('[')[0].split('==')[0].split('>=')[0].split('<')[0]
    name = name.strip()
    # 对类似 pyqt5; platform_system=='Windows' 的 extras 形式，保留前半段
    try:
        __import__(name)
        return True
    except Exception:
        return False


def install_package(package: str) -> bool:
    print(f"正在安装: {package}")
    try:
        cmd = [sys.executable, "-m", "pip", "install", package]
        proc = subprocess.run(cmd, check=False)
        return proc.returncode == 0
    except Exception as e:
        print(f"安装 {package} 失败: {e}")
        return False


def main():
    ok = check_python_version()
    if not ok:
        return 2

    reqs = read_requirements()
    if not reqs:
        print("未检测到待安装依赖，或 requirements.txt 为空")
        return 0

    missing = []
    for pkg in reqs:
        # 处理 platform specific markers 大致跳过不适用于当前平台的行
        if ';' in pkg:
            spec = pkg.split(';', 1)[1]
            try:
                # 仅支持简单的 platform_system=='Windows' 之类判断
                if "platform_system" in spec:
                    if "Windows" in spec and os.name != 'nt':
                        print(f"跳过平台专属依赖: {pkg}")
                        continue
                    if "Linux" in spec and os.name == 'nt':
                        print(f"跳过平台专属依赖: {pkg}")
                        continue
            except Exception:
                pass
            pkg_name = pkg.split(';', 1)[0].strip()
        else:
            pkg_name = pkg

        if not is_package_installed(pkg_name):
            missing.append(pkg)

    if not missing:
        print("所有依赖已安装")
        return 0

    print(f"需要安装 {len(missing)} 个缺失包: {missing}")
    for pkg in missing:
        if not install_package(pkg):
            print(f"安装失败: {pkg}")
            return 3

    print("依赖安��完成")
    return 0


if __name__ == '__main__':
    sys.exit(main())
