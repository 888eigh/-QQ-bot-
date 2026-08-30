"""
图形化管理界面 V2 - 设置页 + 功能页
- 功能页：模板自适应填空，快速生成常用指令和配置
- 设置页：高度自定义，所有参数可调
- 无显示环境自动降级为命令行
"""
import os
import sys
import threading
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings, BASE_DIR
from core import bot_logger, port_manager, ai_chat, doc_replier, napcat_config


class BotGUI:
    """QQ Bot 图形管理面板 V2"""

    def __init__(self):
        self.root = None
        self.running = False
        self.bot_thread = None

    def has_display(self) -> bool:
        if sys.platform in ("win32", "darwin"):
            return True
        return bool(os.environ.get("DISPLAY"))

    def launch(self):
        if not self.has_display():
            self._cli_mode()
            return
        try:
            import tkinter as tk
            from tkinter import ttk, scrolledtext, messagebox, simpledialog
        except ImportError:
            print("错误: tkinter 不可用，请安装 python3-tk")
            return
        self.tk = tk
        self.ttk = ttk
        self.scrolledtext = scrolledtext
        self.messagebox = messagebox
        self.simpledialog = simpledialog
        self._build_window()
        self.root.mainloop()

    def _cli_mode(self):
        print("=" * 55)
        print("  QQ Bot 管理面板（命令行模式）")
        print("=" * 55)
        print(f"  项目目录: {BASE_DIR}")
        print(f"  API 模型: {settings.get('api_model')}")
        print(f"  API 地址: {settings.get('api_base_url')}")
        print(f"  API Key:  {'已配置' if settings.get('api_key') else '未配置'}")
        print(f"  思考模式: {'关闭' if settings.get('api_thinking_disabled', True) else '开启'}")
        print(f"  监听端口: {port_manager.get_port()}")
        print(f"  文档指令: {len(doc_replier.list_commands())} 条")
        print("=" * 55)
        print("  启动 Bot: python3 main.py bot")
        print("  查看状态: python3 main.py status")
        print("  在有桌面环境运行可启动图形界面")
        print("=" * 55)

    # ========== 窗口构建 ==========

    def _build_window(self):
        self.root = self.tk.Tk()
        self.root.title("QQ Bot 管理面板")
        self.root.geometry("850x650")
        self.root.minsize(700, 500)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        style = self.ttk.Style()
        for theme in ["clam", "alt", "default"]:
            if theme in style.theme_names():
                style.theme_use(theme)
                break

        notebook = self.ttk.Notebook(self.root)
        notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        notebook.grid_rowconfigure(0, weight=1)
        notebook.grid_columnconfigure(0, weight=1)

        self._tab_features(notebook)
        self._tab_settings(notebook)

    # ========== 功能页（模板填空） ==========

    def _tab_features(self, notebook):
        frame = self.ttk.Frame(notebook, padding=15)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        notebook.add(frame, text="  功能模板  ")

        title = self.ttk.Label(
            frame, text="快速功能配置 — 填写模板内容，自动生成指令",
            font=("Arial", 12, "bold")
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 10))

        tmpl_frame = self.ttk.LabelFrame(frame, text="选择模板", padding=10)
        tmpl_frame.grid(row=1, column=0, sticky="nsew")
        tmpl_frame.grid_rowconfigure(4, weight=1)
        tmpl_frame.grid_columnconfigure(0, weight=1)

        self.templates = {
            "欢迎语": {
                "command": "welcome",
                "default": "欢迎来到本群！\n请先阅读群规，友好交流。\n输入 /help 查看可用指令。",
                "desc": "新成员入群时发送的欢迎消息",
            },
            "群规": {
                "command": "rules",
                "default": "【群规】\n1. 禁止违法违规内容\n2. 禁止刷屏和恶意@\n3. 保持友好交流\n4. 广告请联系管理员",
                "desc": "群规说明，用户输入 /rules 查看",
            },
            "关于机器人": {
                "command": "about",
                "default": "【关于本机器人】\n基于 NoneBot2 + NapCat 构建\nAI 模型: DeepSeek V4 Flash\n支持 AI 对话和文档指令回复",
                "desc": "机器人介绍，用户输入 /about 查看",
            },
            "帮助说明": {
                "command": "help",
                "default": "【可用指令】\n/hello - 打招呼\n/help - 显示帮助\n/chat <问题> - AI对话\n/docs - 查看所有指令\n/clear - 清除对话历史",
                "desc": "帮助信息，用户输入 /help 查看",
            },
            "AI 人设": {
                "command": "__system_prompt__",
                "default": "你是一个 friendly 的QQ机器人助手，用简洁幽默的中文回答问题。",
                "desc": "设置 AI 的性格和说话风格（影响所有 AI 对话）",
            },
            "自定义指令": {
                "command": "__custom__",
                "default": "在这里输入指令回复内容",
                "desc": "创建一个自定义的 /XXX 指令",
            },
            "自定义性格": {
                "command": "__custom_personality__",
                "default": "性格名称\n性格描述（一句话）\n\n你是一个...（这里写完整的性格设定 system prompt，描述AI的说话方式、口头禅、行为模式等）",
                "desc": "创建自定义性格，第一行写名称，第二行写描述，空行后写性格设定prompt",
            },
        }

        self.tmpl_var = self.tk.StringVar(value="欢迎语")
        tmpl_combo = self.ttk.Combobox(
            tmpl_frame, textvariable=self.tmpl_var,
            values=list(self.templates.keys()), state="readonly", font=("Arial", 10)
        )
        tmpl_combo.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        tmpl_combo.bind("<<ComboboxSelected>>", lambda e: self._on_template_change())

        self.tmpl_desc = self.ttk.Label(tmpl_frame, text="", foreground="gray", wraplength=600)
        self.tmpl_desc.grid(row=1, column=0, sticky="w", pady=(0, 5))

        self.custom_cmd_frame = self.ttk.Frame(tmpl_frame)
        self.custom_cmd_frame.grid(row=2, column=0, sticky="ew", pady=(0, 5))
        self.ttk.Label(self.custom_cmd_frame, text="指令名: /").pack(side="left")
        self.custom_cmd_entry = self.ttk.Entry(self.custom_cmd_frame, width=20)
        self.custom_cmd_entry.pack(side="left", padx=5)
        self.custom_cmd_frame.grid_remove()

        self.ttk.Label(tmpl_frame, text="内容:").grid(row=3, column=0, sticky="w", pady=(5, 2))
        self.tmpl_text = self.scrolledtext.ScrolledText(
            tmpl_frame, height=12, wrap="word", font=("Consolas", 10)
        )
        self.tmpl_text.grid(row=4, column=0, sticky="nsew", pady=(0, 10))

        btn_frame = self.ttk.Frame(tmpl_frame)
        btn_frame.grid(row=5, column=0, sticky="ew")
        self.ttk.Button(btn_frame, text="应用模板", command=self._apply_template).pack(side="left", padx=5)
        self.ttk.Button(btn_frame, text="重置为默认", command=self._reset_template).pack(side="left", padx=5)
        self.ttk.Button(btn_frame, text="预览效果", command=self._preview_template).pack(side="left", padx=5)

        self.tmpl_status = self.ttk.Label(frame, text="", foreground="green")
        self.tmpl_status.grid(row=2, column=0, sticky="w", pady=(5, 0))

        self._on_template_change()

    def _on_template_change(self):
        tmpl_name = self.tmpl_var.get()
        tmpl = self.templates.get(tmpl_name, {})
        self.tmpl_desc.config(text=tmpl.get("desc", ""))
        self.tmpl_text.delete("1.0", "end")
        self.tmpl_text.insert("1.0", tmpl.get("default", ""))
        if tmpl_name == "自定义指令":
            self.custom_cmd_frame.grid()
        else:
            self.custom_cmd_frame.grid_remove()

    def _apply_template(self):
        tmpl_name = self.tmpl_var.get()
        tmpl = self.templates[tmpl_name]
        content = self.tmpl_text.get("1.0", "end").strip()
        if not content:
            self.messagebox.showwarning("提示", "内容不能为空")
            return
        command = tmpl["command"]
        if command == "__custom__":
            command = self.custom_cmd_entry.get().strip().lower()
            if not command:
                self.messagebox.showwarning("提示", "请输入自定义指令名")
                return
        if command == "__system_prompt__":
            settings.set("chat_system_prompt", content)
            ai_chat.reload_config()
            ai_chat.clear_all_sessions()
            self.tmpl_status.config(text="✅ AI 人设已更新，所有对话历史已清除")
        elif command == "__custom_personality__":
            # 解析自定义性格：第一行名称，第二行描述，空行后为prompt
            lines = content.split("\n")
            if len(lines) < 3:
                self.messagebox.showwarning("提示", "格式错误：第一行名称，第二行描述，空行后写性格设定")
                return
            p_name = lines[0].strip()
            p_desc = lines[1].strip()
            p_prompt = "\n".join(lines[2:]).strip()
            if not p_name or not p_prompt:
                self.messagebox.showwarning("提示", "性格名称和设定不能为空")
                return
            from core.personality import personality
            if personality.add_custom_personality(p_name, p_desc, p_prompt):
                personality.set_global_personality(p_name)
                ai_chat.clear_all_sessions()
                self.tmpl_status.config(text=f"✅ 自定义性格「{p_name}」已创建并设为默认")
            else:
                self.messagebox.showerror("错误", "创建自定义性格失败")
        else:
            doc_replier.add_command(command, content)
            self.tmpl_status.config(text=f"✅ 已生成指令 /{command}")
        bot_logger.info(f"[功能模板] 应用模板: {tmpl_name}")

    def _reset_template(self):
        self._on_template_change()
        self.tmpl_status.config(text="已重置为默认内容")

    def _preview_template(self):
        content = self.tmpl_text.get("1.0", "end").strip()
        self.messagebox.showinfo("预览", f"用户将看到以下回复:\n\n{content}")

    # ========== 设置页（高度自定义） ==========

    def _tab_settings(self, notebook):
        frame = self.ttk.Frame(notebook, padding=15)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        notebook.add(frame, text="  高级设置  ")

        self.ttk.Label(
            frame, text="高级设置 — 所有参数可自定义",
            font=("Arial", 12, "bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        canvas = self.tk.Canvas(frame, highlightthickness=0)
        scrollbar = self.ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scroll_frame = self.ttk.Frame(canvas)
        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        scroll_frame.grid_columnconfigure(1, weight=1)
        self.settings_entries = {}

        row = 0
        row = self._section_header(scroll_frame, row, "API 配置（DeepSeek）")
        row = self._add_entry(scroll_frame, row, "API 地址", "api_base_url", "https://api.deepseek.com")
        row = self._add_entry(scroll_frame, row, "API Key", "api_key", "", show="*")
        row = self._add_entry(scroll_frame, row, "模型名称", "api_model", "deepseek-v4-flash")
        row = self._add_entry(scroll_frame, row, "超时时间(秒)", "api_timeout", "60")
        row = self._add_entry(scroll_frame, row, "最大Token", "api_max_tokens", "4096")
        row = self._add_entry(scroll_frame, row, "温度(0-2)", "api_temperature", "1.0")

        self.thinking_var = self.tk.BooleanVar(value=settings.get("api_thinking_disabled", True))
        self.ttk.Checkbutton(
            scroll_frame, text="关闭思考模式（推荐，响应更快）", variable=self.thinking_var
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=3, padx=5)
        row += 1

        row = self._section_header(scroll_frame, row, "Bot 配置")
        row = self._add_entry(scroll_frame, row, "监听主机", "bot_host", "0.0.0.0")
        row = self._add_entry(scroll_frame, row, "默认端口", "bot_port", "8080")
        self.auto_port_var = self.tk.BooleanVar(value=settings.get("auto_port", True))
        self.ttk.Checkbutton(
            scroll_frame, text="启用自适应端口（占用时自动切换）", variable=self.auto_port_var
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=3, padx=5)
        row += 1
        row = self._add_entry(scroll_frame, row, "命令前缀", "command_prefix", "/")
        row = self._add_entry(scroll_frame, row, "管理员QQ(逗号分隔)", "superusers", "")
        row = self._add_entry(scroll_frame, row, "机器人昵称(逗号分隔)", "nickname", "bot,机器人")

        row = self._section_header(scroll_frame, row, "NapCat 配置")
        row = self._add_entry(scroll_frame, row, "NapCat 路径", "napcat_path", "")
        row = self._add_entry(scroll_frame, row, "NapCat 配置文件", "napcat_config_path", "")
        self.napcat_autostart_var = self.tk.BooleanVar(value=settings.get("napcat_auto_start", False))
        self.ttk.Checkbutton(
            scroll_frame, text="启动 Bot 时自动启动 NapCat", variable=self.napcat_autostart_var
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=3, padx=5)
        row += 1

        row = self._section_header(scroll_frame, row, "日志配置")
        row = self._add_entry(scroll_frame, row, "日志级别", "log_level", "INFO")
        row = self._add_entry(scroll_frame, row, "日志保留天数", "log_keep_days", "30")

        row = self._section_header(scroll_frame, row, "聊天配置")
        self.chat_enabled_var = self.tk.BooleanVar(value=settings.get("chat_enabled", True))
        self.ttk.Checkbutton(scroll_frame, text="启用 AI 聊天", variable=self.chat_enabled_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=2, padx=5)
        row += 1
        self.chat_group_var = self.tk.BooleanVar(value=settings.get("chat_group_enabled", True))
        self.ttk.Checkbutton(scroll_frame, text="群聊中启用 AI 聊天", variable=self.chat_group_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=2, padx=5)
        row += 1
        self.chat_private_var = self.tk.BooleanVar(value=settings.get("chat_private_enabled", True))
        self.ttk.Checkbutton(scroll_frame, text="私聊中启用 AI 聊天", variable=self.chat_private_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=2, padx=5)
        row += 1
        row = self._add_entry(scroll_frame, row, "历史消息保留条数", "chat_history_limit", "20")

        row += 1
        # 初始性格选择
        self.ttk.Label(scroll_frame, text="初始性格:").grid(row=row, column=0, sticky="w", pady=3, padx=(5, 10))
        personality_names = ["默认", "傲娇", "温柔", "毒舌", "元气", "冷淡", "病娇"]
        self.personality_var = self.tk.StringVar(value=settings.get("default_personality", "默认"))
        personality_combo = self.ttk.Combobox(
            scroll_frame, textvariable=self.personality_var,
            values=personality_names, state="readonly"
        )
        personality_combo.grid(row=row, column=1, sticky="ew", pady=3, padx=(0, 5))
        row += 1
        btn_frame = self.ttk.Frame(scroll_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=15, sticky="ew")
        self.ttk.Button(btn_frame, text="保存所有设置", command=self._save_all_settings).pack(side="left", padx=5)
        self.ttk.Button(btn_frame, text="测试 API 连接", command=self._test_api).pack(side="left", padx=5)
        self.ttk.Button(btn_frame, text="重新配置 NapCat", command=self._reconfigure_napcat).pack(side="left", padx=5)

        self.settings_status = self.ttk.Label(scroll_frame, text="", foreground="green")
        self.settings_status.grid(row=row + 1, column=0, columnspan=2, sticky="w", pady=5)

    def _section_header(self, parent, row, text):
        lbl = self.ttk.Label(parent, text=text, font=("Arial", 10, "bold"), foreground="#2563eb")
        lbl.grid(row=row, column=0, columnspan=2, sticky="w", pady=(12, 3), padx=5)
        sep = self.ttk.Separator(parent, orient="horizontal")
        sep.grid(row=row + 1, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        return row + 2

    def _add_entry(self, parent, row, label, key, default, show=None):
        self.ttk.Label(parent, text=label + ":").grid(row=row, column=0, sticky="w", pady=3, padx=(5, 10))
        entry = self.ttk.Entry(parent, show=show)
        val = settings.get(key, default)
        if isinstance(val, list):
            val = ",".join(str(x) for x in val)
        entry.insert(0, str(val))
        entry.grid(row=row, column=1, sticky="ew", pady=3, padx=(0, 5))
        self.settings_entries[key] = entry
        return row + 1

    def _save_all_settings(self):
        try:
            for key, entry in self.settings_entries.items():
                value = entry.get()
                if key in ("api_timeout", "api_max_tokens", "bot_port", "log_keep_days", "chat_history_limit"):
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                elif key == "api_temperature":
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                elif key in ("superusers", "nickname"):
                    value = [s.strip() for s in value.split(",") if s.strip()]
                settings.set(key, value)
            settings.set("api_thinking_disabled", self.thinking_var.get())
            settings.set("auto_port", self.auto_port_var.get())
            settings.set("napcat_auto_start", self.napcat_autostart_var.get())
            settings.set("chat_enabled", self.chat_enabled_var.get())
            settings.set("chat_group_enabled", self.chat_group_var.get())
            settings.set("chat_private_enabled", self.chat_private_var.get())
            settings.set("default_personality", self.personality_var.get())
            # 应用全局性格
            try:
                from core.personality import personality
                personality.set_global_personality(self.personality_var.get())
                ai_chat.clear_all_sessions()
            except Exception:
                pass
            ai_chat.reload_config()
            self.settings_status.config(text="所有设置已保存并生效")
            bot_logger.info("设置已通过 GUI 保存")
        except Exception as e:
            self.settings_status.config(text=f"保存失败: {e}", foreground="red")
            bot_logger.error(f"保存设置失败: {e}")

    def _test_api(self):
        self._save_all_settings()
        def test():
            import asyncio
            result = asyncio.run(ai_chat.check_api_balance())
            msg_map = {
                "ok": ("API 连接正常", "green"),
                "warning": (f"警告: {result['message']}", "orange"),
                "error": (f"错误: {result['message']}", "red"),
            }
            msg, color = msg_map.get(result["status"], (str(result), "gray"))
            self.root.after(0, lambda: self.messagebox.showinfo("API 测试", msg))
        threading.Thread(target=test, daemon=True).start()

    def _reconfigure_napcat(self):
        port = port_manager.get_port()
        result = napcat_config.auto_configure(bot_port=port, force=True)
        if result["success"]:
            self.messagebox.showinfo("成功", result["message"])
        else:
            self.messagebox.showwarning("提示", result["message"])


def launch_gui():
    BotGUI().launch()


if __name__ == "__main__":
    launch_gui()
