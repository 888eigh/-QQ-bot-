"""NapCat 启动器兼容层

提供 start()/stop()/is_running() 接口，供 main.py 在未安装 NapCat 工具或仓库未包含启动脚本时调用。

实现说明：
- 优先使用配置项 `napcat_path` 指定的可执行文件路径（在 config/config.json 中配置）。
- 如果未配置，则尝试在 PATH 中查找可执行名 `napcat`。
- 启动后返回 True，失败返回 False。is_running() 可用于轮询进程状态。
"""
import os
import shutil
import subprocess
import threading
import time
import logging

from config.settings import settings

logger = logging.getLogger("napcat_launcher")

_process = None
_process_lock = threading.Lock()


def _find_executable():
    path_cfg = settings.get("napcat_path") or "napcat"
    # 如果是绝对/相对路径且可执行
    if os.path.isfile(path_cfg) and os.access(path_cfg, os.X_OK):
        return os.path.abspath(path_cfg)
    # 尝试 PATH
    exe = shutil.which(path_cfg)
    return exe


def start():
    """尝试启动 NapCat，可多次调用但只会有一个进程。
    返回 True 表示已经在运行或成功启动，False 表示启动失败（可检查日志）。
    """
    global _process
    with _process_lock:
        if _process is not None and _process.poll() is None:
            logger.info("NapCat 已在运行")
            return True

        exe = _find_executable()
        if not exe:
            logger.warning("NapCat 可执行文件未找到，请在配置中设置 napcat_path 或把 napcat 放到 PATH 中")
            return False

        try:
            # 启动子进程，不阻塞当前线程
            _process = subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.1)
            if _process.poll() is None:
                logger.info("NapCat 启动成功")
                return True
            else:
                logger.warning("NapCat 进程启动后立即退出")
                return False
        except Exception as e:
            logger.exception(f"NapCat 启动失败: {e}")
            return False


def is_running() -> bool:
    return _process is not None and _process.poll() is None


def stop() -> bool:
    global _process
    with _process_lock:
        if _process is None:
            return False
        if _process.poll() is None:
            try:
                _process.terminate()
                _process.wait(timeout=5)
            except Exception:
                try:
                    _process.kill()
                except Exception:
                    pass
        _process = None
        logger.info("NapCat 已停止")
        return True
