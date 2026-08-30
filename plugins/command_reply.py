"""
本地文档指令回复插件
- 用户发送 /XXX 时，自动匹配 commands.json 中的标识符并回复
- /docs - 查看所有可用文档指令
- /reload_docs - 热重载指令文档（管理员）
- /add_doc <指令> <内容> - 添加指令（管理员）
- /del_doc <指令> - 删除指令（管理员）
"""
from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    GroupMessageEvent,
    Message,
    MessageSegment,
)
from nonebot.params import CommandArg

from core import doc_replier, bot_logger
from config.settings import settings

# 已被专门注册的命令（这些不走文档匹配）
_RESERVED_COMMANDS = {
    "docs", "reload_docs", "add_doc", "del_doc",
    "ping", "echo", "chat", "clear", "reset",
    "help",
}


# ========== 通用文档指令匹配 ==========
# 用 on_message 捕获所有消息，手动解析斜杠命令
doc_matcher = on_message(priority=5, block=False)


@doc_matcher.handle()
async def handle_doc_command(event: MessageEvent):
    raw_msg = event.get_plaintext().strip()

    # 只处理以 / 开头的消息
    if not raw_msg or not raw_msg.startswith("/"):
        return

    # 提取命令名（/hello world → hello）
    parts = raw_msg[1:].split(maxsplit=1)
    command = parts[0].lower().strip() if parts else ""

    if not command or command in _RESERVED_COMMANDS:
        return

    # 检查是否是文档指令
    reply = doc_replier.get_reply(command)
    if reply is not None:
        source = f"群 {event.group_id}" if isinstance(event, GroupMessageEvent) else "私聊"
        bot_logger.info(f"[文档指令] {source} /{command}")
        if isinstance(event, GroupMessageEvent):
            await doc_matcher.finish(MessageSegment.reply(event.message_id) + reply)
        else:
            await doc_matcher.finish(reply)


# ========== /docs 列出所有指令 ==========
docs_cmd = on_command("docs", priority=10, block=True)


@docs_cmd.handle()
async def handle_docs(event: MessageEvent):
    text = doc_replier.get_command_list_text()
    if isinstance(event, GroupMessageEvent):
        await docs_cmd.finish(MessageSegment.reply(event.message_id) + text)
    else:
        await docs_cmd.finish(text)


# ========== /reload_docs 重载指令文档 ==========
reload_cmd = on_command("reload_docs", priority=10, block=True)


@reload_cmd.handle()
async def handle_reload_docs(event: MessageEvent):
    user_id = str(event.user_id)
    superusers = settings.get("superusers", [])
    if user_id not in [str(s) for s in superusers]:
        await reload_cmd.finish("⚠️ 只有管理员可以执行此操作。")

    count = doc_replier.reload()
    bot_logger.info(f"管理员 {user_id} 重载了指令文档，当前 {count} 条")
    await reload_cmd.finish(f"✅ 指令文档已重载，当前共 {count} 条指令。")


# ========== /add_doc 添加指令 ==========
add_doc_cmd = on_command("add_doc", priority=10, block=True)


@add_doc_cmd.handle()
async def handle_add_doc(event: MessageEvent, args: Message = CommandArg()):
    user_id = str(event.user_id)
    superusers = settings.get("superusers", [])
    if user_id not in [str(s) for s in superusers]:
        await add_doc_cmd.finish("⚠️ 只有管理员可以执行此操作。")

    text = args.extract_plain_text().strip()
    if not text or " " not in text:
        await add_doc_cmd.finish(
            "用法：/add_doc <指令名> <内容>\n例如：/add_doc welcome 欢迎来到本群！"
        )

    command, content = text.split(" ", 1)
    command = command.strip().lower()
    content = content.strip()

    if not command or not content:
        await add_doc_cmd.finish("⚠️ 指令名和内容都不能为空。")

    success = doc_replier.add_command(command, content)
    if success:
        bot_logger.info(f"管理员 {user_id} 添加/更新了指令 /{command}")
        await add_doc_cmd.finish(f"✅ 已添加/更新指令 /{command}")
    else:
        await add_doc_cmd.finish("⚠️ 保存指令失败，请检查日志。")


# ========== /del_doc 删除指令 ==========
del_doc_cmd = on_command("del_doc", priority=10, block=True)


@del_doc_cmd.handle()
async def handle_del_doc(event: MessageEvent, args: Message = CommandArg()):
    user_id = str(event.user_id)
    superusers = settings.get("superusers", [])
    if user_id not in [str(s) for s in superusers]:
        await del_doc_cmd.finish("⚠️ 只有管理员可以执行此操作。")

    command = args.extract_plain_text().strip().lower()
    if not command:
        await del_doc_cmd.finish("用法：/del_doc <指令名>\n例如：/del_doc welcome")

    if doc_replier.remove_command(command):
        bot_logger.info(f"管理员 {user_id} 删除了指令 /{command}")
        await del_doc_cmd.finish(f"✅ 已删除指令 /{command}")
    else:
        await del_doc_cmd.finish(f"⚠️ 指令 /{command} 不存在。")
