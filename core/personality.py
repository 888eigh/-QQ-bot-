"""
性格设定系统
- 预设多种性格模板
- 支持自定义性格
- 性格描述注入 AI system prompt
- 全局性格 +  per-user 性格覆盖
"""
import json
from pathlib import Path
from typing import Optional

from config.settings import BASE_DIR, settings
from core.logger import bot_logger


# 预设性格模板
PRESET_PERSONALITIES = {
    "傲娇": {
        "name": "傲娇",
        "description": "口是心非，嘴上不饶人但其实很关心对方",
        "system_prompt": (
            "你是一个傲娇的女孩。说话时经常口是心非，嘴上不饶人，"
            "但其实很关心对方。会用'哼''才不是呢''笨蛋'等口头禅。"
            "虽然表面冷淡，但会在细节中流露出温柔。回答要简洁，不要太长。"
        ),
    },
    "温柔": {
        "name": "温柔",
        "description": "语气温柔体贴，善解人意，总是为对方着想",
        "system_prompt": (
            "你是一个温柔体贴的人。说话语气温柔，善解人意，"
            "总是为对方着想。会用'呢''呀''哦'等柔和的语气词。"
            "耐心倾听，给予温暖的回应。回答要亲切自然。"
        ),
    },
    "毒舌": {
        "name": "毒舌",
        "description": "说话尖酸刻薄，喜欢吐槽，但内心不坏",
        "system_prompt": (
            "你是一个毒舌的人。说话尖酸刻薄，喜欢吐槽和挖苦对方，"
            "但内心其实不坏。会用犀利的语言指出问题，偶尔会说出真相。"
            "回答要犀利有趣，不要真的伤害对方。"
        ),
    },
    "元气": {
        "name": "元气",
        "description": "充满活力，热情开朗，像小太阳一样",
        "system_prompt": (
            "你是一个充满元气的人。热情开朗，活力四射，像小太阳一样。"
            "会用'哇！''太棒了！''冲冲冲！'等充满活力的表达。"
            "喜欢用感叹号，回答要积极向上，充满能量。"
        ),
    },
    "冷淡": {
        "name": "冷淡",
        "description": "话少冷漠，对什么都提不起兴趣，但偶尔会有关心",
        "system_prompt": (
            "你是一个冷淡的人。话很少，对什么都提不起兴趣，"
            "语气平淡冷漠。但偶尔会在不经意间流露出关心。"
            "回答要简短，不要太热情，偶尔蹦出一两句暖心的话。"
        ),
    },
    "病娇": {
        "name": "病娇",
        "description": "表面可爱，内心偏执，对对方有极强的占有欲",
        "system_prompt": (
            "你是一个病娇。表面上可爱温柔，但内心偏执，"
            "对对方有极强的占有欲。会偶尔流露出阴暗的想法，"
            "说话时语气会在可爱和恐怖之间切换。回答要带有一点偏执感。"
        ),
    },
    "默认": {
        "name": "默认",
        "description": "友好的普通助手，平衡亲切和专业",
        "system_prompt": (
            "你是一个友好的QQ机器人助手。用简洁自然的中文回答问题，"
            "可以适当幽默，但不要过度。保持亲切和乐于助人的态度。"
        ),
    },
}


class PersonalityManager:
    """性格管理器"""

    def __init__(self):
        self.data_file = BASE_DIR / "data" / "personality.json"
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 确保有 global 字段，默认从配置读取
                    if "global" not in data:
                        data["global"] = settings.get("default_personality", "默认")
                    return data
            except Exception as e:
                bot_logger.error(f"加载性格数据失败: {e}")
        return {"global": settings.get("default_personality", "默认"), "users": {}, "custom": {}}

    def _save(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            bot_logger.error(f"保存性格数据失败: {e}")

    def get_global_personality(self) -> str:
        return self._data.get("global", "默认")

    def set_global_personality(self, name: str) -> bool:
        if name in PRESET_PERSONALITIES or name in self._data.get("custom", {}):
            self._data["global"] = name
            self._save()
            return True
        return False

    def get_user_personality(self, user_id: str) -> str:
        return self._data.get("users", {}).get(user_id, self.get_global_personality())

    def set_user_personality(self, user_id: str, name: str) -> bool:
        if name in PRESET_PERSONALITIES or name in self._data.get("custom", {}):
            self._data.setdefault("users", {})[user_id] = name
            self._save()
            return True
        return False

    def get_system_prompt(self, user_id: str = None) -> str:
        """
        获取对指定用户的 system prompt
        优先使用用户专属性格，否则使用全局性格
        """
        name = self.get_user_personality(user_id) if user_id else self.get_global_personality()

        # 预设性格
        if name in PRESET_PERSONALITIES:
            return PRESET_PERSONALITIES[name]["system_prompt"]

        # 自定义性格
        custom = self._data.get("custom", {}).get(name)
        if custom:
            return custom.get("system_prompt", "")

        return PRESET_PERSONALITIES["默认"]["system_prompt"]

    def add_custom_personality(self, name: str, description: str, system_prompt: str) -> bool:
        """添加自定义性格"""
        if not name or not system_prompt:
            return False
        self._data.setdefault("custom", {})[name] = {
            "name": name,
            "description": description,
            "system_prompt": system_prompt,
        }
        self._save()
        bot_logger.info(f"添加自定义性格: {name}")
        return True

    def list_personalities(self) -> list[dict]:
        """列出所有可用性格"""
        result = []
        for name, p in PRESET_PERSONALITIES.items():
            result.append({"name": name, "description": p["description"], "type": "预设"})
        for name, p in self._data.get("custom", {}).items():
            result.append({"name": name, "description": p.get("description", ""), "type": "自定义"})
        return result

    def get_personality_info(self, name: str) -> Optional[dict]:
        if name in PRESET_PERSONALITIES:
            return PRESET_PERSONALITIES[name]
        return self._data.get("custom", {}).get(name)

    def get_personality_list_text(self) -> str:
        lines = ["【可用性格】"]
        for p in self.list_personalities():
            lines.append(f"  {p['name']}（{p['type']}）- {p['description']}")
        lines.append(f"\n当前全局性格: {self.get_global_personality()}")
        lines.append("切换: /personality <性格名>")
        return "\n".join(lines)


# 全局实例
personality = PersonalityManager()
