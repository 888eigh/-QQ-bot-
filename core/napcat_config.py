"""
NapCat 配置自动修改模块
- 首次启动时自动检测并修改 NapCat 配置，确保反向 WebSocket 端口与 Bot 一致
- 支持 JSON 格式配置（主流 NapCat）
- 自动备份原配置
- 支持多种配置路径自动检测
"""
import json
import os
import shutil
from pathlib import Path
from typing import Optional

from config.settings import settings, BASE_DIR
from core.logger import bot_logger


class NapCatConfigManager:
    """NapCat 配置管理器"""

    def __init__(self):
        self.config_path: Optional[Path] = None
        self.first_run_marker = BASE_DIR / "data" / ".napcat_configured"

    def detect_config_path(self) -> Optional[Path]:
        """自动检测 NapCat 配置文件路径"""
        # 1. 用户手动配置的路径
        manual_path = settings.get("napcat_config_path", "")
        if manual_path and Path(manual_path).exists():
            bot_logger.info(f"使用用户指定的 NapCat 配置: {manual_path}")
            return Path(manual_path)

        # 2. NapCat 安装目录下的 config
        napcat_path = settings.get("napcat_path", "")
        if napcat_path:
            napcat_dir = Path(napcat_path).parent if Path(napcat_path).is_file() else Path(napcat_path)
            candidates = [
                napcat_dir / "config" / "onebot11.json",
                napcat_dir / "config" / "napcat.json",
                napcat_dir / "onebot11.json",
                napcat_dir / "napcat.json",
            ]
            for c in candidates:
                if c.exists():
                    return c

        # 3. 常见数据目录
        common_paths = [
            # Windows
            Path(os.environ.get("APPDATA", "")) / "NapCat" / "config" / "onebot11.json",
            Path(os.environ.get("APPDATA", "")) / "NapCat" / "onebot11.json",
            Path(os.environ.get("LOCALAPPDATA", "")) / "NapCat" / "config" / "onebot11.json",
            # Linux
            Path.home() / ".config" / "NapCat" / "config" / "onebot11.json",
            Path.home() / ".config" / "NapCat" / "onebot11.json",
            Path.home() / "NapCat" / "config" / "onebot11.json",
            # macOS
            Path.home() / "Library" / "Application Support" / "NapCat" / "config" / "onebot11.json",
            # 项目同级目录
            BASE_DIR.parent / "NapCat" / "config" / "onebot11.json",
            BASE_DIR / "napcat" / "config" / "onebot11.json",
        ]

        for path in common_paths:
            if path and path.exists():
                bot_logger.info(f"自动检测到 NapCat 配置: {path}")
                return path

        bot_logger.warning("未检测到 NapCat 配置文件，请在配置中设置 napcat_config_path")
        return None

    def is_first_run(self) -> bool:
        """检查是否为首次运行（未配置过 NapCat）"""
        return not self.first_run_marker.exists()

    def mark_configured(self):
        """标记已完成配置"""
        self.first_run_marker.parent.mkdir(parents=True, exist_ok=True)
        self.first_run_marker.write_text(
            f"configured_at: {__import__('datetime').datetime.now()}\n",
            encoding="utf-8"
        )

    def backup_config(self, config_path: Path) -> Optional[Path]:
        """备份配置文件"""
        try:
            backup_path = config_path.with_suffix(config_path.suffix + ".bak")
            shutil.copy2(config_path, backup_path)
            bot_logger.info(f"已备份 NapCat 配置: {backup_path}")
            return backup_path
        except Exception as e:
            bot_logger.error(f"备份 NapCat 配置失败: {e}")
            return None

    def update_reverse_ws_port(self, config_path: Path, bot_port: int, bot_host: str = "127.0.0.1") -> bool:
        """
        修改 NapCat 配置中的反向 WebSocket 端口
        返回是否成功修改
        """
        target_url = f"ws://{bot_host}:{bot_port}/onebot/v11/ws"

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            bot_logger.error(f"NapCat 配置 JSON 解析失败: {e}")
            return False
        except Exception as e:
            bot_logger.error(f"读取 NapCat 配置失败: {e}")
            return False

        modified = False

        # 格式1: network.websocketClients 数组（新版 NapCat）
        if "network" in config and isinstance(config["network"], dict):
            ws_clients = config["network"].get("websocketClients", [])
            if isinstance(ws_clients, list) and ws_clients:
                for client in ws_clients:
                    if isinstance(client, dict) and "url" in client:
                        old_url = client["url"]
                        client["url"] = target_url
                        client["enable"] = True
                        bot_logger.info(f"修改反向WS: {old_url} → {target_url}")
                        modified = True
            else:
                # 没有则添加
                config["network"]["websocketClients"] = [{
                    "enable": True,
                    "name": "QQBot-AutoConfig",
                    "url": target_url,
                    "reportSelfMessage": False,
                    "messagePostFormat": "array",
                    "reconnectInterval": 5000,
                    "token": "",
                    "heartInterval": 30000,
                }]
                bot_logger.info(f"添加反向WS配置: {target_url}")
                modified = True

        # 格式2: 顶层 websocketClients
        elif "websocketClients" in config and isinstance(config["websocketClients"], list):
            for client in config["websocketClients"]:
                if isinstance(client, dict) and "url" in client:
                    old_url = client["url"]
                    client["url"] = target_url
                    client["enable"] = True
                    bot_logger.info(f"修改反向WS: {old_url} → {target_url}")
                    modified = True

        # 格式3: 顶层 reverseWsUrl（旧版/简化版）
        elif "reverseWsUrl" in config:
            old_url = config["reverseWsUrl"]
            config["reverseWsUrl"] = target_url
            bot_logger.info(f"修改 reverseWsUrl: {old_url} → {target_url}")
            modified = True

        # 格式4: wsReverse / websocketReverse 字段
        elif "wsReverse" in config:
            if isinstance(config["wsReverse"], dict):
                old = config["wsReverse"].get("url", "")
                config["wsReverse"]["url"] = target_url
                config["wsReverse"]["enable"] = True
                bot_logger.info(f"修改 wsReverse: {old} → {target_url}")
                modified = True
            elif isinstance(config["wsReverse"], list):
                for item in config["wsReverse"]:
                    if isinstance(item, dict):
                        item["url"] = target_url
                        item["enable"] = True
                modified = True

        if not modified:
            bot_logger.warning("未在 NapCat 配置中找到可修改的反向WS字段，尝试添加 network.websocketClients")
            if "network" not in config:
                config["network"] = {}
            config["network"]["websocketClients"] = [{
                "enable": True,
                "name": "QQBot-AutoConfig",
                "url": target_url,
                "reportSelfMessage": False,
                "messagePostFormat": "array",
                "reconnectInterval": 5000,
                "token": "",
                "heartInterval": 30000,
            }]
            modified = True

        # 保存配置
        if modified:
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                bot_logger.info(f"NapCat 配置已保存: {config_path}")
                return True
            except Exception as e:
                bot_logger.error(f"保存 NapCat 配置失败: {e}")
                return False

        return False

    def auto_configure(self, bot_port: int, bot_host: str = "127.0.0.1", force: bool = False) -> dict:
        """
        首次启动自动配置 NapCat
        返回: {"success": bool, "message": str, "config_path": str|None}
        """
        if not force and not self.is_first_run():
            return {
                "success": True,
                "message": "非首次运行，跳过 NapCat 自动配置",
                "config_path": None,
            }

        config_path = self.detect_config_path()
        if not config_path:
            return {
                "success": False,
                "message": "未找到 NapCat 配置文件，请手动配置反向WebSocket地址",
                "config_path": None,
            }

        # 备份
        self.backup_config(config_path)

        # 修改端口
        success = self.update_reverse_ws_port(config_path, bot_port, bot_host)

        if success:
            self.mark_configured()
            return {
                "success": True,
                "message": f"NapCat 配置已更新，反向WS指向 ws://{bot_host}:{bot_port}/onebot/v11/ws",
                "config_path": str(config_path),
            }
        else:
            return {
                "success": False,
                "message": "NapCat 配置修改失败，请检查日志",
                "config_path": str(config_path),
            }

    def get_current_config(self) -> Optional[dict]:
        """读取当前 NapCat 配置"""
        config_path = self.detect_config_path()
        if not config_path:
            return None
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            bot_logger.error(f"读取 NapCat 配置失败: {e}")
            return None


# 全局实例
napcat_config = NapCatConfigManager()
