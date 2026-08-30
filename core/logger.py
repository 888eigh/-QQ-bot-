"""
UTF-8 日志系统
- 按日期分文件存储
- 错误日志单独存储
- API余额/配额问题专门记录
- 自动清理过期日志
- 全部使用 UTF-8 编码
"""
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config.settings import LOGS_DIR, settings


class UTF8FileHandler(logging.FileHandler):
    """强制 UTF-8 编码的文件处理器"""

    def __init__(self, filename, mode='a', encoding='utf-8', delay=False):
        super().__init__(filename, mode=mode, encoding=encoding, delay=delay)


class BotLogger:
    """机器人日志管理器"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.logs_dir = LOGS_DIR
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # 日志格式
        self.formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # 主日志器
        self.logger = logging.getLogger("qq_bot")
        self.logger.setLevel(getattr(logging, settings.get("log_level", "INFO")))
        self.logger.propagate = False

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)

        # 今日日志文件
        self._attach_file_handlers()

        # 清理旧日志
        self._cleanup_old_logs()

    def _today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _attach_file_handlers(self):
        """挂载今日的文件处理器"""
        today = self._today_str()

        # 全量日志
        all_handler = UTF8FileHandler(
            self.logs_dir / f"bot_{today}.log",
            encoding="utf-8"
        )
        all_handler.setFormatter(self.formatter)
        all_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(all_handler)

        # 错误日志（单独文件）
        error_handler = UTF8FileHandler(
            self.logs_dir / f"error_{today}.log",
            encoding="utf-8"
        )
        error_handler.setFormatter(self.formatter)
        error_handler.setLevel(logging.ERROR)
        self.logger.addHandler(error_handler)

        # API 专用日志（余额、配额、调用失败等）
        api_handler = UTF8FileHandler(
            self.logs_dir / f"api_{today}.log",
            encoding="utf-8"
        )
        api_handler.setFormatter(self.formatter)
        api_handler.setLevel(logging.INFO)
        self.api_logger = logging.getLogger("qq_bot.api")
        self.api_logger.setLevel(logging.INFO)
        self.api_logger.propagate = True
        self.api_logger.addHandler(api_handler)

    def _cleanup_old_logs(self):
        """清理超过保留天数的日志文件"""
        keep_days = settings.get("log_keep_days", 30)
        cutoff = datetime.now() - timedelta(days=keep_days)

        for log_file in self.logs_dir.glob("*.log"):
            try:
                # 从文件名提取日期
                match = re.search(r"(\d{4}-\d{2}-\d{2})", log_file.name)
                if match:
                    file_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                    if file_date < cutoff:
                        log_file.unlink()
                        self.logger.info(f"已清理过期日志: {log_file.name}")
            except Exception as e:
                self.logger.warning(f"清理日志文件失败 {log_file.name}: {e}")

    def check_and_rotate(self):
        """检查是否需要按天轮转日志（跨天时调用）"""
        # 简单实现：检查今日文件是否存在，不存在则重新挂载
        today_file = self.logs_dir / f"bot_{self._today_str()}.log"
        if not today_file.exists():
            # 移除旧的文件处理器，重新挂载
            for handler in self.logger.handlers[:]:
                if isinstance(handler, UTF8FileHandler):
                    self.logger.removeHandler(handler)
            for handler in self.api_logger.handlers[:]:
                if isinstance(handler, UTF8FileHandler):
                    self.api_logger.removeHandler(handler)
            self._attach_file_handlers()
            self.logger.info("日志已按日轮转")

    # 便捷方法
    def debug(self, msg: str, *args, **kwargs):
        self.check_and_rotate()
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self.check_and_rotate()
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.check_and_rotate()
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.check_and_rotate()
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self.check_and_rotate()
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        self.check_and_rotate()
        self.logger.exception(msg, *args, **kwargs)

    # API 专用日志
    def api_info(self, msg: str, *args, **kwargs):
        self.check_and_rotate()
        self.api_logger.info(msg, *args, **kwargs)

    def api_error(self, msg: str, *args, **kwargs):
        self.check_and_rotate()
        self.api_logger.error(msg, *args, **kwargs)

    def api_balance_warning(self, msg: str):
        """API余额/配额不足警告"""
        self.check_and_rotate()
        self.api_logger.warning(f"[API余额/配额] {msg}")
        self.logger.warning(f"API余额/配额警告: {msg}")

    def get_log_files(self) -> list:
        """获取所有日志文件列表"""
        return sorted(self.logs_dir.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True)

    def read_log(self, filename: str, tail: int = 100) -> str:
        """读取指定日志文件的最后N行"""
        log_path = self.logs_dir / filename
        if not log_path.exists():
            return f"日志文件不存在: {filename}"
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return "".join(lines[-tail:])
        except Exception as e:
            return f"读取日志失败: {e}"


# 全局日志实例
bot_logger = BotLogger()
