"""General Information Page for the Builder GUI."""
import customtkinter as ctk
from tkinter import messagebox
import random
try:
    import faker
except ImportError:
    faker = None

from .base_page import BasePage
from ..widgets import CollapsibleSection, FieldFrame
from ..theme import Style, Fonts, Colors

class GeneralPage(BasePage):
    def setup_ui(self):
        # --- Product Information Section ---
        product_section = CollapsibleSection(self, "产品信息")
        product_section.pack(fill="x", pady=(0, 20))
        
        self.product_name = ctk.CTkEntry(product_section.content, placeholder_text="例如：我的应用程序", **Style.ENTRY)
        self.product_version = ctk.CTkEntry(product_section.content, placeholder_text="1.0.0", **Style.ENTRY)
        self.product_company = ctk.CTkEntry(product_section.content, placeholder_text="例如：我的公司", **Style.ENTRY)
        self.product_description = ctk.CTkEntry(product_section.content, placeholder_text="一句话简介", **Style.ENTRY)
        self.product_copyright = ctk.CTkEntry(product_section.content, placeholder_text="© 2024 我的公司. 保留所有权利.", **Style.ENTRY)
        self.product_website = ctk.CTkEntry(product_section.content, placeholder_text="https://example.com", **Style.ENTRY)

        product_fields = [
            ("产品名称", self.product_name, "最终用户看到的产品名称", True),
            ("产品版本", self.product_version, "产品的版本号，如 1.0.0", True),
            ("公司名称", self.product_company, "开发者的公司名称", False),
            ("产品描述", self.product_description, "产品的简短描述", False),
            ("版权信息", self.product_copyright, "法律版权信息", False),
            ("官网地址", self.product_website, "产品或公司的官方网站", False),
        ]

        for label, widget, help_text, required in product_fields:
            field_frame = FieldFrame(product_section.content, label, help_text, required)
            field_frame.pack(fill="x", padx=10, pady=(0, 10))
            widget.pack(in_=field_frame, fill="x", pady=(5, 0))

        # --- Metadata Section ---
        metadata_section = CollapsibleSection(self, "安装包元数据")
        metadata_section.pack(fill="x", pady=(0, 20))

        self.package_name = ctk.CTkEntry(metadata_section.content, placeholder_text="例如：我的应用程序 安装包", **Style.ENTRY)
        self.package_version = ctk.CTkEntry(metadata_section.content, placeholder_text="1.0.0", **Style.ENTRY)
        self.release_notes = ctk.CTkEntry(metadata_section.content, placeholder_text="本次更新的主要内容", **Style.ENTRY)
        self.compatibility = ctk.CTkEntry(metadata_section.content, placeholder_text="例如：Windows 10 / 11", **Style.ENTRY)

        metadata_fields = [
            ("安装包名称", self.package_name, "安装程序自身的名称", True),
            ("安装包版本", self.package_version, "安装程序的版本，可与产品版本不同", True),
            ("发布说明", self.release_notes, "更新日志或发布说明", False),
            ("兼容性", self.compatibility, "兼容的操作系统", False),
        ]

        for label, widget, help_text, required in metadata_fields:
            field_frame = FieldFrame(metadata_section.content, label, help_text, required)
            field_frame.pack(fill="x", padx=10, pady=(0, 10))
            widget.pack(in_=field_frame, fill="x", pady=(5, 0))

        # --- Actions and Status ---
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", pady=(10, 0))

        save_button = ctk.CTkButton(action_frame, text="保存信息", command=self.save_info, **Style.BUTTON_PRIMARY)
        save_button.pack(side="left", padx=(10, 10))
        
        self.status_msg_var = ctk.StringVar(value="请填写基本信息")
        status_label = ctk.CTkLabel(action_frame, textvariable=self.status_msg_var, font=Fonts.BODY, text_color=Colors.TEXT_MUTED)
        status_label.pack(side="left", padx=(20, 0))

        self.after(100, self.auto_fill_info)

    def auto_fill_info(self):
        """自动填充信息（仅用于演示）"""
        if not faker:
            self.status_msg_var.set("无法自动填充，缺少 'faker' 库。")
            return
        try:
            fake = faker.Faker()
            
            # Product Info
            product_name_str = f"应用程序 {random.randint(1, 100)}"
            product_version_str = f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
            company_name_str = fake.company()
            self.product_name.delete(0, 'end'); self.product_name.insert(0, product_name_str)
            self.product_version.delete(0, 'end'); self.product_version.insert(0, product_version_str)
            self.product_company.delete(0, 'end'); self.product_company.insert(0, company_name_str)
            self.product_description.delete(0, 'end'); self.product_description.insert(0, fake.catch_phrase())
            self.product_copyright.delete(0, 'end'); self.product_copyright.insert(0, f"© {random.randint(2000, 2024)} {company_name_str}. 保留所有权利.")
            self.product_website.delete(0, 'end'); self.product_website.insert(0, fake.url())
            
            # Metadata
            self.package_name.delete(0, 'end'); self.package_name.insert(0, f"{product_name_str} 安装包")
            self.package_version.delete(0, 'end'); self.package_version.insert(0, product_version_str)
            self.release_notes.delete(0, 'end'); self.release_notes.insert(0, "- 新增功能 A\n- 修复问题 B")
            self.compatibility.delete(0, 'end'); self.compatibility.insert(0, "Windows 10 (x64) 或更高版本")

            self.status_msg_var.set("已自动填充示例数据")
        except Exception as e:
            self.status_msg_var.set(f"自动填充失败: {e}")

    def save_info(self):
        """保存信息（演示不执行实际保存）"""
        name = self.product_name.get().strip()
        version = self.product_version.get().strip()
        if not name or not version:
            messagebox.showerror("错误", "产品名称和版本是必填项")
            return
        
        pkg_name = self.package_name.get().strip()
        pkg_version = self.package_version.get().strip()
        if not pkg_name or not pkg_version:
            messagebox.showerror("错误", "安装包名称和版本是必填项")
            return

        messagebox.showinfo("信息已保存", "基本信息和元数据已在内存中更新。")
        self.status_msg_var.set("信息已保存")

    def get_data(self) -> dict:
        return {
            "product": {
                "name": self.product_name.get(),
                "version": self.product_version.get(),
                "company": self.product_company.get(),
                "description": self.product_description.get(),
                "copyright": self.product_copyright.get(),
                "website": self.product_website.get(),
            },
            "metadata": {
                "package_name": self.package_name.get(),
                "package_version": self.package_version.get(),
                "release_notes": self.release_notes.get(),
                "compatibility": self.compatibility.get(),
            }
        }

    def load_data(self, data: dict):
        product_data = data.get("product", {})
        self.product_name.delete(0, 'end'); self.product_name.insert(0, product_data.get("name", ""))
        self.product_version.delete(0, 'end'); self.product_version.insert(0, product_data.get("version", ""))
        self.product_company.delete(0, 'end'); self.product_company.insert(0, product_data.get("company", ""))
        self.product_description.delete(0, 'end'); self.product_description.insert(0, product_data.get("description", ""))
        self.product_copyright.delete(0, 'end'); self.product_copyright.insert(0, product_data.get("copyright", ""))
        self.product_website.delete(0, 'end'); self.product_website.insert(0, product_data.get("website", ""))

        metadata_data = data.get("metadata", {})
        self.package_name.delete(0, 'end'); self.package_name.insert(0, metadata_data.get("package_name", ""))
        self.package_version.delete(0, 'end'); self.package_version.insert(0, metadata_data.get("package_version", ""))
        self.release_notes.delete(0, 'end'); self.release_notes.insert(0, metadata_data.get("release_notes", ""))
        self.compatibility.delete(0, 'end'); self.compatibility.insert(0, metadata_data.get("compatibility", ""))
