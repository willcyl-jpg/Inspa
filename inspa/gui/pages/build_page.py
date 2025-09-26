"""Build Page for the Builder GUI."""
import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path

from .base_page import BasePage
from ..widgets import CollapsibleSection, FieldFrame
from ..theme import Style, Colors
from ...config.schema import CompressionAlgorithm

class BuildPage(BasePage):
    def setup_ui(self):
        section = CollapsibleSection(self, "构建")
        section.pack(fill="x", pady=(0, 20))
        
        # 压缩算法
        algo_field = FieldFrame(section.content, "压缩算法", "选择压缩算法")
        algo_field.pack(fill="x", padx=20, pady=(10, 0))
        self.compression_algo = ctk.CTkOptionMenu(
            algo_field,
            values=[e.value for e in CompressionAlgorithm],
            fg_color=Colors.BACKGROUND,
            button_color=Colors.PRIMARY
        )
        self.compression_algo.pack(fill="x", pady=(5, 0))
        
        # 压缩级别
        level_field = FieldFrame(section.content, "压缩级别", "选择压缩级别")
        level_field.pack(fill="x", padx=20, pady=(10, 0))
        
        slider_frame = ctk.CTkFrame(level_field, fg_color="transparent")
        slider_frame.pack(fill="x", pady=(5,0))

        self.compression_level = ctk.CTkSlider(slider_frame, from_=1, to=9, number_of_steps=8, command=self.update_level_label, **Style.SLIDER)
        self.compression_level.pack(side="left", fill="x", expand=True, pady=(5, 0))
        self.level_label = ctk.CTkLabel(slider_frame, text="5", **Style.LABEL)
        self.level_label.pack(side="right", padx=(10,0), pady=(5, 0))
        self.compression_level.set(5)
        
        # 输出路径
        output_field = FieldFrame(section.content, "输出路径", "选择安装包输出路径")
        output_field.pack(fill="x", padx=20, pady=(10, 0))

        entry_frame = ctk.CTkFrame(output_field, fg_color="transparent")
        entry_frame.pack(fill="x", pady=(5, 0))

        self.output_path = ctk.CTkEntry(entry_frame, placeholder_text="选择输出路径", **Style.ENTRY)
        self.output_path.pack(side="left", fill="x", expand=True, pady=(5, 0))
        
        browse_button = ctk.CTkButton(entry_frame, text="浏览", command=self.browse_output_path, **Style.BUTTON_SECONDARY)
        browse_button.pack(side="right", padx=(8,0), pady=(5, 0))
        
        # 构建按钮
        build_button = ctk.CTkButton(section.content, text="构建安装器", command=self.build_installer, **Style.BUTTON_PRIMARY)
        build_button.pack(pady=20, padx=20)
        
        self.build_status_var = ctk.StringVar(value="请填写构建设置")
        build_status_label = ctk.CTkLabel(section.content, textvariable=self.build_status_var, font=("", 12), text_color=Colors.TEXT_MUTED)
        build_status_label.pack(pady=(8, 0))

    def update_level_label(self, value):
        self.level_label.configure(text=str(int(value)))

    def browse_output_path(self):
        path = filedialog.asksaveasfilename(
            title="选择输出文件路径",
            defaultextension=".exe",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if path:
            self.output_path.delete(0, 'end')
            self.output_path.insert(0, path)

    def build_installer(self):
        self.controller.build_installer()

    def get_data(self) -> dict:
        return {
            "compression": {
                "algorithm": self.compression_algo.get(),
                "level": int(self.compression_level.get())
            },
            "output_path": self.output_path.get()
        }

    def load_data(self, data: dict):
        comp_data = data.get("compression", {})
        self.compression_algo.set(comp_data.get("algorithm", "zstd"))
        self.compression_level.set(comp_data.get("level", 5))
        self.update_level_label(self.compression_level.get())
        self.output_path.delete(0, 'end')
        self.output_path.insert(0, data.get("output_path", ""))
