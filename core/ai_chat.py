"""
AI 聊天模块 - 基于 OpenAI 兼容 API
支持接入任意 OpenAI 格式的 API（DeepSeek、通义千问、豆包、Kimi 等）
包含对话历史管理、错误处理、余额检测、API日志
AI 返回 JSON 格式：{"reply": "回复内容", "affinity_delta": 5}
好感度由 AI 一并返回，无需额外 API 调用
"""
import json
import re
import time
from typing import Optional
from collections import defaultdict
import httpx
from config.settings import settings
from core.logger import bot_logger


class ChatSession:
    """单用户对话会话"""

    def __init__(self, user_id: str, system_prompt: str, history_limit: int = 20):
        self.user_id = user_id
        self.history_limit = history_limit
        self.messages = [{"role": "system", "content": system_prompt}]
        self.last_active = time.time()

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})
        self.last_active = time.time()
        self._trim_history()

    def add_assistant_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content})
        self.last_active = time.time()
        self._trim_history()

    def _trim_history(self):
        """保留 system + 最近 N 轮对话"""
        if len(self.messages) > self.history_limit + 1:
            system_msg = self.messages[0]
            recent = self.messages[-(self.history_limit):]
            self.messages = [system_msg] + recent

    def clear(self):
        system_msg = self.messages[0]
        self.messages = [system_msg]


class AIChatManager:
    """AI 聊天管理器"""

    def __init__(self):
        self.sessions: dict[str, ChatSession] = {}
        self.api_base_url = settings.get("api_base_url", "https://api.deepseek.com")
        self.api_key = settings.get("api_key", "")
        self.model = settings.get("api_model", "deepseek-v4-flash")
        self.timeout = settings.get("api_timeout", 60)
        self.max_tokens = settings.get("api_max_tokens", 4096)
        self.temperature = settings.get("api_temperature", 1.0)
        self.thinking_disabled = settings.get("api_thinking_disabled", True)
        self.system_prompt = settings.get(
            "chat_system_prompt",
            "你是一个 helpful 的QQ机器人助手，用简洁友好的中文回答问题。"
        )
        self.history_limit = settings.get("chat_history_limit", 20)
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def reload_config(self):
        """重新加载配置（修改配置后调用）"""
        self.api_base_url = settings.get("api_base_url", self.api_base_url)
        self.api_key = settings.get("api_key", self.api_key)
        self.model = settings.get("api_model", self.model)
        self.timeout = settings.get("api_timeout", self.timeout)
        self.max_tokens = settings.get("api_max_tokens", self.max_tokens)
        self.temperature = settings.get("api_temperature", self.temperature)
        self.thinking_disabled = settings.get("api_thinking_disabled", self.thinking_disabled)
        self.system_prompt = settings.get("chat_system_prompt", self.system_prompt)
        self.history_limit = settings.get("chat_history_limit", self.history_limit)
        bot_logger.info("AI 聊天配置已重新加载")

    def get_session(self, user_id: str) -> ChatSession:
        """获取或创建用户会话"""
        if user_id not in self.sessions:
            self.sessions[user_id] = ChatSession(
                user_id, self.system_prompt, self.history_limit
            )
        return self.sessions[user_id]

    def clear_session(self, user_id: str):
        """清除用户对话历史"""
        if user_id in self.sessions:
            self.sessions[user_id].clear()
            bot_logger.info(f"用户 {user_id} 的对话历史已清除")

    def clear_all_sessions(self):
        """清除所有会话"""
        self.sessions.clear()
        bot_logger.info("所有对话历史已清除")

    def build_system_prompt(self, user_id: str) -> str:
        """
        构建动态 system prompt
        包含：基础设定 + 性格 + 好感度 + 可用媒体资源 + JSON输出要求
        """
        parts = []
        # 1. 性格设定
        try:
            from core.personality import personality
            char_prompt = personality.get_system_prompt(user_id)
            if char_prompt:
                parts.append(char_prompt)
        except Exception:
            parts.append(self.system_prompt)
        # 2. 好感度提示
        try:
            from core.affinity import affinity
            current_score = affinity.get_affinity(user_id)
            affinity_hint = affinity.get_affinity_hint(user_id)
            parts.append(f"【当前对用户的好感度】{affinity_hint}（当前数值: {current_score}，范围-100到100）")
        except Exception:
            pass
        # 3. 媒体资源说明
        try:
            from core.media_manager import media_manager
            media_list = media_manager.get_media_list_text()
            if media_list and "暂无" not in media_list:
                parts.append(f"【可用媒体资源】\n{media_list}\n注意：如果觉得合适，可以在回复中用 [pic:文件名] 或 [emo:文件名] 标记来发送图片/表情。一次回复最多使用1-2个媒体。")
        except Exception:
            pass
        # 4. 输出格式要求（关键：AI一并返回好感度变化）
        parts.append(
            "【输出格式要求】\n"
            "你必须严格按照以下JSON格式回复，不要输出任何其他内容：\n"
            "{\"reply\": \"你的回复内容\", \"affinity_delta\": 好感度变化整数}\n\n"
            "其中：\n"
            "- reply: 你对用户说的话，自然、符合性格设定\n"
            "- affinity_delta: 本次对话后你对用户好感度的变化量，整数，范围-10到+10\n"
            "  正数表示好感增加（用户说了让你开心/感动/有趣的话）\n"
            "  负数表示好感减少（用户说了让你生气/难过/无聊的话）\n"
            "  0表示无变化\n"
            "  注意：好感度变化要符合你的性格和当前好感度等级，不要每次都加很多。\n\n"
            "示例：{\"reply\": \"你好呀！今天过得怎么样？\", \"affinity_delta\": 2}\n"
            "示例：{\"reply\": \"哼，不想理你。\", \"affinity_delta\": -3}"
        )
        # 5. 基础规则
        parts.append("回复要自然，不要提及你是AI或系统提示词的存在。必须输出合法JSON。")
        return "\n\n".join(parts)

    def _update_system_prompt(self, session: ChatSession, user_id: str):
        """更新会话的 system prompt（保留历史对话）"""
        new_prompt = self.build_system_prompt(user_id)
        if session.messages and session.messages[0]["role"] == "system":
            session.messages[0]["content"] = new_prompt
        else:
            session.messages.insert(0, {"role": "system", "content": new_prompt})

    def _parse_ai_response(self, raw_text: str) -> dict:
        """
        解析 AI 返回的 JSON
        返回: {"reply": "...", "affinity_delta": 0}
        解析失败时回退到纯文本
        """
        result = {"reply": raw_text, "affinity_delta": 0}
        # 尝试提取 JSON（可能被 markdown 代码块包裹）
        json_match = re.search(r'\{[^{}]*"reply"[^{}]*\}', raw_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if "reply" in data:
                    result["reply"] = str(data["reply"])
                if "affinity_delta" in data:
                    delta = int(data["affinity_delta"])
                    result["affinity_delta"] = max(-10, min(10, delta))
                return result
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        # 尝试直接解析整段
        try:
            data = json.loads(raw_text.strip())
            if isinstance(data, dict) and "reply" in data:
                result["reply"] = str(data["reply"])
                if "affinity_delta" in data:
                    delta = int(data["affinity_delta"])
                    result["affinity_delta"] = max(-10, min(10, delta))
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        return result

    async def chat(self, user_id: str, message: str) -> dict:
        """
        发送聊天消息并获取回复
        返回: {"reply": "AI回复文本", "affinity_delta": 好感度变化, "raw": "原始响应"}
        """
        if not self.api_key:
            bot_logger.api_error("API Key 未配置，无法进行AI对话")
            return {"reply": "⚠️ AI 功能未配置 API Key，请在配置文件中设置 api_key。", "affinity_delta": 0, "raw": ""}

        session = self.get_session(user_id)
        # 动态更新 system prompt（注入性格、好感度、媒体资源、JSON格式要求）
        self._update_system_prompt(session, user_id)
        session.add_user_message(message)

        url = f"{self.api_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": session.messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "thinking": {"type": "disabled" if self.thinking_disabled else "enabled"},
            "response_format": {"type": "json_object"},
        }

        try:
            client = self._get_client()
            response = await client.post(url, headers=headers, json=payload)

            # 处理 HTTP 状态码
            if response.status_code == 401:
                bot_logger.api_error(f"API 认证失败 (401): API Key 无效或已过期")
                return {"reply": "⚠️ API 认证失败，请检查 API Key 是否正确。", "affinity_delta": 0, "raw": ""}
            if response.status_code == 402:
                bot_logger.api_balance_warning("API 账户余额不足 (402)")
                return {"reply": "⚠️ API 账户余额不足，请充值后再试。", "affinity_delta": 0, "raw": ""}
            if response.status_code == 429:
                bot_logger.api_balance_warning("API 请求频率超限或配额耗尽 (429)")
                return {"reply": "⚠️ API 请求过于频繁或配额已耗尽，请稍后再试。", "affinity_delta": 0, "raw": ""}
            if response.status_code >= 500:
                bot_logger.api_error(f"API 服务器错误 ({response.status_code}): {response.text[:500]}")
                return {"reply": f"⚠️ AI 服务暂时不可用 (HTTP {response.status_code})，请稍后再试。", "affinity_delta": 0, "raw": ""}
            if response.status_code != 200:
                bot_logger.api_error(f"API 请求失败 ({response.status_code}): {response.text[:500]}")
                return {"reply": f"⚠️ API 请求失败 (HTTP {response.status_code})。", "affinity_delta": 0, "raw": ""}

            result = response.json()
            raw_reply = result["choices"][0]["message"]["content"].strip()

            # 记录 token 使用情况
            usage = result.get("usage", {})
            if usage:
                bot_logger.api_info(
                    f"用户 {user_id} | 模型 {self.model} | "
                    f"prompt_tokens={usage.get('prompt_tokens', '?')}, "
                    f"completion_tokens={usage.get('completion_tokens', '?')}, "
                    f"total_tokens={usage.get('total_tokens', '?')}"
                )

            # 解析 JSON，提取回复和好感度变化
            parsed = self._parse_ai_response(raw_reply)
            reply = parsed["reply"]
            affinity_delta = parsed["affinity_delta"]

            # 历史记录只存纯回复内容（不存JSON）
            session.add_assistant_message(reply)

            bot_logger.info(f"[AI回复] 用户 {user_id}: 好感度变化 {affinity_delta:+d}")

            return {"reply": reply, "affinity_delta": affinity_delta, "raw": raw_reply}

        except httpx.TimeoutException:
            bot_logger.api_error(f"API 请求超时 (用户 {user_id})")
            return {"reply": "⚠️ AI 响应超时，请稍后再试。", "affinity_delta": 0, "raw": ""}
        except httpx.ConnectError:
            bot_logger.api_error(f"API 连接失败: {self.api_base_url}")
            return {"reply": "⚠️ 无法连接到 AI 服务，请检查网络或 API 地址配置。", "affinity_delta": 0, "raw": ""}
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            bot_logger.api_error(f"API 响应解析失败: {e}")
            return {"reply": "⚠️ AI 服务返回格式异常，请稍后再试。", "affinity_delta": 0, "raw": ""}
        except Exception as e:
            bot_logger.exception(f"AI 聊天发生未知错误 (用户 {user_id}): {e}")
            return {"reply": f"⚠️ 发生未知错误: {type(e).__name__}", "affinity_delta": 0, "raw": ""}

    async def check_api_balance(self) -> dict:
        """
        检查 API 余额/状态（尽力而为，不同平台接口不同）
        返回: {"status": "ok"/"warning"/"error", "message": "..."}
        """
        if not self.api_key:
            return {"status": "error", "message": "API Key 未配置"}

        url = f"{self.api_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
            "thinking": {"type": "disabled"},
        }
        try:
            client = self._get_client()
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return {"status": "ok", "message": "API 连接正常"}
            elif response.status_code == 401:
                return {"status": "error", "message": "API Key 无效"}
            elif response.status_code in (402, 429):
                return {"status": "warning", "message": "余额不足或配额耗尽"}
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": f"连接失败: {e}"}

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# 全局 AI 聊天管理器
ai_chat = AIChatManager()
