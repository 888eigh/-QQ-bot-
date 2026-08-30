"""
Text 文档指令系统
- 读取程序根目录 text/ 下的文本文档
- 支持自定义指令格式（如 #文档名、[文档名]、{{文档名}} 等）
- 用户发送匹配格式的指令时，返回对应文档内容
"""
import re
from pathlib import Path
from typing import Optional

from config.settings import BASE_DIR, settings
from core.logger import bot_logger


class TextDocsManager:
    """Text 文档管理器"""

    def __init__(self):
        self.text_dir = BASE_DIR / "text"
        self.text_dir.mkdir(parents=True, exist_ok=True)
        # 支持的文件扩展名
        self.supported_exts = {".txt", ".md", ".text"}
        # 文档缓存
        self._cache: dict[str, str] = {}

    def list_docs(self) -> list[str]:
        """列出所有可用文档（不含扩展名）"""
        docs = []
        for f in self.text_dir.iterdir():
            if f.is_file() and f.suffix.lower() in self.supported_exts:
                docs.append(f.stem)
        return sorted(docs)

    def read_doc(self, name: str) -> Optional[str]:
        """
        读取指定文档内容
        name: 文档名（不含扩展名）
        返回: 文档内容，不存在返回 None
        """
        name = name.strip()
        # 先查缓存
        if name in self._cache:
            return self._cache[name]

        # 尝试匹配文件（支持多种扩展名）
        for ext in self.supported_exts:
            filepath = self.text_dir / f"{name}{ext}"
            if filepath.exists():
                try:
                    content = filepath.read_text(encoding="utf-8")
                    self._cache[name] = content
                    return content
                except Exception as e:
                    bot_logger.error(f"读取文档 {name} 失败: {e}")
                    return None
        return None

    def reload(self):
        """清除缓存，重新扫描"""
        self._cache.clear()
        bot_logger.info(f"Text 文档缓存已清除，当前 {len(self.list_docs())} 个文档")

    def get_command_pattern(self) -> re.Pattern:
        """
        根据配置生成指令匹配正则
        配置项 text_command_format 支持:
          - "hash"  : #文档名（默认）
          - "bracket": [文档名]
          - "brace"  : {{文档名}}
          - "at"     : @文档名
          - 自定义正则字符串
        """
        fmt = settings.get("text_command_format", "hash")

        patterns = {
            "hash": r"#(\w+)",
            "bracket": r"\[(\w+)\]",
            "brace": r"\{\{(\w+)\}\}",
            "at": r"@(\w+)",
        }

        if fmt in patterns:
            return re.compile(patterns[fmt])
        else:
            # 用户自定义正则
            try:
                return re.compile(fmt)
            except re.error:
                bot_logger.warning(f"无效的自定义指令格式: {fmt}，使用默认 #文档名")
                return re.compile(r"#(\w+)")

    def match_and_read(self, message: str) -> Optional[tuple[str, str]]:
        """
        从消息中匹配文档指令并读取内容
        返回: (文档名, 内容) 或 None
        """
        pattern = self.get_command_pattern()
        match = pattern.search(message)
        if not match:
            return None

        doc_name = match.group(1)
        content = self.read_doc(doc_name)
        if content is not None:
            return (doc_name, content)
        return None

    def get_doc_list_text(self) -> str:
        """获取格式化的文档列表"""
        docs = self.list_docs()
        if not docs:
            return "text/ 目录下暂无文档。"
        fmt = settings.get("text_command_format", "hash")
        prefix = {"hash": "#", "bracket": "[", "brace": "{{", "at": "@"}.get(fmt, "#")
        lines = ["【可用文本文档】"]
        for doc in docs:
            lines.append(f"  {prefix}{doc}")
        lines.append(f"\n共 {len(docs)} 个文档，发送对应指令即可读取。")
        return "\n".join(lines)


# 全局实例
text_docs = TextDocsManager()
