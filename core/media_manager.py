"""
多媒体资源管理器
- 扫描 picture/ 和 emotional/ 目录下的图片
- 提供资源列表给 AI 选择
- 解析 AI 回复中的媒体标记，转换为 OneBot 图片消息
"""
import re
from pathlib import Path
from typing import Optional

from config.settings import BASE_DIR
from core.logger import bot_logger


class MediaManager:
    """多媒体资源管理器"""

    def __init__(self):
        self.picture_dir = BASE_DIR / "picture"
        self.emotional_dir = BASE_DIR / "emotional"
        for d in [self.picture_dir, self.emotional_dir]:
            d.mkdir(parents=True, exist_ok=True)
        self.supported_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
        # 媒体标记正则：[pic:文件名] [emo:文件名]
        self.pic_pattern = re.compile(r"\[pic:([^\]]+)\]")
        self.emo_pattern = re.compile(r"\[emo:([^\]]+)\]")

    def list_pictures(self) -> list[str]:
        """列出所有图片"""
        return self._list_files(self.picture_dir)

    def list_emotionals(self) -> list[str]:
        """列出所有表情"""
        return self._list_files(self.emotional_dir)

    def _list_files(self, directory: Path) -> list[str]:
        files = []
        for f in directory.iterdir():
            if f.is_file() and f.suffix.lower() in self.supported_exts:
                files.append(f.name)
        return sorted(files)

    def get_picture_path(self, name: str) -> Optional[Path]:
        """获取图片路径（支持不带扩展名）"""
        return self._find_file(self.picture_dir, name)

    def get_emotional_path(self, name: str) -> Optional[Path]:
        """获取表情路径"""
        return self._find_file(self.emotional_dir, name)

    def _find_file(self, directory: Path, name: str) -> Optional[Path]:
        name = name.strip()
        # 精确匹配
        exact = directory / name
        if exact.exists():
            return exact
        # 不带扩展名匹配
        for ext in self.supported_exts:
            candidate = directory / f"{name}{ext}"
            if candidate.exists():
                return candidate
        return None

    def get_media_list_text(self) -> str:
        """获取可用媒体列表文本（注入 prompt 用）"""
        pics = self.list_pictures()
        emos = self.list_emotionals()
        lines = []
        if pics:
            lines.append("可用图片（回复中用 [pic:文件名] 标记发送）:")
            for p in pics[:20]:  # 最多列20个
                lines.append(f"  - {p}")
            if len(pics) > 20:
                lines.append(f"  ... 还有 {len(pics) - 20} 张")
        if emos:
            lines.append("可用表情（回复中用 [emo:文件名] 标记发送）:")
            for e in emos[:20]:
                lines.append(f"  - {e}")
            if len(emos) > 20:
                lines.append(f"  ... 还有 {len(emos) - 20} 个")
        if not pics and not emos:
            lines.append("（暂无可用图片和表情）")
        return "\n".join(lines)

    def parse_and_get_media(self, text: str) -> tuple[str, list[Path]]:
        """
        解析文本中的媒体标记，返回清理后的文本和媒体文件路径列表
        """
        media_files = []

        # 解析图片
        for match in self.pic_pattern.finditer(text):
            name = match.group(1)
            path = self.get_picture_path(name)
            if path:
                media_files.append(path)
            else:
                bot_logger.warning(f"未找到图片: {name}")

        # 解析表情
        for match in self.emo_pattern.finditer(text):
            name = match.group(1)
            path = self.get_emotional_path(name)
            if path:
                media_files.append(path)
            else:
                bot_logger.warning(f"未找到表情: {name}")

        # 清理标记
        clean_text = self.pic_pattern.sub("", text)
        clean_text = self.emo_pattern.sub("", clean_text)
        clean_text = clean_text.strip()

        return clean_text, media_files

    def reload(self):
        """重新扫描（清除内部缓存，当前无缓存但预留）"""
        bot_logger.info(
            f"媒体资源刷新: 图片 {len(self.list_pictures())} 张, "
            f"表情 {len(self.list_emotionals())} 个"
        )


# 全局实例
media_manager = MediaManager()
