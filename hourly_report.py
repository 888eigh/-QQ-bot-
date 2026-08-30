#!/usr/bin/env python3
"""
每小时日志报告生成器
- 收集最近1小时运行日志、错误日志、API日志
- 检查Bot进程状态
- 生成HTML格式报告
- 支持邮件推送 / Webhook推送 / 本地保存
"""
import os
import sys
import json
import smtplib
import urllib.request
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime, timedelta
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# 推送配置（从环境变量或配置文件读取）
CONFIG_FILE = BASE_DIR / "config" / "report_config.json"

def load_config():
    """加载推送配置"""
    default = {
        "push_method": "local",  # local / email / webhook
        "email": {
            "smtp_server": "smtp.qq.com",
            "smtp_port": 465,
            "sender": "",
            "password": "",  # 授权码
            "receiver": ""
        },
        "webhook": {
            "url": "",  # Server酱 / 飞书 / 钉钉 Webhook
            "type": "serverchan"  # serverchan / feishu / dingtalk
        },
        "local_save_path": ""  # 本地保存路径（仅作记录，实际保存在reports目录）
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                for k, v in user_cfg.items():
                    if isinstance(v, dict) and k in default:
                        default[k].update(v)
                    else:
                        default[k] = v
        except Exception as e:
            print(f"读取配置失败: {e}")
    return default

def read_log_file(filename, hours=1):
    """读取最近N小时的日志内容"""
    log_path = LOGS_DIR / filename
    if not log_path.exists():
        return []
    cutoff = datetime.now() - timedelta(hours=hours)
    lines = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                # 尝试解析时间戳
                try:
                    time_str = line[:19]
                    log_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    if log_time >= cutoff:
                        lines.append(line.rstrip())
                except:
                    # nonebot格式的日志（08-30 12:05:01）
                    try:
                        time_str = line[:14]
                        log_time = datetime.strptime(f"{datetime.now().year}-{time_str}", "%Y-%m-%d %H:%M:%S")
                        if log_time >= cutoff:
                            lines.append(line.rstrip())
                    except:
                        lines.append(line.rstrip())
    except Exception as e:
        lines.append(f"读取日志失败: {e}")
    return lines

def check_bot_status():
    """检查Bot进程状态"""
    import subprocess
    try:
        result = subprocess.run(["pgrep", "-f", "bot.py"], capture_output=True, text=True)
        pids = result.stdout.strip().split("\n") if result.stdout.strip() else []
        # 过滤掉grep自身
        pids = [p for p in pids if p]
        return {"running": len(pids) > 0, "pids": pids}
    except Exception as e:
        return {"running": False, "error": str(e)}

def check_port(port=8083):
    """检查端口是否在监听"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        return result == 0
    except:
        return False

def generate_report():
    """生成日志报告"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    report_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # 收集日志
    bot_logs = read_log_file(f"bot_{today_str}.log", hours=1)
    error_logs = read_log_file(f"error_{today_str}.log", hours=1)
    api_logs = read_log_file(f"api_{today_str}.log", hours=1)

    # 检查状态
    bot_status = check_bot_status()
    port_status = check_port()

    # 统计
    error_count = len(error_logs)
    api_count = len(api_logs)
    bot_log_count = len(bot_logs)

    # 生成HTML报告
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>QQ Bot 每小时报告 - {report_time}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; border-radius: 8px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4A90D9; padding-bottom: 10px; }}
        .status-card {{ display: flex; gap: 16px; margin: 16px 0; }}
        .status-item {{ flex: 1; padding: 16px; border-radius: 6px; text-align: center; }}
        .status-ok {{ background: #e8f5e9; color: #2e7d32; }}
        .status-error {{ background: #ffebee; color: #c62828; }}
        .status-warn {{ background: #fff3e0; color: #e65100; }}
        .status-value {{ font-size: 24px; font-weight: bold; }}
        .status-label {{ font-size: 12px; margin-top: 4px; }}
        h2 {{ color: #555; margin-top: 24px; border-left: 4px solid #4A90D9; padding-left: 10px; }}
        pre {{ background: #f8f8f8; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 12px; line-height: 1.5; max-height: 400px; overflow-y: auto; }}
        .empty {{ color: #999; font-style: italic; padding: 12px; }}
        .footer {{ margin-top: 24px; padding-top: 12px; border-top: 1px solid #eee; color: #999; font-size: 12px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>QQ Bot 每小时运行报告</h1>
        <p style="color: #666;">报告时间: {report_time} | 统计周期: 最近1小时</p>

        <div class="status-card">
            <div class="status-item {'status-ok' if bot_status['running'] else 'status-error'}">
                <div class="status-value">{'运行中' if bot_status['running'] else '已停止'}</div>
                <div class="status-label">Bot进程状态</div>
            </div>
            <div class="status-item {'status-ok' if port_status else 'status-error'}">
                <div class="status-value">{'正常' if port_status else '异常'}</div>
                <div class="status-label">端口监听(8083)</div>
            </div>
            <div class="status-item {'status-error' if error_count > 0 else 'status-ok'}">
                <div class="status-value">{error_count}</div>
                <div class="status-label">错误日志数</div>
            </div>
            <div class="status-item status-warn">
                <div class="status-value">{api_count}</div>
                <div class="status-label">API调用数</div>
            </div>
        </div>

        <h2>运行日志（最近1小时，共{bot_log_count}条）</h2>
        {f'<pre>{"".join(bot_logs[-50:])}</pre>' if bot_logs else '<div class="empty">暂无运行日志</div>'}

        <h2>错误日志（最近1小时，共{error_count}条）</h2>
        {f'<pre>{"".join(error_logs[-50:])}</pre>' if error_logs else '<div class="empty">无错误日志，运行正常</div>'}

        <h2>API日志（最近1小时，共{api_count}条）</h2>
        {f'<pre>{"".join(api_logs[-50:])}</pre>' if api_logs else '<div class="empty">暂无API调用记录</div>'}

        <div class="footer">
            QQ Bot 自动报告系统 | 生成时间: {report_time}<br>
            如有异常请检查服务器状态或联系管理员
        </div>
    </div>
</body>
</html>
    """

    # 保存报告
    report_filename = f"report_{now.strftime('%Y%m%d_%H%M%S')}.html"
    report_path = REPORTS_DIR / report_filename
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    # 同时生成纯文本版本
    txt_content = f"""QQ Bot 每小时运行报告
报告时间: {report_time}
统计周期: 最近1小时
{'='*50}

【运行状态】
Bot进程: {'运行中 (PID: ' + ','.join(bot_status.get('pids',[])) + ')' if bot_status['running'] else '已停止 ⚠️'}
端口监听: {'正常' if port_status else '异常 ⚠️'}
错误日志: {error_count}条
API调用: {api_count}条

{'='*50}
【运行日志】
{chr(10).join(bot_logs[-50:]) if bot_logs else '（暂无）'}

{'='*50}
【错误日志】
{chr(10).join(error_logs[-50:]) if error_logs else '（无错误）'}

{'='*50}
【API日志】
{chr(10).join(api_logs[-50:]) if api_logs else '（暂无）'}
"""
    txt_path = REPORTS_DIR / f"report_{now.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)

    return {
        "html_path": str(report_path),
        "txt_path": str(txt_path),
        "bot_running": bot_status["running"],
        "error_count": error_count,
        "api_count": api_count,
        "report_time": report_time,
        "txt_content": txt_content
    }

def push_email(config, report):
    """通过邮件推送报告"""
    email_cfg = config["email"]
    if not email_cfg["sender"] or not email_cfg["receiver"]:
        print("邮件配置不完整，跳过邮件推送")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = email_cfg["sender"]
        msg["To"] = email_cfg["receiver"]
        subject = f"QQ Bot 报告 - {report['report_time']} {'⚠️有错误' if report['error_count'] > 0 else '✅正常'}"
        msg["Subject"] = Header(subject, "utf-8")

        # 正文
        body = MIMEText(report["txt_content"], "plain", "utf-8")
        msg.attach(body)

        # HTML附件
        with open(report["html_path"], "r", encoding="utf-8") as f:
            html_attach = MIMEText(f.read(), "html", "utf-8")
            html_attach.add_header("Content-Disposition", "attachment", filename="report.html")
            msg.attach(html_attach)

        # 发送
        server = smtplib.SMTP_SSL(email_cfg["smtp_server"], email_cfg["smtp_port"])
        server.login(email_cfg["sender"], email_cfg["password"])
        server.sendmail(email_cfg["sender"], email_cfg["receiver"], msg.as_string())
        server.quit()
        print(f"邮件已发送到 {email_cfg['receiver']}")
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False

def push_webhook(config, report):
    """通过Webhook推送报告"""
    webhook_cfg = config["webhook"]
    if not webhook_cfg["url"]:
        print("Webhook URL未配置，跳过推送")
        return False

    try:
        wtype = webhook_cfg["type"]
        title = f"QQ Bot 报告 - {report['report_time']}"
        content = report["txt_content"]

        if wtype == "serverchan":
            # Server酱
            data = urllib.parse.urlencode({"title": title, "desp": content}).encode()
            req = urllib.request.Request(webhook_cfg["url"], data=data)
            urllib.request.urlopen(req, timeout=10)

        elif wtype == "feishu":
            # 飞书
            payload = json.dumps({
                "msg_type": "text",
                "content": {"text": f"{title}\n\n{content}"}
            }).encode()
            req = urllib.request.Request(webhook_cfg["url"], data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)

        elif wtype == "dingtalk":
            # 钉钉
            payload = json.dumps({
                "msgtype": "text",
                "text": {"content": f"{title}\n\n{content}"}
            }).encode()
            req = urllib.request.Request(webhook_cfg["url"], data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)

        print(f"Webhook推送成功 ({wtype})")
        return True
    except Exception as e:
        print(f"Webhook推送失败: {e}")
        return False

def main():
    print("=" * 50)
    print("QQ Bot 每小时日志报告生成器")
    print("=" * 50)

    config = load_config()
    report = generate_report()

    print(f"\n报告已生成: {report['html_path']}")
    print(f"Bot状态: {'运行中' if report['bot_running'] else '已停止 ⚠️'}")
    print(f"错误数: {report['error_count']}")
    print(f"API调用: {report['api_count']}")

    # 推送
    method = config.get("push_method", "local")
    print(f"\n推送方式: {method}")

    if method == "email":
        push_email(config, report)
    elif method == "webhook":
        push_webhook(config, report)
    else:
        print("本地保存模式，报告已保存到 reports/ 目录")

    # 清理超过7天的报告
    cutoff = datetime.now() - timedelta(days=7)
    for f in REPORTS_DIR.glob("report_*"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
        except:
            pass

    print("\n完成!")

if __name__ == "__main__":
    main()
