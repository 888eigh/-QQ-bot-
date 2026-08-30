"""
自适应端口管理模块
- 检测端口是否被占用
- 自动在指定范围内寻找可用端口
- 支持端口冲突时自动切换
"""
import socket
from typing import Optional

from config.settings import settings
from core.logger import bot_logger


class PortManager:
    """端口管理器"""

    def __init__(self):
        self.host = settings.get("bot_host", "0.0.0.0")
        self.preferred_port = settings.get("bot_port", 8080)
        self.auto_port = settings.get("auto_port", True)
        self.port_range = settings.get("port_range", [8080, 9090])
        self.current_port: Optional[int] = None

    def is_port_in_use(self, port: int, host: str = None) -> bool:
        """检测指定端口是否被占用"""
        check_host = host or self.host
        # 0.0.0.0 检测时用 127.0.0.1 更可靠
        if check_host == "0.0.0.0":
            check_host = "127.0.0.1"

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            try:
                s.bind((check_host, port))
                return False
            except OSError:
                return True

    def find_available_port(self, start: int = None, end: int = None) -> Optional[int]:
        """在指定范围内寻找可用端口"""
        start_port = start if start is not None else self.port_range[0]
        end_port = end if end is not None else self.port_range[1]

        for port in range(start_port, end_port + 1):
            if not self.is_port_in_use(port):
                return port
        return None

    def get_port(self) -> int:
        """
        获取可用端口
        - 优先使用配置的端口
        - 如果被占用且开启了自适应，则自动寻找
        - 返回最终确定的端口
        """
        # 先尝试首选端口
        if not self.is_port_in_use(self.preferred_port):
            self.current_port = self.preferred_port
            bot_logger.info(f"端口 {self.preferred_port} 可用，使用该端口")
            return self.current_port

        # 首选端口被占用
        if self.auto_port:
            bot_logger.warning(f"端口 {self.preferred_port} 已被占用，启动自适应端口搜索...")
            available = self.find_available_port()
            if available:
                self.current_port = available
                bot_logger.info(f"自适应找到可用端口: {available}")
                # 更新配置中的端口
                settings.set("bot_port", available)
                return available
            else:
                bot_logger.error(f"端口范围 {self.port_range} 内无可用端口！")
                # 退而求其次，让系统自动分配
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("", 0))
                    self.current_port = s.getsockname()[1]
                bot_logger.warning(f"使用系统随机分配端口: {self.current_port}")
                return self.current_port
        else:
            bot_logger.error(f"端口 {self.preferred_port} 已被占用，且未开启自适应端口！")
            return self.preferred_port

    def release_port(self):
        """释放端口标记"""
        self.current_port = None

    def get_connection_info(self) -> dict:
        """获取连接信息（用于 NapCat 配置和 GUI 显示）"""
        port = self.current_port or self.get_port()
        return {
            "host": self.host,
            "port": port,
            "ws_url": f"ws://127.0.0.1:{port}/onebot/v11/ws",
            "http_url": f"http://127.0.0.1:{port}/onebot/v11/",
        }


# 全局端口管理器
port_manager = PortManager()
