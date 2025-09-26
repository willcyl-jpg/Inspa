"""Post-Install Actions and Scripts Page for the Builder GUI."""
import customtkinter as ctk
from tkinter import filedialog, messagebox

from .base_page import BasePage
from ..widgets import CollapsibleSection, FieldFrame
from ..theme import Style, Fonts, Colors

class PostInstallPage(BasePage):
    def setup_ui(self):
        # --- Post-Install Actions Section ---
        actions_section = CollapsibleSection(self, "安装后操作")
        actions_section.pack(fill="x", pady=(0, 20))

        post_action_field = FieldFrame(actions_section.content, "启动应用程序", "安装后要启动的可执行文件路径 (相对于安装目录)")
        post_action_field.pack(fill="x", padx=20, pady=(10, 0))
        self.post_action_executable = ctk.CTkEntry(post_action_field, placeholder_text="例如: MyApp.exe", **Style.ENTRY)
        self.post_action_executable.pack(fill="x", pady=(5, 0))

        self.post_action_args = ctk.CTkEntry(actions_section.content, placeholder_text="启动参数 (可选)", **Style.ENTRY)
        self.post_action_args.pack(fill="x", padx=20, pady=(10, 0))

        self.create_desktop_shortcut = ctk.CTkCheckBox(actions_section.content, text="创建桌面快捷方式")
        self.create_desktop_shortcut.pack(anchor="w", padx=20, pady=(10, 0))

        self.create_start_menu_shortcut = ctk.CTkCheckBox(actions_section.content, text="创建开始菜单快捷方式")
        self.create_start_menu_shortcut.pack(anchor="w", padx=20, pady=(5, 0))


        # --- Scripts Section ---
        scripts_section = CollapsibleSection(self, "自定义脚本")
        scripts_section.pack(fill="x", pady=(0, 20))
        
        script_field = FieldFrame(scripts_section.content, "脚本文件", "选择安装后要执行的脚本文件 (例如 .bat, .ps1)")
        script_field.pack(fill="x", padx=20, pady=(10, 0))

        entry_frame = ctk.CTkFrame(script_field, fg_color="transparent")
        entry_frame.pack(fill="x", pady=(5, 0))

        self.script_file_path = ctk.CTkEntry(entry_frame, placeholder_text="选择脚本文件", **Style.ENTRY)
        self.script_file_path.pack(side="left", fill="x", expand=True, pady=(5, 0))
        
        browse_button = ctk.CTkButton(entry_frame, text="浏览", command=self.browse_script_file, **Style.BUTTON_SECONDARY)
        browse_button.pack(side="right", padx=(8,0), pady=(5, 0))
        
        args_field = FieldFrame(scripts_section.content, "脚本参数", "传递给脚本的参数")
        args_field.pack(fill="x", padx=20, pady=(10, 0))
        self.script_args = ctk.CTkEntry(args_field, placeholder_text="例如: --silent --no-restart", **Style.ENTRY)
        self.script_args.pack(fill="x", pady=(5, 0))
        
        self.hide_script_window = ctk.CTkCheckBox(scripts_section.content, text="隐藏脚本执行窗口")
        self.hide_script_window.pack(anchor="w", padx=20, pady=(10, 0))
        
        # --- Save Button and Status ---
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", pady=(10, 0))

        save_button = ctk.CTkButton(action_frame, text="保存设置", command=self.save_settings, **Style.BUTTON_PRIMARY)
        save_button.pack(side="left", padx=20)
        
        self.status_var = ctk.StringVar(value="请配置安装后操作")
        status_label = ctk.CTkLabel(action_frame, textvariable=self.status_var, font=Fonts.BODY, text_color=Colors.TEXT_MUTED)
        status_label.pack(side="left", padx=20)

    def browse_script_file(self):
        path = filedialog.askopenfilename(
            title="选择脚本文件",
            filetypes=[
                ("PowerShell 脚本", "*.ps1"),
                ("批处理文件", "*.bat;*.cmd"),
                ("所有文件", "*.*")
            ]
        )
        if path:
            self.script_file_path.delete(0, 'end')
            self.script_file_path.insert(0, path)

    def save_settings(self):
        messagebox.showinfo("设置已保存", "安装后操作和脚本设置已在内存中更新。")
        self.status_var.set("设置已保存")

    def get_data(self) -> dict:
        return {
            "post_install": [
                {
                    "type": "run_executable",
                    "path": self.post_action_executable.get(),
                    "arguments": self.post_action_args.get(),
                    "create_desktop_shortcut": self.create_desktop_shortcut.get(),
                    "create_start_menu_shortcut": self.create_start_menu_shortcut.get(),
                },
                {
                    "type": "run_script",
                    "path": self.script_file_path.get(),
                    "arguments": self.script_args.get(),
                    "hide_window": self.hide_script_window.get(),
                }
            ]
        }

    def load_data(self, data: dict):
        post_install_data = data.get("post_install", [])
        
        run_exe_data = next((item for item in post_install_data if item.get("type") == "run_executable"), {})
        self.post_action_executable.delete(0, 'end'); self.post_action_executable.insert(0, run_exe_data.get("path", ""))
        self.post_action_args.delete(0, 'end'); self.post_action_args.insert(0, run_exe_data.get("arguments", ""))
        if run_exe_data.get("create_desktop_shortcut"): self.create_desktop_shortcut.select()
        else: self.create_desktop_shortcut.deselect()
        if run_exe_data.get("create_start_menu_shortcut"): self.create_start_menu_shortcut.select()
        else: self.create_start_menu_shortcut.deselect()

        run_script_data = next((item for item in post_install_data if item.get("type") == "run_script"), {})
        self.script_file_path.delete(0, 'end'); self.script_file_path.insert(0, run_script_data.get("path", ""))
        self.script_args.delete(0, 'end'); self.script_args.insert(0, run_script_data.get("arguments", ""))
        if run_script_data.get("hide_window"): self.hide_script_window.select()
        else: self.hide_script_window.deselect()
