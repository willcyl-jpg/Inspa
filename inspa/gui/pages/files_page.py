"""Files and Directories Page for the Builder GUI."""
import customtkinter as ctk
from tkinter import filedialog
from typing import List

from .base_page import BasePage
from ..widgets import CollapsibleSection
from ..theme import Style, Fonts, Colors

class FilesPage(BasePage):
    def setup_ui(self):
        self.input_paths: List[str] = []

        section = CollapsibleSection(self, "文件与目录")
        section.pack(fill="x", expand=True, pady=(0, 20))
        
        button_frame = ctk.CTkFrame(section.content, fg_color="transparent")
        button_frame.pack(pady=10, padx=20, fill="x")

        add_files_button = ctk.CTkButton(button_frame, text="添加文件", command=self.add_files, **Style.BUTTON_ACCENT)
        add_files_button.pack(side="left", padx=(0, 10))
        
        add_folder_button = ctk.CTkButton(button_frame, text="添加文件夹", command=self.add_folder, **Style.BUTTON_ACCENT)
        add_folder_button.pack(side="left")
        
        self.file_list = ctk.CTkTextbox(section.content, height=200, fg_color=Colors.SURFACE_LIGHT, border_width=0, font=Fonts.MONO_SMALL)
        self.file_list.pack(fill="x", expand=True, padx=20, pady=(5, 0))
        
        clear_list_button = ctk.CTkButton(section.content, text="清空列表", command=self.clear_file_list, **Style.BUTTON_DANGER)
        clear_list_button.pack(pady=10, padx=20)
        
        self.files_status_var = ctk.StringVar(value="请添加文件或文件夹")
        files_status_label = ctk.CTkLabel(section.content, textvariable=self.files_status_var, font=Fonts.BODY, text_color=Colors.TEXT_MUTED)
        files_status_label.pack(pady=(8, 0))

    def add_files(self):
        files = filedialog.askopenfilenames(title="选择要打包的文件")
        if files:
            self.input_paths.extend(files)
            self.update_file_list()

    def add_folder(self):
        folder = filedialog.askdirectory(title="选择要打包的文件夹")
        if folder:
            self.input_paths.append(folder)
            self.update_file_list()

    def update_file_list(self):
        self.file_list.delete('1.0', 'end')
        for path in self.input_paths:
            self.file_list.insert('end', f"{path}\n")
        self.file_list.see('end')
        
        count = len(self.input_paths)
        self.files_status_var.set(f"已添加 {count} 个文件/文件夹")

    def clear_file_list(self):
        self.input_paths.clear()
        self.file_list.delete('1.0', 'end')
        self.files_status_var.set("请添加文件或文件夹")

    def get_data(self) -> dict:
        return {"inputs": self.input_paths}

    def load_data(self, data: dict):
        self.input_paths = data.get("inputs", [])
        self.update_file_list()
