"""Advanced Page for the Builder GUI."""
import customtkinter as ctk

from .base_page import BasePage
from ..widgets import CollapsibleSection, FieldFrame
from ..theme import Style, Fonts, Colors

class AdvancedPage(BasePage):
    def setup_ui(self):
        section = CollapsibleSection(self, "高级选项")
        section.pack(fill="x", pady=(0, 20))

        # 排除模式
        exclude_field = FieldFrame(section.content, "排除模式", "输入要排除的文件或目录模式 (glob格式)，每行一个")
        exclude_field.pack(fill="x", padx=20, pady=(10, 0))
        self.exclude_patterns = ctk.CTkTextbox(exclude_field, height=100, **Style.TEXTBOX)
        self.exclude_patterns.pack(fill="x", pady=(5, 0))

        # 环境变量
        env_field = FieldFrame(section.content, "环境变量", "设置安装后的环境变量")
        env_field.pack(fill="x", padx=20, pady=(10, 0))
        
        self.env_system_scope = ctk.CTkCheckBox(env_field, text="系统级环境变量 (需要管理员权限)")
        self.env_system_scope.pack(anchor="w", pady=(5, 5))

        path_label = ctk.CTkLabel(env_field, text="添加到 PATH (每行一个):")
        path_label.pack(anchor="w")
        self.env_path = ctk.CTkTextbox(env_field, height=80, **Style.TEXTBOX)
        self.env_path.pack(fill="x", pady=(0, 10))

        custom_label = ctk.CTkLabel(env_field, text="自定义变量 (格式: KEY=VALUE, 每行一个):")
        custom_label.pack(anchor="w")
        self.env_custom = ctk.CTkTextbox(env_field, height=80, **Style.TEXTBOX)
        self.env_custom.pack(fill="x")

        # 验证规则
        validation_section = CollapsibleSection(self, "验证规则")
        validation_section.pack(fill="x", pady=(20, 0))

        self.integrity_check = ctk.CTkCheckBox(validation_section.content, text="启用安装包完整性验证")
        self.integrity_check.pack(anchor="w", padx=20, pady=(10, 5))
        
        hash_field = FieldFrame(validation_section.content, "SHA256 哈希", "提供安装包的预期 SHA256 哈希值以供验证")
        hash_field.pack(fill="x", padx=20, pady=(0, 10))
        self.file_hash = ctk.CTkEntry(hash_field, placeholder_text="例如：e3b0c44298fc1c149afbf4c8...", **Style.ENTRY)
        self.file_hash.pack(fill="x", pady=(5, 0))

    def get_data(self) -> dict:
        custom_env = {}
        for line in self.env_custom.get("1.0", "end-1c").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                custom_env[key.strip()] = value.strip()

        return {
            "advanced": {
                "exclude": self.exclude_patterns.get("1.0", "end-1c").splitlines(),
                "env": {
                    "system_scope": self.env_system_scope.get(),
                    "add_path": self.env_path.get("1.0", "end-1c").splitlines(),
                    "set": custom_env
                },
                "validation": {
                    "integrity_check": self.integrity_check.get(),
                    "file_hash": self.file_hash.get()
                }
            }
        }

    def load_data(self, data: dict):
        advanced_data = data.get("advanced", {})

        self.exclude_patterns.delete("1.0", "end")
        self.exclude_patterns.insert("1.0", "\n".join(advanced_data.get("exclude", [])))

        env_data = advanced_data.get("env", {})
        if env_data.get("system_scope"):
            self.env_system_scope.select()
        else:
            self.env_system_scope.deselect()
        
        self.env_path.delete("1.0", "end")
        self.env_path.insert("1.0", "\n".join(env_data.get("add_path", [])))

        custom_env_str = "\n".join([f"{k}={v}" for k, v in env_data.get("set", {}).items()])
        self.env_custom.delete("1.0", "end")
        self.env_custom.insert("1.0", custom_env_str)

        validation_data = advanced_data.get("validation", {})
        if validation_data.get("integrity_check"):
            self.integrity_check.select()
        else:
            self.integrity_check.deselect()
        self.file_hash.delete(0, 'end'); self.file_hash.insert(0, validation_data.get("file_hash", ""))
