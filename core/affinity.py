"""
好感度系统
- 好感度变化由 AI 一并返回（在 AI 回复的 JSON 中）
- 持久化存储每个用户的好感度
- 好感度影响 AI 回复态度（注入 system prompt）
- 支持查询和重置
"""
import json
import time
from pathlib import Path
from typing import Optional
from config.settings import BASE_DIR
from core.logger import bot_logger


class AffinityManager:
    """好感度管理器"""

    def __init__(self):
        self.data_file = BASE_DIR / "data" / "affinity.json"
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                bot_logger.error(f"加载好感度数据失败: {e}")
        return {}

    def _save(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            bot_logger.error(f"保存好感度数据失败: {e}")

    def get_affinity(self, user_id: str) -> int:
        """获取用户好感度（-100 到 100）"""
        return self._data.get(user_id, {}).get("score", 0)

    def get_level(self, score: int = None, user_id: str = None) -> str:
        """获取好感度等级描述"""
        if score is None:
            score = self.get_affinity(user_id) if user_id else 0
        if score >= 80:
            return "挚爱"
        elif score >= 60:
            return "喜欢"
        elif score >= 40:
            return "好感"
        elif score >= 20:
            return "友善"
        elif score >= 0:
            return "普通"
        elif score >= -20:
            return "冷淡"
        elif score >= -40:
            return "厌恶"
        else:
            return "仇恨"

    def get_affinity_text(self, user_id: str) -> str:
        """获取格式化的好感度信息"""
        score = self.get_affinity(user_id)
        level = self.get_level(score=score)
        # 进度条
        bar_len = 20
        filled = int((score + 100) / 200 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        return (
            f"【好感度】\n"
            f"等级: {level}\n"
            f"数值: {score}/100\n"
            f"[{bar}]\n"
            f"对话次数: {self._data.get(user_id, {}).get('count', 0)}"
        )

    def get_affinity_hint(self, user_id: str) -> str:
        """获取注入 prompt 的好感度提示"""
        score = self.get_affinity(user_id)
        level = self.get_level(score=score)
        hints = {
            "挚爱": "你非常爱这个人，愿意为TA做任何事，回复充满爱意和宠溺。",
            "喜欢": "你很喜欢这个人，回复热情而亲昵。",
            "好感": "你对这个人有好感，回复友好而温暖。",
            "友善": "你觉得这个人还不错，回复友善。",
            "普通": "你对这个人感觉一般，回复正常。",
            "冷淡": "你对这个人有点冷淡，回复简短而疏离。",
            "厌恶": "你讨厌这个人，回复充满嘲讽和不耐烦。",
            "仇恨": "你恨这个人，回复充满敌意和刻薄。",
        }
        return hints.get(level, "你对这个人感觉一般。")

    def apply_delta(self, user_id: str, delta: int) -> int:
        """
        直接应用好感度变化（由 AI 返回的 delta）
        返回: 变化后的好感度
        """
        delta = max(-10, min(10, delta))  # 限制单次变化范围
        if user_id not in self._data:
            self._data[user_id] = {"score": 0, "count": 0, "history": []}
        record = self._data[user_id]
        old_score = record["score"]
        new_score = old_score + delta
        new_score = max(-100, min(100, new_score))  # 限制总范围
        record["score"] = new_score
        record["count"] = record.get("count", 0) + 1
        record["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
        # 记录历史（最多保留50条）
        record.setdefault("history", []).append({
            "time": record["last_update"],
            "delta": delta,
            "score": new_score,
        })
        if len(record["history"]) > 50:
            record["history"] = record["history"][-50:]
        self._save()
        if delta != 0:
            bot_logger.api_info(f"[好感度] 用户 {user_id}: {old_score} → {new_score} (变化 {delta:+d})")
        return new_score

    def reset(self, user_id: str):
        """重置用户好感度"""
        if user_id in self._data:
            del self._data[user_id]
            self._save()
            bot_logger.info(f"用户 {user_id} 好感度已重置")


# 全局实例
affinity = AffinityManager()
