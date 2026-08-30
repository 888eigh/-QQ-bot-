"""配置管理模块 - 统一管理所有配置项，支持环境变量和配置文件"""
import os
import json
from pathlib import Path
from typing import Optional

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 配置文件路径
CONFIG_FILE = BASE_DIR / "config" / "config.json"
DOCS_DIR = BASE_DIR / "config" / "docs"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

# 确保目录存在
for d in [DOCS_DIR, LOGS_DIR, DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class Settings:
    """全局配置单例"""

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
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """加载配置文件，不存在则创建默认配置"""
        default = {
            # AI API 配置（DeepSeek V4 Flash）
            "api_base_url": "https://api.deepseek.com",
            "api_key": "",
            "api_model": "deepseek-v4-flash",
            "api_timeout": 60,
            "api_max_tokens": 4096,
            "api_temperature": 1.0,
            "api_thinking_disabled": True,

            # 机器人配置
            "bot_host": "0.0.0.0",
            "bot_port": 8080,
            "auto_port": True,
            "port_range": [8080, 9090],
            "command_prefix": "/",
            "superusers": [],
            "nickname": ["bot", "机器人"],

            # NapCat 配置
            "napcat_path": "",
            "napcat_auto_start": False,
            "napcat_ws_url": "ws://127.0.0.1:3001",

            # 日志配置
            "log_level": "INFO",
            "log_keep_days": 30,

            # 聊天配置
            "chat_enabled": True,
            "chat_group_enabled": True,
            "chat_private_enabled": True,
            "chat_system_prompt": "你是一个 helpful 的QQ机器人助手，用简洁友好的中文回答问题。",
            "chat_history_limit": 20,

            # Text 文档指令配置
            "text_command_format": "hash",  # hash/bracket/brace/at 或自定义正则
        }

        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                default.update(user_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[配置警告] 读取配置文件失败，使用默认配置: {e}")
        else:
            self._save_config(default)

        return default

    def _save_config(self, config: dict = None):
        """保存配置到文件"""
        if config is None:
            config = self._config
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[配置错误] 保存配置文件失败: {e}")

    def get(self, key: str, default=None):
        """获取配置项"""
        return self._config.get(key, default)

    def set(self, key: str, value):
        """设置配置项并保存"""
        self._config[key] = value
        self._save_config()

    def update(self, data: dict):
        """批量更新配置"""
        self._config.update(data)
        self._save_config()

    @property
    def all(self) -> dict:
        return self._config.copy()


# 全局配置实例
settings = Settings()
