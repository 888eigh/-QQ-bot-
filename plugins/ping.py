from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent, Message
from nonebot.params import CommandArg

# 简单的 ping 测试插件
ping = on_command("ping", priority=10, block=True)


@ping.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    user_id = event.user_id
    msg_type = "群聊" if event.message_type == "group" else "私聊"
    await ping.finish(f"pong! 🏓\n用户: {user_id}\n来源: {msg_type}")


# 回声测试
echo = on_command("echo", priority=10, block=True)


@echo.handle()
async def _(args: Message = CommandArg()):
    text = args.extract_plain_text().strip()
    if not text:
        await echo.finish("echo 后面要跟内容哦，比如 /echo 你好")
    await echo.finish(text)
