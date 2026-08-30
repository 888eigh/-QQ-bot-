"""
本地文档指令回复系统
- 加载 config/docs/commands.json 中的指令标识符
- 用户发送 /XXX 时，自动匹配并返回对应内容
- 支持热重载、指令列表查询
"""
import json
from pathlib import Path
from typing import Optional

from config.settings import DOCS_DIR
from core.logger import bot_logger


class DocReplier:
    """文档指令回复器"""

    def __init__(self):
        self.docs_file = DOCS_DIR / "commands.json"
        self.commands: dict[str, str] = {}
        self.load_commands()

    def load_commands(self):
        """从 JSON 文件加载指令"""
        if not self.docs_file.exists():
            bot_logger.warning(f"指令文档文件不存在: {self.docs_file}")
            self.commands = {}
            return

        try:
            with open(self.docs_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.commands = {k.lower(): str(v) for k, v in data.items()}
                bot_logger.info(f"已加载 {len(self.commands)} 条文档指令")
            else:
                bot_logger.error("指令文档格式错误，应为 JSON 对象")
                self.commands = {}
        except json.JSONDecodeError as e:
            bot_logger.error(f"指令文档 JSON 解析失败: {e}")
            self.commands = {}
        except Exception as e:
            bot_logger.exception(f"加载指令文档失败: {e}")
            self.commands = {}

    def reload(self):
        """热重载指令文档"""
        old_count = len(self.commands)
        self.load_commands()
        new_count = len(self.commands)
        bot_logger.info(f"指令文档已重载: {old_count} → {new_count} 条")
        return new_count

    def get_reply(self, command: str) -> Optional[str]:
        """
        根据指令标识符获取回复内容
        command: 不带前缀的指令名（如 "hello", "help"）
        返回: 对应内容，不存在则返回 None
        """
        key = command.lower().strip()
        return self.commands.get(key)

    def has_command(self, command: str) -> bool:
        """检查指令是否存在"""
        return command.lower().strip() in self.commands

    def list_commands(self) -> list[str]:
        """获取所有指令名列表"""
        return sorted(self.commands.keys())

    def get_command_list_text(self) -> str:
        """获取格式化的指令列表文本"""
        if not self.commands:
            return "暂无可用的文档指令。"
        lines = ["【文档指令列表】"]
        for cmd in sorted(self.commands.keys()):
            preview = self.commands[cmd].split("\n")[0][:30]
            if len(self.commands[cmd]) > 30:
                preview += "..."
            lines.append(f"  /{cmd} - {preview}")
        lines.append(f"\n共 {len(self.commands)} 条指令")
        return "\n".join(lines)

    def add_command(self, command: str, content: str) -> bool:
        """添加/更新指令并保存到文件"""
        key = command.lower().strip()
        self.commands[key] = content
        return self._save()

    def remove_command(self, command: str) -> bool:
        """删除指令并保存"""
        key = command.lower().strip()
        if key in self.commands:
            del self.commands[key]
            return self._save()
        return False

    def _save(self) -> bool:
        """保存指令到文件"""
        try:
            with open(self.docs_file, "w", encoding="utf-8") as f:
                json.dump(self.commands, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            bot_logger.exception(f"保存指令文档失败: {e}")
            return False


# 全局文档回复器
doc_replier = DocReplier()
