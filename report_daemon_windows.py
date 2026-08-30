#!/usr/bin/env python3
"""
报告守护进程（Windows版）
每小时运行一次日志报告生成
运行: python report_daemon_windows.py
"""
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
REPORT_SCRIPT = BASE_DIR / "hourly_report.py"
PID_FILE = BASE_DIR / "report_daemon.pid"
LOG_FILE = BASE_DIR / "logs" / "report_daemon.log"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_report():
    log("开始生成每小时报告...")
    try:
        result = subprocess.run(
            [sys.executable, str(REPORT_SCRIPT)],
            capture_output=True, text=True, timeout=120,
            cwd=str(BASE_DIR)
        )
        if result.returncode == 0:
            log("报告生成成功")
        else:
            log(f"报告生成失败，返回码: {result.returncode}")
            log(f"错误: {result.stderr[-300:]}")
    except Exception as e:
        log(f"报告生成异常: {e}")

def main():
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    log(f"报告守护进程启动，PID: {os.getpid()}")
    log("每小时整点生成一次报告")

    run_report()

    while True:
        try:
            now = datetime.now()
            next_hour = now.replace(minute=0, second=0, microsecond=0)
            if next_hour <= now:
                next_hour = next_hour.replace(hour=next_hour.hour + 1)
            wait_seconds = (next_hour - now).total_seconds()
            log(f"下次报告时间: {next_hour.strftime('%Y-%m-%d %H:%M:%S')}，等待 {wait_seconds:.0f} 秒")
            time.sleep(wait_seconds)
            run_report()
        except KeyboardInterrupt:
            log("收到中断信号，退出")
            break
        except Exception as e:
            log(f"守护进程异常: {e}")
            time.sleep(60)

    if PID_FILE.exists():
        PID_FILE.unlink()
    log("守护进程已退出")

if __name__ == "__main__":
    main()
