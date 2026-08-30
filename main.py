#!/usr/bin/env python3
"""
QQ Bot 统一启动入口
用法:
  python3 main.py          # 自动检测环境，有GUI则启动GUI，否则命令行启动Bot
  python3 main.py bot      # 直接启动 Bot（命令行模式）
  python3 main.py gui      # 强制启动 GUI 管理面板
  python3 main.py napcat   # 仅启动 NapCat
  python3 main.py status   # 查看状态
"""
import os
import sys
import argparse
import threading
import time

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings, BASE_DIR
from core import bot_logger, port_manager, ai_chat, doc_replier


def has_gui_display() -> bool:
    """检测是否有可用的图形显示"""
    if sys.platform == "win32" or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY"))


def start_napcat_if_configured():
    """如果配置了自动启动，则启动 NapCat"""
    if not settings.get("napcat_auto_start", False):
        return
    try:
        from napcat_launcher import napcat_launcher
        if napcat_launcher.start():
            bot_logger.info("NapCat 已自动启动")
            # 等待 NapCat 初始化
            time.sleep(5)
        else:
            bot_logger.warning("NapCat 自动启动失败")
    except Exception as e:
        bot_logger.exception(f"NapCat 自动启动异常: {e}")


def run_bot():
    """运行 Bot 主进程"""
    bot_logger.info("正在启动 QQ Bot...")

    # 自适应端口
    port = port_manager.get_port()
    bot_logger.info(f"最终监听端口: {port}")

    # 启动 NapCat（如果配置了）
    start_napcat_if_configured()

    # 启动 NoneBot
    try:
        import bot
        bot.main()
    except KeyboardInterrupt:
        bot_logger.info("收到中断信号，Bot 已停止")
    except Exception as e:
        bot_logger.exception(f"Bot 运行异常: {e}")
        sys.exit(1)


def run_gui():
    """启动 GUI 管理面板"""
    try:
        from gui import launch_gui
        launch_gui()
    except ImportError as e:
        bot_logger.error(f"GUI 模块导入失败: {e}")
        print("错误: 无法启动 GUI，请确保 tkinter 已安装")
        print("在 Ubuntu/Debian 上: sudo apt install python3-tk")
        sys.exit(1)


def run_napcat_only():
    """仅启动 NapCat"""
    try:
        from napcat_launcher import napcat_launcher
        if napcat_launcher.start():
            print("NapCat 已启动，按 Ctrl+C 停止...")
            try:
                while napcat_launcher.is_running():
                    time.sleep(1)
            except KeyboardInterrupt:
                napcat_launcher.stop()
        else:
            print("NapCat 启动失败，请检查配置和日志")
            sys.exit(1)
    except Exception as e:
        bot_logger.exception(f"NapCat 启动异常: {e}")
        sys.exit(1)


def show_status():
    """显示当前状态"""
    print("=" * 55)
    print("  QQ Bot 状态信息")
    print("=" * 55)
    print(f"  项目目录:   {BASE_DIR}")
    print(f"  配置文件:   {BASE_DIR / 'config' / 'config.json'}")
    print(f"  日志目录:   {BASE_DIR / 'logs'}")
    print(f"  监听主机:   {settings.get('bot_host', '0.0.0.0')}")
    print(f"  默认端口:   {settings.get('bot_port', 8080)}")
    print(f"  自适应端口: {'开启' if settings.get('auto_port', True) else '关闭'}")
    print(f"  可用端口:   {port_manager.get_port()}")
    print(f"  API 地址:   {settings.get('api_base_url', '-')}")
    print(f"  API Key:    {'已配置' if settings.get('api_key') else '未配置'}")
    print(f"  AI 模型:    {settings.get('api_model', '-')}")
    print(f"  文档指令:   {len(doc_replier.list_commands())} 条")
    print(f"  NapCat路径: {settings.get('napcat_path') or '未配置'}")
    print(f"  自动启动:   {'开启' if settings.get('napcat_auto_start', False) else '关闭'}")
    print("=" * 55)
    print("  可用指令:")
    for cmd in doc_replier.list_commands():
        print(f"    /{cmd}")
    print("=" * 55)


def main():
    parser = argparse.ArgumentParser(description="QQ Bot - 基于 NoneBot2 + NapCat")
    parser.add_argument(
        "mode",
        nargs="?",
        default="auto",
        choices=["auto", "bot", "gui", "napcat", "status"],
        help="启动模式: auto(默认) / bot / gui / napcat / status"
    )
    args = parser.parse_args()

    if args.mode == "status":
        show_status()
    elif args.mode == "bot":
        run_bot()
    elif args.mode == "gui":
        run_gui()
    elif args.mode == "napcat":
        run_napcat_only()
    else:  # auto
        if has_gui_display():
            bot_logger.info("检测到图形环境，启动 GUI 管理面板")
            run_gui()
        else:
            bot_logger.info("未检测到图形环境，使用命令行模式启动 Bot")
            run_bot()


if __name__ == "__main__":
    main()
