"""
Text 文档指令插件
- 识别自定义格式指令（默认 #文档名），读取 text/ 目录下对应文档回复
- /text <文档名> - 直接读取指定文档
- /textlist - 列出所有可用文档
- /textreload - 重新扫描文档目录
"""
from nonebot import on_message, on_command
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, Message
from nonebot.params import CommandArg

from core import text_docs, bot_logger
from config.settings import settings


def _reply(event: MessageEvent, text: str):
    """构造回复（群聊带引用）"""
    if isinstance(event, GroupMessageEvent):
        from nonebot.adapters.onebot.v11 import MessageSegment
        return MessageSegment.reply(event.message_id) + text
    return text


# ========== 自动匹配自定义格式指令 ==========
text_matcher = on_message(priority=8, block=False)


@text_matcher.handle()
async def handle_text_command(event: MessageEvent):
    raw = event.get_plaintext().strip()
    if not raw:
        return

    result = text_docs.match_and_read(raw)
    if result:
        doc_name, content = result
        source = f"群 {event.group_id}" if isinstance(event, GroupMessageEvent) else "私聊"
        bot_logger.info(f"[Text文档] {source} 读取: {doc_name}")
        await text_matcher.finish(_reply(event, content))


# ========== /text 直接读取 ==========
text_cmd = on_command("text", priority=10, block=True)


@text_cmd.handle()
async def handle_text(event: MessageEvent, args: Message = CommandArg()):
    name = args.extract_plain_text().strip()
    if not name:
        await text_cmd.finish(_reply(event, f"用法：/text <文档名>\n{text_docs.get_doc_list_text()}"))
        return

    content = text_docs.read_doc(name)
    if content is not None:
        await text_cmd.finish(_reply(event, content))
    else:
        await text_cmd.finish(_reply(event, f"未找到文档「{name}」\n{text_docs.get_doc_list_text()}"))


# ========== /textlist 列出文档 ==========
textlist_cmd = on_command("textlist", priority=10, block=True)


@textlist_cmd.handle()
async def handle_textlist(event: MessageEvent):
    await textlist_cmd.finish(_reply(event, text_docs.get_doc_list_text()))


# ========== /textreload 重载 ==========
textreload_cmd = on_command("textreload", priority=10, block=True)


@textreload_cmd.handle()
async def handle_textreload(event: MessageEvent):
    text_docs.reload()
    count = len(text_docs.list_docs())
    await textreload_cmd.finish(_reply(event, f"文档目录已重新扫描，当前 {count} 个文档。"))
