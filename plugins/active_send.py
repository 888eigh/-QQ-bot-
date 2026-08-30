"""
主动消息插件
- 不定时从 boring.txt 随机选句发送到指定群
- 管理员命令控制
"""
from nonebot import on_command, get_driver
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, Message
from nonebot.params import CommandArg

from core import active_sender, bot_logger
from config.settings import settings

driver = get_driver()


@driver.on_bot_connect
async def _on_bot_connect(bot):
    """Bot 连接时设置实例并自动启动（如果已启用）"""
    active_sender.set_bot(bot)
    bot_logger.info(f"[主动消息] Bot 已连接: {bot.self_id}")
    if active_sender.enabled and active_sender.target_group:
        active_sender.start()


@driver.on_bot_disconnect
async def _on_bot_disconnect(bot):
    """Bot 断开时停止"""
    active_sender.stop()


# ========== /boring 命令组 ==========
boring_cmd = on_command("boring", priority=10, block=True)


@boring_cmd.handle()
async def handle_boring(event: MessageEvent, args: Message = CommandArg()):
    user_id = str(event.user_id)
    superusers = [str(s) for s in settings.get("superusers", [])]

    # 非管理员只能看状态
    is_admin = user_id in superusers

    parts = args.extract_plain_text().strip().split()
    sub_cmd = parts[0].lower() if parts else "status"

    if sub_cmd == "status":
        await boring_cmd.finish(active_sender.get_status_text())

    if not is_admin:
        await boring_cmd.finish("⚠️ 只有管理员可以操作主动消息功能。")

    if sub_cmd == "on":
        if not active_sender.target_group:
            await boring_cmd.finish("⚠️ 请先设置目标群：/boring set <群号>")
        if active_sender.start():
            await boring_cmd.finish("✅ 主动消息已开启，将在随机间隔后发送。")
        else:
            await boring_cmd.finish("❌ 启动失败，请检查日志。")

    elif sub_cmd == "off":
        active_sender.stop()
        await boring_cmd.finish("⏹️ 主动消息已停止。")

    elif sub_cmd == "now":
        if not active_sender.target_group:
            await boring_cmd.finish("⚠️ 请先设置目标群：/boring set <群号>")
        success = await active_sender.send_now()
        await boring_cmd.finish("✅ 已立即发送一条。" if success else "❌ 发送失败。")

    elif sub_cmd == "set":
        if len(parts) < 2:
            await boring_cmd.finish("用法：/boring set <群号>")
        try:
            group_id = int(parts[1])
            active_sender.set_target_group(group_id)
            await boring_cmd.finish(f"✅ 目标群已设置为: {group_id}")
        except ValueError:
            await boring_cmd.finish("⚠️ 群号必须是数字。")

    elif sub_cmd == "interval":
        if len(parts) < 3:
            await boring_cmd.finish("用法：/boring interval <最小秒数> <最大秒数>")
        try:
            min_s = int(parts[1])
            max_s = int(parts[2])
            active_sender.set_interval(min_s, max_s)
            await boring_cmd.finish(f"✅ 间隔已设置: {min_s}~{max_s} 秒")
        except ValueError:
            await boring_cmd.finish("⚠️ 间隔必须是数字。")

    elif sub_cmd == "reload":
        count = active_sender.reload_messages()
        await boring_cmd.finish(f"✅ boring.txt 已重新加载，共 {count} 条消息。")

    else:
        await boring_cmd.finish(
            "【主动消息命令】\n"
            "/boring status - 查看状态\n"
            "/boring on - 开启\n"
            "/boring off - 关闭\n"
            "/boring now - 立即发一条\n"
            "/boring set <群号> - 设置目标群\n"
            "/boring interval <最小> <最大> - 设置间隔(秒)\n"
            "/boring reload - 重新加载 boring.txt"
        )
