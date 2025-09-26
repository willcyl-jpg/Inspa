"""License Page for the Builder GUI."""
import customtkinter as ctk
from tkinter import filedialog, messagebox

from .base_page import BasePage
from ..widgets import CollapsibleSection, FieldFrame
from ..theme import Style, Fonts, Colors

class LicensePage(BasePage):
    def setup_ui(self):
        section = CollapsibleSection(self, "许可协议")
        section.pack(fill="x", pady=(0, 20))
        
        # 许可协议标题
        title_field = FieldFrame(section.content, "许可协议标题", "在安装界面上显示的许可协议标题")
        title_field.pack(fill="x", padx=20, pady=(10, 0))
        self.license_title = ctk.CTkEntry(title_field, placeholder_text="最终用户许可协议 (EULA)", **Style.ENTRY)
        self.license_title.pack(fill="x", pady=(5, 0))

        # 许可协议文件
        file_field = FieldFrame(section.content, "许可协议文件", "选择包含协议内容的文本文件", required=True)
        file_field.pack(fill="x", padx=20, pady=(10, 0))
        
        entry_frame = ctk.CTkFrame(file_field, fg_color="transparent")
        entry_frame.pack(fill="x", pady=(5, 0))

        self.license_file_path = ctk.CTkEntry(entry_frame, placeholder_text="选择许可协议文件", **Style.ENTRY)
        self.license_file_path.pack(side="left", fill="x", expand=True, pady=(5, 0))
        
        # 浏览按钮
        browse_button = ctk.CTkButton(entry_frame, text="浏览", command=self.browse_license_file, **Style.BUTTON_SECONDARY)
        browse_button.pack(side="right", padx=(8,0), pady=(5,0))
        
        # 预览文本
        self.license_preview = ctk.CTkTextbox(section.content, height=200, fg_color=Colors.SURFACE_LIGHT, border_width=0, font=Fonts.MONO_SMALL)
        self.license_preview.pack(fill="x", expand=True, padx=20, pady=(5, 0))
        
        # 加载按钮
        load_button = ctk.CTkButton(section.content, text="加载协议", command=self.load_license_file, **Style.BUTTON_PRIMARY)
        load_button.pack(pady=10, padx=20)
        
        # 状态提示
        self.license_status_var = ctk.StringVar(value="请加载许可协议")
        license_status_label = ctk.CTkLabel(section.content, textvariable=self.license_status_var, font=Fonts.BODY, text_color=Colors.TEXT_MUTED)
        license_status_label.pack(pady=(8, 0))

    def browse_license_file(self):
        """浏览许可协议文件"""
        path = filedialog.askopenfilename(
            title="选择许可协议文件",
            filetypes=[
                ("文本文件", "*.txt"),
                ("Markdown", "*.md"),
                ("reStructuredText", "*.rst"),
                ("所有文件", "*.*")
            ]
        )
        if path:
            self.license_file_path.delete(0, 'end')
            self.license_file_path.insert(0, path)
            self.load_license_file()

    def load_license_file(self):
        """加载许可协议文件并显示预览"""
        file_path = self.license_file_path.get().strip()
        if not file_path:
            messagebox.showerror("错误", "请先选择许可协议文件")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.license_preview.delete('1.0', 'end')
                self.license_preview.insert('1.0', content)
            
            self.license_status_var.set("许可协议已加载")
        except Exception as e:
            messagebox.showerror("错误", f"加载许可协议文件失败：{e}")

    def get_data(self) -> dict:
        return {
            "license": {
                "title": self.license_title.get(),
                "file": self.license_file_path.get()
            }
        }

    def load_data(self, data: dict):
        license_data = data.get("license", {})
        self.license_title.delete(0, 'end')
        self.license_title.insert(0, license_data.get("title", "最终用户许可协议 (EULA)"))
        
        path = license_data.get("file", "")
        self.license_file_path.delete(0, 'end')
        self.license_file_path.insert(0, path)
        if path:
            self.load_license_file()
