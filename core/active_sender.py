"""
主动消息发送模块
- 从 boring.txt 中随机选取一句话（% 分隔）
- 不定时（随机间隔）主动发送到指定群聊
- 发送前检查 Bot 连接状态
- 支持开启/关闭、立即发送、配置目标群
"""
import asyncio
import random
from pathlib import Path
from typing import Optional

from config.settings import BASE_DIR, settings
from core.logger import bot_logger


class ActiveSender:
    """主动消息发送器"""

    def __init__(self):
        self.boring_file = BASE_DIR / "boring.txt"
        self.data_file = BASE_DIR / "data" / "active_send.json"
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

        # 运行时状态
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._bot = None  # NoneBot Bot 实例，运行时设置

        # 加载持久化配置
        self._config = self._load_config()

    def _load_config(self) -> dict:
        default = {
            "enabled": False,
            "target_group": None,
            "min_interval": 1800,   # 最小间隔 30 分钟（秒）
            "max_interval": 7200,   # 最大间隔 2 小时（秒）
            "sent_count": 0,
            "last_sent": None,
        }
        if self.data_file.exists():
            try:
                import json
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                default.update(data)
            except Exception as e:
                bot_logger.error(f"加载主动发送配置失败: {e}")
        return default

    def _save_config(self):
        try:
            import json
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            bot_logger.error(f"保存主动发送配置失败: {e}")

    def load_messages(self) -> list[str]:
        """从 boring.txt 加载消息列表（% 分隔）"""
        if not self.boring_file.exists():
            bot_logger.warning(f"boring.txt 不存在: {self.boring_file}")
            return []

        try:
            content = self.boring_file.read_text(encoding="utf-8")
            # 用 % 分隔，去除空白，过滤空行
            messages = [m.strip() for m in content.split("%") if m.strip()]
            return messages
        except Exception as e:
            bot_logger.error(f"读取 boring.txt 失败: {e}")
            return []

    def random_message(self) -> Optional[str]:
        """随机选取一条消息"""
        messages = self.load_messages()
        if not messages:
            return None
        return random.choice(messages)

    @property
    def enabled(self) -> bool:
        return self._config.get("enabled", False)

    @property
    def target_group(self) -> Optional[int]:
        return self._config.get("target_group")

    @property
    def is_running(self) -> bool:
        return self._running

    def set_bot(self, bot):
        """设置 NoneBot Bot 实例"""
        self._bot = bot

    def set_target_group(self, group_id: int):
        """设置目标群"""
        self._config["target_group"] = int(group_id)
        self._save_config()
        bot_logger.info(f"主动消息目标群已设置: {group_id}")

    def set_interval(self, min_sec: int, max_sec: int):
        """设置发送间隔范围（秒）"""
        self._config["min_interval"] = max(60, min_sec)
        self._config["max_interval"] = max(min_sec + 60, max_sec)
        self._save_config()

    def get_status(self) -> dict:
        """获取状态信息"""
        return {
            "enabled": self.enabled,
            "running": self._running,
            "target_group": self.target_group,
            "min_interval": self._config.get("min_interval"),
            "max_interval": self._config.get("max_interval"),
            "sent_count": self._config.get("sent_count", 0),
            "last_sent": self._config.get("last_sent"),
            "message_count": len(self.load_messages()),
        }

    def get_status_text(self) -> str:
        s = self.get_status()
        lines = ["【主动消息状态】"]
        lines.append(f"  开关: {'开启' if s['enabled'] else '关闭'}")
        lines.append(f"  运行中: {'是' if s['running'] else '否'}")
        lines.append(f"  目标群: {s['target_group'] or '未设置'}")
        lines.append(f"  间隔: {s['min_interval']}~{s['max_interval']} 秒")
        lines.append(f"  已发送: {s['sent_count']} 条")
        lines.append(f"  上次发送: {s['last_sent'] or '从未'}")
        lines.append(f"  消息库: {s['message_count']} 条")
        return "\n".join(lines)

    async def _send_one(self) -> bool:
        """发送一条随机消息"""
        if self._bot is None:
            bot_logger.warning("主动发送: Bot 实例未设置，无法发送")
            return False

        target = self.target_group
        if not target:
            bot_logger.warning("主动发送: 未设置目标群")
            return False

        message = self.random_message()
        if not message:
            bot_logger.warning("主动发送: 消息库为空")
            return False

        try:
            from nonebot.adapters.onebot.v11 import Message, MessageSegment
            await self._bot.send_group_msg(group_id=target, message=Message(message))
            self._config["sent_count"] = self._config.get("sent_count", 0) + 1
            from datetime import datetime
            self._config["last_sent"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_config()
            bot_logger.info(f"[主动消息] 已发送到群 {target}: {message[:30]}...")
            return True
        except Exception as e:
            bot_logger.error(f"主动消息发送失败: {e}")
            return False

    async def _loop(self):
        """主循环：随机间隔发送"""
        bot_logger.info("主动消息循环已启动")
        while self._running and self.enabled:
            try:
                min_i = self._config.get("min_interval", 1800)
                max_i = self._config.get("max_interval", 7200)
                wait_time = random.randint(min_i, max_i)
                bot_logger.info(f"[主动消息] 下次发送将在 {wait_time} 秒后")

                # 分段等待，支持快速停止
                waited = 0
                while waited < wait_time and self._running and self.enabled:
                    await asyncio.sleep(min(10, wait_time - waited))
                    waited += 10

                if not self._running or not self.enabled:
                    break

                await self._send_one()

            except asyncio.CancelledError:
                break
            except Exception as e:
                bot_logger.exception(f"主动消息循环异常: {e}")
                await asyncio.sleep(60)

        self._running = False
        bot_logger.info("主动消息循环已停止")

    def start(self):
        """启动主动消息循环"""
        if self._running:
            bot_logger.warning("主动消息已在运行中")
            return False

        if not self.enabled:
            self._config["enabled"] = True
            self._save_config()

        if not self.target_group:
            bot_logger.warning("主动消息启动失败: 未设置目标群")
            return False

        self._running = True
        self._task = asyncio.create_task(self._loop())
        bot_logger.info("主动消息已启动")
        return True

    def stop(self):
        """停止主动消息循环"""
        self._config["enabled"] = False
        self._save_config()
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        bot_logger.info("主动消息已停止")

    async def send_now(self) -> bool:
        """立即发送一条"""
        return await self._send_one()

    def reload_messages(self):
        """重新加载消息（清除缓存，当前无缓存但预留）"""
        count = len(self.load_messages())
        bot_logger.info(f"boring.txt 已重新加载，共 {count} 条消息")
        return count


# 全局实例
active_sender = ActiveSender()
