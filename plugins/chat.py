"""
AI 聊天插件 V3
- 私聊/群聊@ 直接对话
- AI 一并返回回复内容和好感度变化（单次API调用）
- 动态性格注入、好感度系统、多媒体回复
- /chat <内容> - 主动对话
- /clear - 清除对话历史和好感度
- /personality [性格名] - 查看/设定性格
- /affinity - 查看好感度
- /media - 查看可用图片和表情
"""
from nonebot import on_message, on_command
from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    GroupMessageEvent,
    PrivateMessageEvent,
    Message,
    MessageSegment,
)
from nonebot.params import CommandArg
from nonebot.rule import to_me
from core import ai_chat, bot_logger, affinity, personality, media_manager
from config.settings import settings

chat_enabled = settings.get("chat_enabled", True)
group_enabled = settings.get("chat_group_enabled", True)
private_enabled = settings.get("chat_private_enabled", True)


async def _send_reply(event: MessageEvent, text: str):
    """发送回复，自动解析并发送媒体"""
    clean_text, media_files = media_manager.parse_and_get_media(text)
    msg = Message()
    if clean_text:
        msg.append(MessageSegment.text(clean_text))
    for media_path in media_files:
        try:
            file_uri = f"file://{media_path.absolute()}"
            msg.append(MessageSegment.image(file_uri))
        except Exception as e:
            bot_logger.error(f"发送图片失败 {media_path}: {e}")
    if isinstance(event, GroupMessageEvent):
        msg = MessageSegment.reply(event.message_id) + msg
    await event.reply(msg)


async def _handle_chat(event: MessageEvent, text: str):
    """处理 AI 对话的通用逻辑（AI一并返回好感度）"""
    if not chat_enabled:
        await _send_reply(event, "AI 聊天功能未启用。")
        return
    user_id = str(event.user_id)
    source = f"群 {event.group_id}" if isinstance(event, GroupMessageEvent) else "私聊"
    bot_logger.info(f"[AI对话] {source} 用户 {user_id}: {text[:50]}")
    try:
        # AI 返回: {"reply": "...", "affinity_delta": 5}
        result = await ai_chat.chat(user_id, text)
        reply = result.get("reply", "")
        affinity_delta = result.get("affinity_delta", 0)
        # 应用好感度变化（由AI返回，无需额外API调用）
        if affinity_delta != 0:
            affinity.apply_delta(user_id, affinity_delta)
        await _send_reply(event, reply)
    except Exception as e:
        bot_logger.exception(f"AI 回复失败: {e}")
        await _send_reply(event, "处理消息时发生错误，请稍后再试。")


# ========== 私聊直接对话 ==========
if chat_enabled and private_enabled:
    private_chat = on_message(priority=99, block=False)

    @private_chat.handle()
    async def handle_private(event: PrivateMessageEvent):
        raw = event.get_plaintext().strip()
        if not raw or raw.startswith("/") or raw.startswith("#"):
            return
        await _handle_chat(event, raw)


# ========== 群聊 @机器人 对话 ==========
if chat_enabled and group_enabled:
    group_chat = on_message(rule=to_me(), priority=99, block=False)

    @group_chat.handle()
    async def handle_group(event: GroupMessageEvent):
        raw = event.get_plaintext().strip()
        if not raw or raw.startswith("/") or raw.startswith("#"):
            return
        await _handle_chat(event, raw)


# ========== /chat 命令 ==========
chat_cmd = on_command("chat", priority=10, block=True)


@chat_cmd.handle()
async def handle_chat_cmd(event: MessageEvent, args: Message = CommandArg()):
    text = args.extract_plain_text().strip()
    if not text:
        await _send_reply(event, "用法：/chat <你想说的话>")
        return
    await _handle_chat(event, text)


# ========== /clear 清除历史 ==========
clear_cmd = on_command("clear", priority=10, block=True)


@clear_cmd.handle()
async def handle_clear(event: MessageEvent):
    user_id = str(event.user_id)
    ai_chat.clear_session(user_id)
    affinity.reset(user_id)
    await _send_reply(event, "已清除你的对话历史和好感度。")


# ========== /personality 性格设定 ==========
personality_cmd = on_command("personality", aliases={"性格"}, priority=10, block=True)


@personality_cmd.handle()
async def handle_personality(event: MessageEvent, args: Message = CommandArg()):
    user_id = str(event.user_id)
    name = args.extract_plain_text().strip()
    if not name:
        current = personality.get_user_personality(user_id)
        info = personality.get_personality_info(current)
        desc = info.get("description", "") if info else ""
        text = f"当前性格：{current}\n{desc}\n\n{personality.get_personality_list_text()}"
        await _send_reply(event, text)
        return
    if personality.set_user_personality(user_id, name):
        ai_chat.clear_session(user_id)
        await _send_reply(event, f"性格已切换为：{name}\n（对话历史已清除，新性格将生效）")
    else:
        await _send_reply(event, f"未找到性格「{name}」\n{personality.get_personality_list_text()}")


# ========== /affinity 好感度查询 ==========
affinity_cmd = on_command("affinity", aliases={"好感度"}, priority=10, block=True)


@affinity_cmd.handle()
async def handle_affinity(event: MessageEvent):
    user_id = str(event.user_id)
    text = affinity.get_affinity_text(user_id)
    await _send_reply(event, text)


# ========== /media 查看媒体资源 ==========
media_cmd = on_command("media", aliases={"图片", "表情"}, priority=10, block=True)


@media_cmd.handle()
async def handle_media(event: MessageEvent):
    pics = media_manager.list_pictures()
    emos = media_manager.list_emotionals()
    lines = ["【可用媒体资源】"]
    if pics:
        lines.append(f"图片 ({len(pics)}): {', '.join(pics[:10])}")
    if emos:
        lines.append(f"表情 ({len(emos)}): {', '.join(emos[:10])}")
    if not pics and not emos:
        lines.append("暂无图片和表情，请将文件放入 picture/ 或 emotional/ 目录。")
    lines.append("\nAI 会根据对话内容自动选择使用。")
    await _send_reply(event, "\n".join(lines))


# ========== /addpersonality 自定义性格 ==========
add_personality_cmd = on_command("addpersonality", aliases={"添加性格", "自定义性格"}, priority=10, block=True)


@add_personality_cmd.handle()
async def handle_add_personality(event: MessageEvent, args: Message = CommandArg()):
    """
    添加自定义性格
    格式：/addpersonality 名称|描述|性格设定prompt
    示例：/addpersonality 猫娘|可爱的猫耳少女|你是一个可爱的猫耳少女，说话结尾会加"喵"...
    """
    text = args.extract_plain_text().strip()
    if not text:
        help_text = (
            "【添加自定义性格】\n"
            "格式：/addpersonality 名称|描述|性格设定\n\n"
            "示例：\n"
            "/addpersonality 猫娘|可爱的猫耳少女|你是一个可爱的猫耳少女，说话结尾会加喵，喜欢蹭人，会用可爱的语气说话。\n\n"
            "注意：用 | 分隔三部分，性格设定要详细描述AI的说话方式、口头禅、行为模式。"
        )
        await _send_reply(event, help_text)
        return
    parts = text.split("|", 2)
    if len(parts) < 3:
        await _send_reply(event, "格式错误！需要用 | 分隔三部分：名称|描述|性格设定")
        return
    p_name = parts[0].strip()
    p_desc = parts[1].strip()
    p_prompt = parts[2].strip()
    if not p_name or not p_prompt:
        await _send_reply(event, "性格名称和设定不能为空！")
        return
    if personality.add_custom_personality(p_name, p_desc, p_prompt):
        user_id = str(event.user_id)
        personality.set_user_personality(user_id, p_name)
        ai_chat.clear_session(user_id)
        await _send_reply(event, f"✅ 自定义性格「{p_name}」已创建并为你启用！\n对话历史已清除，新性格将生效。")
    else:
        await _send_reply(event, "创建失败，请检查格式是否正确。")
