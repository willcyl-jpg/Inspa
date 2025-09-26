"""UI Page for the Builder GUI."""
import customtkinter as ctk
from tkinter import messagebox

from .base_page import BasePage
from ..widgets import CollapsibleSection, FieldFrame
from ..theme import Style, Fonts, Colors

class UIPage(BasePage):
    def setup_ui(self):
        section = CollapsibleSection(self, "安装界面")
        section.pack(fill="x", pady=(0, 20))
        
        # 背景颜色
        bg_color_field = FieldFrame(section.content, "背景颜色", "选择安装界面的背景颜色")
        bg_color_field.pack(fill="x", padx=20, pady=(10, 0))
        self.bg_color = ctk.CTkEntry(bg_color_field, placeholder_text="例如：#FFFFFF", **Style.ENTRY)
        self.bg_color.pack(fill="x", pady=(5, 0))
        
        # 字体颜色
        font_color_field = FieldFrame(section.content, "字体颜色", "选择安装界面的字体颜色")
        font_color_field.pack(fill="x", padx=20, pady=(10, 0))
        self.font_color = ctk.CTkEntry(font_color_field, placeholder_text="例如：#000000", **Style.ENTRY)
        self.font_color.pack(fill="x", pady=(5, 0))
        
        # 按钮颜色
        btn_color_field = FieldFrame(section.content, "按钮颜色", "选择安装界面的按钮颜色")
        btn_color_field.pack(fill="x", padx=20, pady=(10, 0))
        self.btn_color = ctk.CTkEntry(btn_color_field, placeholder_text="例如：#0078D4", **Style.ENTRY)
        self.btn_color.pack(fill="x", pady=(5, 0))
        
        # 保存按钮
        save_button = ctk.CTkButton(section.content, text="保存界面设置", command=self.save_ui_settings, **Style.BUTTON_PRIMARY)
        save_button.pack(pady=10, padx=20)
        
        # 状态提示
        self.ui_status_var = ctk.StringVar(value="请填写界面设置")
        ui_status_label = ctk.CTkLabel(section.content, textvariable=self.ui_status_var, font=Fonts.BODY, text_color=Colors.TEXT_MUTED)
        ui_status_label.pack(pady=(8, 0))

    def save_ui_settings(self):
        """保存安装界面设置（演示不执行实际保存）"""
        bg_color = self.bg_color.get().strip()
        font_color = self.font_color.get().strip()
        btn_color = self.btn_color.get().strip()
        
        info = f"背景颜色: {bg_color}\n字体颜色: {font_color}\n按钮颜色: {btn_color}"
        messagebox.showinfo("界面设置", info)
        
        self.ui_status_var.set("界面设置已保存")

    def get_data(self) -> dict:
        return {
            "ui": {
                "bg_color": self.bg_color.get(),
                "font_color": self.font_color.get(),
                "btn_color": self.btn_color.get(),
            }
        }

    def load_data(self, data: dict):
        ui_data = data.get("ui", {})
        self.bg_color.delete(0, 'end'); self.bg_color.insert(0, ui_data.get("bg_color", ""))
        self.font_color.delete(0, 'end'); self.font_color.insert(0, ui_data.get("font_color", ""))
        self.btn_color.delete(0, 'end'); self.btn_color.insert(0, ui_data.get("btn_color", ""))
