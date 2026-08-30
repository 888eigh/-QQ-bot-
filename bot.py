"""
QQ Bot 主入口 - NoneBot2
集成自适应端口、UTF-8日志、AI聊天、文档指令回复
"""
import os
import sys

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

from core import port_manager, bot_logger, napcat_config
from config.settings import settings


def setup_environment():
    """配置运行环境（端口等）"""
    # 自适应端口
    port = port_manager.get_port()
    host = settings.get("bot_host", "0.0.0.0")

    # 首次启动自动配置 NapCat 反向 WebSocket 端口
    nc_result = napcat_config.auto_configure(bot_port=port, bot_host="127.0.0.1")
    if nc_result["success"] and nc_result["config_path"]:
        bot_logger.info(f"[NapCat] {nc_result['message']}")
    elif not nc_result["success"]:
        bot_logger.warning(f"[NapCat] {nc_result['message']}")

    # 设置环境变量供 NoneBot 读取
    os.environ["HOST"] = host
    os.environ["PORT"] = str(port)
    os.environ["DRIVER"] = "~fastapi"

    bot_logger.info(f"=" * 50)
    bot_logger.info(f"QQ Bot 启动中...")
    bot_logger.info(f"监听地址: {host}:{port}")
    bot_logger.info(f"WebSocket: ws://127.0.0.1:{port}/onebot/v11/ws")
    bot_logger.info(f"AI模型: {settings.get('api_model', 'deepseek-v4-flash')} (思考模式: {'关闭' if settings.get('api_thinking_disabled', True) else '开启'})")
    bot_logger.info(f"日志级别: {settings.get('log_level', 'INFO')}")
    bot_logger.info(f"=" * 50)

    return port


def main():
    """主函数"""
    setup_environment()

    # 初始化 NoneBot
    nonebot.init()

    driver = nonebot.get_driver()
    driver.register_adapter(OneBotV11Adapter)

    # 加载插件
    nonebot.load_from_toml("pyproject.toml")

    # 启动
    nonebot.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        bot_logger.info("收到中断信号，正在关闭...")
    except Exception as e:
        bot_logger.exception(f"Bot 运行异常: {e}")
        sys.exit(1)
