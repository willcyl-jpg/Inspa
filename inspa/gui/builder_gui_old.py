"""
现代化 Inspa 构建器 GUI

采用 Liquid Glass 设计语言的现代化构建器界面
设计理念：简洁、直观、功能性强
映射需求：NFR-UI-001, NFR-UI-002, NFR-UI-003, FR-GUI-001, FR-GUI-003
"""

import os
import sys
import threading
import json
import queue
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    ctk = None
    filedialog = None
    messagebox = None
    print("警告: GUI 依赖未安装，GUI 功能不可用")

# 导入配置和构建器
if GUI_AVAILABLE:
    try:
        from ..config.schema import InspaConfig, ProductModel, InstallModel, CompressionAlgorithm
        from ..config.loader import load_config
        from ..build.builder import InspaBuilder
    except ImportError:
        print("警告: 无法导入 Inspa 核心模块")


# 仅在GUI可用时定义GUI类
if GUI_AVAILABLE:
    
    # 设置 CustomTkinter 主题和外观
    ctk.set_appearance_mode("system")  # 跟随系统主题
    ctk.set_default_color_theme("blue")  # 使用蓝色主题
    
    # 颜色定义 - Liquid Glass 风格
    class Colors:
        # 主色调
        PRIMARY = "#007AFF"        # iOS 蓝色
        PRIMARY_DARK = "#0051D0"   # 深蓝色
        PRIMARY_LIGHT = "#4DA6FF"  # 浅蓝色
        
        # 中性色
        SURFACE = "#F2F2F7"        # 表面色
        SURFACE_DARK = "#1C1C1E"   # 深色表面
        BACKGROUND = "#FFFFFF"     # 背景色
        BACKGROUND_DARK = "#000000" # 深色背景
        
        # 语义色
        SUCCESS = "#34C759"        # 成功绿色
        ERROR = "#FF3B30"          # 错误红色
        WARNING = "#FF9500"        # 警告橙色
        
        # 文本色
        TEXT_PRIMARY = "#000000"
        TEXT_SECONDARY = "#6D6D70"
        TEXT_TERTIARY = "#C7C7CC"
    
    
    class HelpButton(ctk.CTkButton):
        """帮助按钮组件"""
        
        def __init__(self, parent, help_text: str, **kwargs):
            kwargs.update({
                'text': '?',
                'width': 24,
                'height': 24,
                'corner_radius': 12,
                'font': ('', 12, 'bold'),
                'fg_color': Colors.PRIMARY_LIGHT,
                'hover_color': Colors.PRIMARY,
                'command': lambda: self.show_help()
            })
            super().__init__(parent, **kwargs)
            self.help_text = help_text
        
        def show_help(self):
            """显示帮助信息"""
            messagebox.showinfo("帮助", self.help_text)
    
    
    class LiquidFrame(ctk.CTkFrame):
        """Liquid Glass 风格的框架组件"""
        
        def __init__(self, parent, **kwargs):
            kwargs.update({
                'corner_radius': 12,
                'border_width': 1,
                'border_color': ('gray80', 'gray25')
            })
            super().__init__(parent, **kwargs)
    
    
    class FieldFrame(ctk.CTkFrame):
        """字段框架 - 包含标签、输入控件和帮助按钮"""
        
        def __init__(self, parent, label: str, help_text: str = "", required: bool = False, **kwargs):
            kwargs.update({
                'corner_radius': 8,
                'fg_color': 'transparent'
            })
            super().__init__(parent, **kwargs)
            
            # 标签行
            label_frame = ctk.CTkFrame(self, fg_color='transparent')
            label_frame.pack(fill='x', pady=(0, 5))
            
            # 标签文本
            label_text = f"{'* ' if required else ''}{label}"
            self.label = ctk.CTkLabel(
                label_frame, 
                text=label_text,
                font=('', 13, 'bold' if required else 'normal'),
                text_color=Colors.ERROR if required else Colors.TEXT_PRIMARY
            )
            self.label.pack(side='left')
            
            # 帮助按钮
            if help_text:
                self.help_btn = HelpButton(label_frame, help_text)
                self.help_btn.pack(side='right')
    
    
    class BuildProgressDialog(ctk.CTkToplevel):
        """构建进度对话框"""
        
        def __init__(self, parent):
            super().__init__(parent)
            self.title("构建安装器")
            self.geometry("500x350")
            self.resizable(False, False)
            
            # 设置模态
            self.transient(parent)
            self.grab_set()
            
            # 居中显示
            self.center_window()
            
            # 进度信息
            self.cancelled = False
            self.setup_ui()
        
        def center_window(self):
            """窗口居中"""
            self.update_idletasks()
            x = (self.winfo_screenwidth() // 2) - (500 // 2)
            y = (self.winfo_screenheight() // 2) - (350 // 2)
            self.geometry(f"500x350+{x}+{y}")
        
        def setup_ui(self):
            """设置UI"""
            # 标题
            title_label = ctk.CTkLabel(
                self, 
                text="🏗️ 正在构建安装器",
                font=('', 18, 'bold')
            )
            title_label.pack(pady=(20, 10))
            
            # 当前状态
            self.status_var = ctk.StringVar(value="准备中...")
            self.status_label = ctk.CTkLabel(
                self, 
                textvariable=self.status_var,
                font=('', 12)
            )
            self.status_label.pack(pady=5)
            
            # 进度条
            self.progress_bar = ctk.CTkProgressBar(self, width=400)
            self.progress_bar.pack(pady=10)
            self.progress_bar.set(0)
            
            # 详细日志（折叠）
            self.log_frame = LiquidFrame(self, width=450, height=150)
            self.log_frame.pack(pady=10, padx=25, fill='both', expand=True)
            
            self.log_text = ctk.CTkTextbox(self.log_frame, width=420, height=120)
            self.log_text.pack(pady=10, padx=10, fill='both', expand=True)
            
            # 按钮框架
            btn_frame = ctk.CTkFrame(self, fg_color='transparent')
            btn_frame.pack(pady=10)
            
            # 取消按钮
            self.cancel_btn = ctk.CTkButton(
                btn_frame,
                text="取消",
                width=100,
                command=self.cancel_build,
                fg_color=Colors.ERROR,
                hover_color='#D70015'
            )
            self.cancel_btn.pack(side='left', padx=10)
            
            # 关闭按钮（初始隐藏）
            self.close_btn = ctk.CTkButton(
                btn_frame,
                text="关闭",
                width=100,
                command=self.destroy,
                fg_color=Colors.SUCCESS,
                hover_color='#28A745'
            )
        
        def update_progress(self, progress: float, status: str, log: str = ""):
            """更新进度"""
            self.progress_bar.set(progress)
            self.status_var.set(status)
            
            if log:
                self.log_text.insert('end', f"{log}\n")
                self.log_text.see('end')
            
            self.update()
        
        def show_error(self, error_msg: str):
            """显示错误"""
            self.status_var.set(f"❌ 构建失败")
            self.log_text.insert('end', f"\n❌ 错误: {error_msg}\n")
            self.log_text.see('end')
            
            # 切换按钮
            self.cancel_btn.pack_forget()
            self.close_btn.pack(side='left', padx=10)
        
        def show_success(self, output_path: str):
            """显示成功"""
            self.progress_bar.set(1.0)
            self.status_var.set(f"✅ 构建成功！")
            self.log_text.insert('end', f"\n✅ 安装器已生成: {output_path}\n")
            self.log_text.see('end')
            
            # 切换按钮
            self.cancel_btn.pack_forget()
            self.close_btn.pack(side='left', padx=10)
        
        def cancel_build(self):
            """取消构建"""
            self.cancelled = True
            self.destroy()
    

    class InspaBuilderGUI:
        """Inspa 构建器主界面"""
        
        def __init__(self):
            self.root = ctk.CTk()
            self.config_data = {}
            self.input_paths = []
            self.setup_window()
            self.setup_ui()
            self.load_default_config()
        
        def setup_window(self):
            """设置窗口"""
            self.root.title("Inspa - Windows 安装器构建工具")
            self.root.geometry("800x900")
            self.root.minsize(750, 800)
            
            # 设置应用图标（如果存在）
            # self.root.iconbitmap("assets/icon.ico")
            
            # 居中显示
            self.center_window()
        
        def center_window(self):
            """窗口居中"""
            self.root.update_idletasks()
            x = (self.root.winfo_screenwidth() // 2) - (800 // 2)
            y = (self.root.winfo_screenheight() // 2) - (900 // 2)
            self.root.geometry(f"800x900+{x}+{y}")
        
        def setup_ui(self):
            """设置用户界面"""
            # 创建滚动框架
            self.main_frame = ctk.CTkScrollableFrame(
                self.root,
                corner_radius=0,
                fg_color='transparent'
            )
            self.main_frame.pack(fill='both', expand=True, padx=20, pady=10)
            
            # 标题区域
            self.setup_header()
            
            # 产品信息区域（必填）
            self.setup_product_section()
            
            # 安装配置区域（必填）
            self.setup_install_section()
            
            # 输入文件区域（必填）
            self.setup_input_section()
            
            # 压缩设置区域（可选）
            self.setup_compression_section()
            
            # 高级设置区域（可选）
            self.setup_advanced_section()
            
            # 构建按钮区域
            self.setup_build_section()
        
        def setup_header(self):
            """设置标题区域"""
            header_frame = LiquidFrame(self.main_frame)
            header_frame.pack(fill='x', pady=(0, 20))
            
            # 应用标题
            title_label = ctk.CTkLabel(
                header_frame,
                text="🚀 Inspa",
                font=('', 32, 'bold'),
                text_color=Colors.PRIMARY
            )
            title_label.pack(pady=(20, 5))
            
            # 副标题描述
            subtitle_label = ctk.CTkLabel(
                header_frame,
                text="现代化的 Windows 单文件自解压安装器构建工具",
                font=('', 12),
                text_color=Colors.TEXT_SECONDARY
            )
            subtitle_label.pack(pady=(0, 20))
        
        def setup_product_section(self):
            """设置产品信息区域"""
            section_frame = LiquidFrame(self.main_frame)
            section_frame.pack(fill='x', pady=(0, 15))
            
            # 区域标题
            section_title = ctk.CTkLabel(
                section_frame,
                text="📦 产品信息",
                font=('', 16, 'bold'),
                anchor='w'
            )
            section_title.pack(fill='x', padx=20, pady=(15, 10))
            
            # 产品名称（必填）
            name_field = FieldFrame(
                section_frame,
                label="产品名称",
                help_text="安装器和程序的显示名称，将出现在标题栏、欢迎页面等位置",
                required=True
            )
            name_field.pack(fill='x', padx=20, pady=5)
            
            self.product_name = ctk.CTkEntry(
                name_field,
                placeholder_text="例如：我的应用程序"
            )
            self.product_name.pack(fill='x', pady=(5, 0))
            
            # 版本号（必填）
            version_field = FieldFrame(
                section_frame,
                label="版本号",
                help_text="产品版本号，建议使用语义化版本格式（如 1.0.0）",
                required=True
            )
            version_field.pack(fill='x', padx=20, pady=5)
            
            self.product_version = ctk.CTkEntry(
                version_field,
                placeholder_text="1.0.0"
            )
            self.product_version.pack(fill='x', pady=(5, 0))
            
            # 公司名称
            company_field = FieldFrame(
                section_frame,
                label="公司名称",
                help_text="开发公司或组织名称，将显示在安装器中"
            )
            company_field.pack(fill='x', padx=20, pady=5)
            
            self.product_company = ctk.CTkEntry(
                company_field,
                placeholder_text="例如：我的公司"
            )
            self.product_company.pack(fill='x', pady=(5, 0))
            
            # 产品描述
            desc_field = FieldFrame(
                section_frame,
                label="产品描述",
                help_text="产品的简要描述，将在安装器中显示"
            )
            desc_field.pack(fill='x', padx=20, pady=(5, 15))
            
            self.product_description = ctk.CTkEntry(
                desc_field,
                placeholder_text="例如：一个功能强大的应用程序"
            )
            self.product_description.pack(fill='x', pady=(5, 0))
        
        def setup_install_section(self):
            """设置安装配置区域"""
            section_frame = LiquidFrame(self.main_frame)
            section_frame.pack(fill='x', pady=(0, 15))
            
            # 区域标题
            section_title = ctk.CTkLabel(
                section_frame,
                text="⚙️ 安装设置",
                font=('', 16, 'bold'),
                anchor='w'
            )
            section_title.pack(fill='x', padx=20, pady=(15, 10))
            
            # 默认安装路径（必填）
            path_field = FieldFrame(
                section_frame,
                label="默认安装路径",
                help_text="软件的默认安装目录，支持环境变量（如 %ProgramFiles%）",
                required=True
            )
            path_field.pack(fill='x', padx=20, pady=5)
            
            path_frame = ctk.CTkFrame(path_field, fg_color='transparent')
            path_frame.pack(fill='x', pady=(5, 0))
            
            self.install_path = ctk.CTkEntry(
                path_frame,
                placeholder_text="C:\\Program Files\\我的应用"
            )
            self.install_path.pack(side='left', fill='x', expand=True, padx=(0, 10))
            
            browse_btn = ctk.CTkButton(
                path_frame,
                text="浏览",
                width=70,
                command=self.browse_install_path
            )
            browse_btn.pack(side='right')
            
            # 安装选项
            options_frame = ctk.CTkFrame(section_frame, fg_color='transparent')
            options_frame.pack(fill='x', padx=20, pady=(10, 15))
            
            self.allow_user_path = ctk.CTkCheckBox(
                options_frame,
                text="允许用户修改安装路径"
            )
            self.allow_user_path.pack(anchor='w', pady=2)
            
            self.show_ui = ctk.CTkCheckBox(
                options_frame,
                text="显示安装界面"
            )
            self.show_ui.pack(anchor='w', pady=2)
            
            self.require_admin = ctk.CTkCheckBox(
                options_frame,
                text="需要管理员权限"
            )
            self.require_admin.pack(anchor='w', pady=2)
        
        def setup_input_section(self):
            """设置输入文件区域"""
            section_frame = LiquidFrame(self.main_frame)
            section_frame.pack(fill='x', pady=(0, 15))
            
            # 区域标题
            section_title = ctk.CTkLabel(
                section_frame,
                text="📁 输入文件",
                font=('', 16, 'bold'),
                anchor='w'
            )
            section_title.pack(fill='x', padx=20, pady=(15, 10))
            
            # 输入路径列表
            input_field = FieldFrame(
                section_frame,
                label="要打包的文件或目录",
                help_text="选择需要打包到安装器中的文件和文件夹",
                required=True
            )
            input_field.pack(fill='x', padx=20, pady=5)
            
            # 输入列表框架
            list_frame = ctk.CTkFrame(input_field)
            list_frame.pack(fill='x', pady=(5, 0))
            
            # 列表显示
            self.input_listbox = ctk.CTkTextbox(
                list_frame,
                height=100,
                state='disabled'
            )
            self.input_listbox.pack(fill='x', padx=10, pady=(10, 0))
            
            # 按钮框架
            btn_frame = ctk.CTkFrame(list_frame, fg_color='transparent')
            btn_frame.pack(fill='x', padx=10, pady=10)
            
            add_file_btn = ctk.CTkButton(
                btn_frame,
                text="添加文件",
                width=100,
                command=self.add_files
            )
            add_file_btn.pack(side='left', padx=(0, 5))
            
            add_folder_btn = ctk.CTkButton(
                btn_frame,
                text="添加文件夹",
                width=100,
                command=self.add_folder
            )
            add_folder_btn.pack(side='left', padx=5)
            
            clear_btn = ctk.CTkButton(
                btn_frame,
                text="清空",
                width=70,
                fg_color=Colors.ERROR,
                hover_color='#D70015',
                command=self.clear_inputs
            )
            clear_btn.pack(side='right')
        
        def setup_compression_section(self):
            """设置压缩区域"""
            section_frame = LiquidFrame(self.main_frame)
            section_frame.pack(fill='x', pady=(0, 15))
            
            # 区域标题
            section_title = ctk.CTkLabel(
                section_frame,
                text="🗜️ 压缩设置",
                font=('', 16, 'bold'),
                anchor='w'
            )
            section_title.pack(fill='x', padx=20, pady=(15, 10))
            
            # 压缩算法
            algo_field = FieldFrame(
                section_frame,
                label="压缩算法",
                help_text="ZSTD 提供更好的压缩比，ZIP 兼容性更好"
            )
            algo_field.pack(fill='x', padx=20, pady=5)
            
            self.compression_algo = ctk.CTkOptionMenu(
                algo_field,
                values=["zstd", "zip"],
                command=self.on_compression_change
            )
            self.compression_algo.pack(anchor='w', pady=(5, 0))
            
            # 压缩级别
            level_field = FieldFrame(
                section_frame,
                label="压缩级别",
                help_text="更高的级别提供更好的压缩比，但需要更多时间"
            )
            level_field.pack(fill='x', padx=20, pady=(5, 15))
            
            level_frame = ctk.CTkFrame(level_field, fg_color='transparent')
            level_frame.pack(fill='x', pady=(5, 0))
            
            self.compression_level = ctk.CTkSlider(
                level_frame,
                from_=1,
                to=22,
                number_of_steps=21
            )
            self.compression_level.pack(side='left', fill='x', expand=True, padx=(0, 10))
            
            self.level_label = ctk.CTkLabel(level_frame, text="3")
            self.level_label.pack(side='right')
            
            self.compression_level.configure(command=self.update_level_label)
            self.compression_level.set(3)
        
        def setup_advanced_section(self):
            """设置高级选项区域"""
            section_frame = LiquidFrame(self.main_frame)
            section_frame.pack(fill='x', pady=(0, 15))
            
            # 区域标题
            section_title = ctk.CTkLabel(
                section_frame,
                text="🔧 高级选项",
                font=('', 16, 'bold'),
                anchor='w'
            )
            section_title.pack(fill='x', padx=20, pady=(15, 10))
            
            # 排除模式
            exclude_field = FieldFrame(
                section_frame,
                label="排除模式",
                help_text="使用 glob 模式排除不需要的文件，一行一个模式"
            )
            exclude_field.pack(fill='x', padx=20, pady=5)
            
            self.exclude_patterns = ctk.CTkTextbox(
                exclude_field,
                height=80,
                placeholder_text="*.pyc\n__pycache__/\n*.log"
            )
            self.exclude_patterns.pack(fill='x', pady=(5, 0))
            
            # 配置文件操作
            config_field = FieldFrame(
                section_frame,
                label="配置文件",
                help_text="可以导入现有配置文件或导出当前设置"
            )
            config_field.pack(fill='x', padx=20, pady=(10, 15))
            
            config_frame = ctk.CTkFrame(config_field, fg_color='transparent')
            config_frame.pack(fill='x', pady=(5, 0))
            
            import_btn = ctk.CTkButton(
                config_frame,
                text="导入配置",
                width=100,
                command=self.import_config
            )
            import_btn.pack(side='left', padx=(0, 10))
            
            export_btn = ctk.CTkButton(
                config_frame,
                text="导出配置",
                width=100,
                command=self.export_config
            )
            export_btn.pack(side='left')
        
        def setup_build_section(self):
            """设置构建区域"""
            build_frame = LiquidFrame(self.main_frame)
            build_frame.pack(fill='x', pady=(0, 20))
            
            # 输出路径
            output_field = FieldFrame(
                build_frame,
                label="输出路径",
                help_text="生成的安装器 EXE 文件保存位置"
            )
            output_field.pack(fill='x', padx=20, pady=(15, 10))
            
            output_frame = ctk.CTkFrame(output_field, fg_color='transparent')
            output_frame.pack(fill='x', pady=(5, 0))
            
            self.output_path = ctk.CTkEntry(
                output_frame,
                placeholder_text="installer.exe"
            )
            self.output_path.pack(side='left', fill='x', expand=True, padx=(0, 10))
            
            browse_output_btn = ctk.CTkButton(
                output_frame,
                text="浏览",
                width=70,
                command=self.browse_output_path
            )
            browse_output_btn.pack(side='right')
            
            # 构建按钮
            self.build_btn = ctk.CTkButton(
                build_frame,
                text="🚀 构建安装器",
                height=50,
                font=('', 16, 'bold'),
                fg_color=Colors.SUCCESS,
                hover_color='#28A745',
                command=self.start_build
            )
            self.build_btn.pack(fill='x', padx=20, pady=(10, 20))
        
        def load_default_config(self):
            """加载默认配置"""
            # 设置默认值
            self.product_name.insert(0, "我的应用程序")
            self.product_version.insert(0, "1.0.0")
            self.install_path.insert(0, "C:\\Program Files\\我的应用程序")
            self.output_path.insert(0, "installer.exe")
            
            # 设置默认选项
            self.allow_user_path.select()
            self.show_ui.select()
            
            # 设置默认排除模式
            self.exclude_patterns.insert('end', "*.pyc\n__pycache__/\n*.log\n*.tmp\n.git/")
        
        # 事件处理方法
        def browse_install_path(self):
            """浏览安装路径"""
            path = filedialog.askdirectory(title="选择默认安装目录")
            if path:
                self.install_path.delete(0, 'end')
                self.install_path.insert(0, path)
        
        def browse_output_path(self):
            """浏览输出路径"""
            path = filedialog.asksaveasfilename(
                title="保存安装器",
                defaultextension=".exe",
                filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
            )
            if path:
                self.output_path.delete(0, 'end')
                self.output_path.insert(0, path)
        
        def add_files(self):
            """添加文件"""
            files = filedialog.askopenfilenames(title="选择要打包的文件")
            for file in files:
                if file not in self.input_paths:
                    self.input_paths.append(file)
            self.update_input_list()
        
        def add_folder(self):
            """添加文件夹"""
            folder = filedialog.askdirectory(title="选择要打包的文件夹")
            if folder and folder not in self.input_paths:
                self.input_paths.append(folder)
                self.update_input_list()
        
        def clear_inputs(self):
            """清空输入列表"""
            self.input_paths.clear()
            self.update_input_list()
        
        def update_input_list(self):
            """更新输入列表显示"""
            self.input_listbox.configure(state='normal')
            self.input_listbox.delete('1.0', 'end')
            
            for i, path in enumerate(self.input_paths, 1):
                self.input_listbox.insert('end', f"{i}. {path}\n")
            
            self.input_listbox.configure(state='disabled')
        
        def on_compression_change(self, value):
            """压缩算法改变时调整级别范围"""
            if value == "zstd":
                self.compression_level.configure(to=22)
            else:  # zip
                self.compression_level.configure(to=9)
                if self.compression_level.get() > 9:
                    self.compression_level.set(9)
        
        def update_level_label(self, value):
            """更新压缩级别标签"""
            self.level_label.configure(text=str(int(value)))
        
        def import_config(self):
            """导入配置文件"""
            file_path = filedialog.askopenfilename(
                title="选择配置文件",
                filetypes=[("YAML文件", "*.yaml"), ("YAML文件", "*.yml"), ("所有文件", "*.*")]
            )
            if file_path:
                try:
                    config = load_config(Path(file_path))
                    self.load_config_to_ui(config)
                    messagebox.showinfo("成功", "配置文件导入成功！")
                except Exception as e:
                    messagebox.showerror("错误", f"导入配置文件失败：{e}")
        
        def export_config(self):
            """导出配置文件"""
            file_path = filedialog.asksaveasfilename(
                title="保存配置文件",
                defaultextension=".yaml",
                filetypes=[("YAML文件", "*.yaml"), ("所有文件", "*.*")]
            )
            if file_path:
                try:
                    config = self.build_config()
                    self.save_config_to_file(config, Path(file_path))
                    messagebox.showinfo("成功", "配置文件导出成功！")
                except Exception as e:
                    messagebox.showerror("错误", f"导出配置文件失败：{e}")
        
        def load_config_to_ui(self, config: InspaConfig):
            """将配置加载到UI"""
            # 清空现有内容
            self.clear_ui_fields()
            
            # 产品信息
            if config.product.name:
                self.product_name.insert(0, config.product.name)
            if config.product.version:
                self.product_version.insert(0, config.product.version)
            if config.product.company:
                self.product_company.insert(0, config.product.company)
            if config.product.description:
                self.product_description.insert(0, config.product.description)
            
            # 安装设置
            if config.install.default_path:
                self.install_path.insert(0, config.install.default_path)
            
            # 设置复选框
            if config.install.allow_user_path:
                self.allow_user_path.select()
            else:
                self.allow_user_path.deselect()
            
            if config.install.show_ui:
                self.show_ui.select()
            else:
                self.show_ui.deselect()
            
            if config.install.require_admin:
                self.require_admin.select()
            else:
                self.require_admin.deselect()
            
            # 压缩设置
            self.compression_algo.set(config.compression.algo.value)
            self.compression_level.set(config.compression.level)
            
            # 输入路径
            self.input_paths.clear()
            for input_path in config.inputs:
                self.input_paths.append(str(input_path.path))
            self.update_input_list()
            
            # 排除模式
            if config.exclude:
                self.exclude_patterns.delete('1.0', 'end')
                self.exclude_patterns.insert('end', '\n'.join(config.exclude))
        
        def clear_ui_fields(self):
            """清空UI字段"""
            self.product_name.delete(0, 'end')
            self.product_version.delete(0, 'end')
            self.product_company.delete(0, 'end')
            self.product_description.delete(0, 'end')
            self.install_path.delete(0, 'end')
            self.exclude_patterns.delete('1.0', 'end')
            self.input_paths.clear()
            self.update_input_list()
        
        def build_config(self) -> InspaConfig:
            """从UI构建配置对象"""
            # TODO: 实现配置构建逻辑
            pass
        
        def save_config_to_file(self, config: InspaConfig, file_path: Path):
            """保存配置到文件"""
            # TODO: 实现配置保存逻辑
            pass
        
        def start_build(self):
            """开始构建"""
            # 验证输入
            if not self.validate_inputs():
                return
            
            # 创建进度对话框
            progress_dialog = BuildProgressDialog(self.root)
            
            # 在后台线程中执行构建
            def build_thread():
                try:
                    # TODO: 实现实际的构建逻辑
                    import time
                    for i in range(101):
                        if progress_dialog.cancelled:
                            break
                        progress_dialog.update_progress(
                            i / 100.0,
                            f"构建进度 {i}%",
                            f"处理步骤 {i}"
                        )
                        time.sleep(0.05)
                    
                    if not progress_dialog.cancelled:
                        output_path = self.output_path.get() or "installer.exe"
                        progress_dialog.show_success(output_path)
                        
                except Exception as e:
                    progress_dialog.show_error(str(e))
            
            # 启动构建线程
            build_thread_obj = threading.Thread(target=build_thread, daemon=True)
            build_thread_obj.start()
        
        def validate_inputs(self) -> bool:
            """验证输入"""
            errors = []
            
            if not self.product_name.get().strip():
                errors.append("请输入产品名称")
            
            if not self.product_version.get().strip():
                errors.append("请输入产品版本")
            
            if not self.install_path.get().strip():
                errors.append("请输入默认安装路径")
            
            if not self.input_paths:
                errors.append("请添加要打包的文件或文件夹")
            
            if errors:
                messagebox.showerror("输入错误", "\n".join(errors))
                return False
            
            return True
        
        def run(self):
            """运行GUI"""
            self.root.mainloop()
    
    # 兼容性别名
    BuilderGUI = InspaBuilderGUI


    class BuilderGUI:
        """Inspa 构建器主界面"""
        
        def __init__(self):
            if not GUI_AVAILABLE:
                raise ImportError("GUI 依赖未安装，无法启动图形界面")
            
            # 设置外观模式和颜色主题
            ctk.set_appearance_mode("light")  # GitHub Light 主题
            ctk.set_default_color_theme("blue")
            
            # 创建主窗口
            self.root = ctk.CTk()
            self.root.title("Inspa - Windows 安装器构建工具")
            self.root.geometry("900x700")
            self.root.minsize(800, 600)
            
            # 配置 DPI 缩放
            self._configure_dpi()
            
            # 初始化变量
            self.config_path = ctk.StringVar()
            self.output_path = ctk.StringVar()
            self.current_config = None
            
            # 构建界面
            self._build_ui()
            
            # 绑定事件
            self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        def _configure_dpi(self):
            """配置 DPI 缩放"""
            try:
                # Windows DPI 感知设置
                if sys.platform == "win32":
                    import ctypes
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass  # 忽略 DPI 设置错误
        
        def _build_ui(self):
            """构建用户界面"""
            # 主容器
            main_container = ctk.CTkScrollableFrame(self.root)
            main_container.pack(fill="both", expand=True, padx=20, pady=20)
            
            # 标题
            title_label = ctk.CTkLabel(
                main_container, 
                text="Inspa - Windows 安装器构建工具",
                font=("Segoe UI", 24, "bold")
            )
            title_label.pack(pady=(0, 20))
            
            # 配置文件区域
            self._build_config_section(main_container)
            
            # 输出设置区域
            self._build_output_section(main_container)
            
            # 构建选项区域
            self._build_options_section(main_container)
            
            # 操作按钮区域
            self._build_action_section(main_container)
            
            # 日志显示区域
            self._build_log_section(main_container)
        
        def _build_config_section(self, parent):
            """构建配置文件区域"""
            config_frame = ModernFrame(parent)
            config_frame.pack(fill="x", pady=(0, 15))
            
            # 标题
            ctk.CTkLabel(config_frame, text="配置文件", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=15, pady=(15, 5))
            
            # 文件选择行
            file_row = ctk.CTkFrame(config_frame, fg_color="transparent")
            file_row.pack(fill="x", padx=15, pady=(0, 15))
            
            # 路径输入框
            self.config_entry = ctk.CTkEntry(
                file_row, 
                textvariable=self.config_path,
                placeholder_text="选择配置文件 (inspa.yaml)",
                height=36,
                font=('Segoe UI', 11)
            )
            self.config_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
            
            # 浏览按钮
            browse_btn = ModernButton(file_row, text="浏览", width=80, command=self._browse_config)
            browse_btn.pack(side="right")
            
            # 验证按钮
            validate_btn = ModernButton(file_row, text="验证", width=80, command=self._validate_config)
            validate_btn.pack(side="right", padx=(0, 10))
        
        def _build_output_section(self, parent):
            """构建输出设置区域"""
            output_frame = ModernFrame(parent)
            output_frame.pack(fill="x", pady=(0, 15))
            
            # 标题
            ctk.CTkLabel(output_frame, text="输出设置", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=15, pady=(15, 5))
            
            # 输出路径行
            output_row = ctk.CTkFrame(output_frame, fg_color="transparent")
            output_row.pack(fill="x", padx=15, pady=(0, 15))
            
            # 路径输入框
            self.output_entry = ctk.CTkEntry(
                output_row,
                textvariable=self.output_path,
                placeholder_text="输出文件路径 (可选，默认自动生成)",
                height=36,
                font=('Segoe UI', 11)
            )
            self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
            
            # 保存对话框按钮
            save_btn = ModernButton(output_row, text="另存为", width=80, command=self._browse_output)
            save_btn.pack(side="right")
        
        def _build_options_section(self, parent):
            """构建构建选项区域"""
            options_frame = ModernFrame(parent)
            options_frame.pack(fill="x", pady=(0, 15))
            
            # 标题
            ctk.CTkLabel(options_frame, text="构建选项", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=15, pady=(15, 5))
            
            # 选项容器
            options_container = ctk.CTkFrame(options_frame, fg_color="transparent")
            options_container.pack(fill="x", padx=15, pady=(0, 15))
            
            # 压缩选项
            compression_row = ctk.CTkFrame(options_container, fg_color="transparent")
            compression_row.pack(fill="x", pady=(0, 10))
            
            ctk.CTkLabel(compression_row, text="压缩算法:", width=100, font=('Segoe UI', 11)).pack(side="left")
            
            self.compression_var = ctk.StringVar(value="zstd")
            compression_menu = ctk.CTkOptionMenu(
                compression_row,
                values=["zstd", "zip"],
                variable=self.compression_var,
                font=('Segoe UI', 11)
            )
            compression_menu.pack(side="left", padx=(10, 0))
            
            # 验证选项
            validation_row = ctk.CTkFrame(options_container, fg_color="transparent")
            validation_row.pack(fill="x", pady=(0, 10))
            
            self.verify_hash = ctk.BooleanVar(value=True)
            hash_check = ctk.CTkCheckBox(
                validation_row, 
                text="验证文件哈希",
                variable=self.verify_hash,
                font=('Segoe UI', 11)
            )
            hash_check.pack(side="left")
            
            # 详细日志选项
            verbose_row = ctk.CTkFrame(options_container, fg_color="transparent")
            verbose_row.pack(fill="x")
            
            self.verbose_logging = ctk.BooleanVar(value=False)
            verbose_check = ctk.CTkCheckBox(
                verbose_row,
                text="详细日志",
                variable=self.verbose_logging,
                font=('Segoe UI', 11)
            )
            verbose_check.pack(side="left")
        
        def _build_action_section(self, parent):
            """构建操作按钮区域"""
            action_frame = ModernFrame(parent)
            action_frame.pack(fill="x", pady=(0, 15))
            
            # 按钮容器
            button_container = ctk.CTkFrame(action_frame, fg_color="transparent")
            button_container.pack(fill="x", padx=15, pady=15)
            
            # 构建按钮
            build_btn = ModernButton(
                button_container,
                text="🔨 开始构建",
                width=120,
                height=40,
                font=("Segoe UI", 12, "bold"),
                command=self._start_build
            )
            build_btn.pack(side="left", padx=(0, 10))
            
            # 检查按钮
            inspect_btn = ModernButton(
                button_container,
                text="🔍 检查安装器",
                width=120,
                command=self._inspect_installer
            )
            inspect_btn.pack(side="left", padx=(0, 10))
            
            # 清空日志按钮
            clear_btn = ModernButton(
                button_container,
                text="🗑️ 清空日志",
                width=100,
                command=self._clear_log
            )
            clear_btn.pack(side="right")
            
            # 帮助按钮
            help_btn = ModernButton(
                button_container,
                text="❓ 帮助",
                width=80,
                command=self._show_help
            )
            help_btn.pack(side="right", padx=(0, 10))
        
        def _build_log_section(self, parent):
            """构建日志显示区域"""
            log_frame = ModernFrame(parent)
            log_frame.pack(fill="both", expand=True)
            
            # 标题
            ctk.CTkLabel(log_frame, text="构建日志", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=15, pady=(15, 5))
            
            # 日志文本框
            self.log_text = ctk.CTkTextbox(
                log_frame,
                height=200,
                font=("Consolas", 10),
                wrap="word"
            )
            self.log_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        def _browse_config(self):
            """浏览配置文件"""
            filename = filedialog.askopenfilename(
                title="选择配置文件",
                filetypes=[("YAML 文件", "*.yaml *.yml"), ("所有文件", "*.*")]
            )
            if filename:
                self.config_path.set(filename)
                self._log(f"已选择配置文件: {filename}")
                # 自动加载并预览配置
                self._load_config_preview()
        
        def _browse_output(self):
            """浏览输出文件"""
            filename = filedialog.asksaveasfilename(
                title="保存安装器",
                defaultextension=".exe",
                filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
            )
            if filename:
                self.output_path.set(filename)
                self._log(f"已选择输出文件: {filename}")
        
        def _load_config_preview(self):
            """加载配置文件并显示预览"""
            config_file = self.config_path.get().strip()
            if not config_file or not Path(config_file).exists():
                return
            
            try:
                from ..config import load_config
                self.current_config = load_config(Path(config_file))
                
                # 在日志中显示配置概要
                product = self.current_config.product
                self._log(f"📋 配置预览:")
                self._log(f"   产品: {product.name} v{product.version}")
                self._log(f"   输入: {len(self.current_config.inputs)} 个路径")
                if self.current_config.post_actions:
                    self._log(f"   脚本: {len(self.current_config.post_actions)} 个操作")
                
                # 如果输出路径为空，自动生成默认路径
                if not self.output_path.get().strip():
                    output_name = f"{product.name}_v{product.version}_installer.exe"
                    output_name = "".join(c for c in output_name if c.isalnum() or c in '_-.')
                    default_output = Path.cwd() / "output" / output_name
                    self.output_path.set(str(default_output))
                    
            except Exception as e:
                self._log(f"❌ 配置加载失败: {e}")
                self.current_config = None
        
        def _validate_config(self):
            """验证配置文件"""
            config_file = self.config_path.get().strip()
            if not config_file:
                messagebox.showerror("错误", "请先选择配置文件")
                return
            
            if not Path(config_file).exists():
                messagebox.showerror("错误", f"配置文件不存在: {config_file}")
                return
            
            self._log("开始验证配置文件...")
            
            try:
                from ..config import validate_config_with_result
                
                # 验证配置文件
                validation_result = validate_config_with_result(Path(config_file))
                
                if validation_result.is_valid:
                    self._log(f"✅ 配置文件验证成功: {Path(config_file).name}")
                    messagebox.showinfo("成功", "配置文件验证成功！")
                    self.current_config = validation_result.config
                else:
                    error_msg = "\\n".join([f"• {error}" for error in validation_result.errors])
                    self._log(f"❌ 配置文件验证失败:")
                    for error in validation_result.errors:
                        self._log(f"   • {error}")
                    messagebox.showerror("验证失败", f"配置文件存在问题:\\n\\n{error_msg}")
                    
            except Exception as e:
                error_msg = str(e)
                self._log(f"❌ 配置文件验证失败: {error_msg}")
                messagebox.showerror("错误", f"配置文件验证失败:\\n{error_msg}")
        
        def _start_build(self):
            """开始构建"""
            config_file = self.config_path.get().strip()
            if not config_file:
                messagebox.showerror("错误", "请先选择配置文件")
                return
            
            output_file = self.output_path.get().strip()
            if not output_file:
                messagebox.showerror("错误", "请先选择输出文件路径")
                return
            
            # 确保有加载的配置
            if not self.current_config:
                self._log("配置未加载，先验证配置文件...")
                self._validate_config()
                if not self.current_config:
                    return
            
            self._log("🔨 开始构建安装器...")
            
            # 创建进度对话框
            progress = ProgressDialog(self.root, "构建安装器")
            
            def build_thread():
                try:
                    from ..build.builder import Builder
                    from ..utils import ensure_directory
                    
                    # 确保输出目录存在
                    ensure_directory(Path(output_file).parent)
                    
                    # 创建构建器
                    builder = Builder()
                    
                    # 构建进度回调
                    def progress_callback(stage: str, current: int, total: int, current_item: str):
                        if progress.cancelled:
                            return
                        
                        progress_value = current / total if total > 0 else 0
                        status_msg = f"{stage}: {current_item}" if current_item else stage
                        
                        # 在主线程更新 GUI
                        progress.root.after(0, lambda: progress.update_progress(progress_value, status_msg))
                        
                        # 同时更新日志
                        self.root.after(0, lambda: self._log(f"   {status_msg} ({current}/{total})"))
                    
                    # 开始构建
                    result = builder.build(
                        config=self.current_config,
                        output_path=Path(output_file),
                        progress_callback=progress_callback
                    )
                    
                    if not progress.cancelled:
                        if result.success:
                            self._log("✅ 安装器构建成功！")
                            self._log(f"   输出文件: {result.output_path}")
                            self._log(f"   文件大小: {self._format_size(result.output_size)}")
                            
                            progress.root.after(0, lambda: progress.complete("构建完成"))
                            progress.root.after(1000, lambda: progress.destroy())
                            
                            # 询问是否打开输出目录
                            if messagebox.askyesno("构建完成", f"安装器构建成功！\\n\\n输出文件: {result.output_path}\\n\\n是否打开所在目录？"):
                                import subprocess
                                subprocess.run(f'explorer /select,"{result.output_path}"', shell=True)
                        else:
                            error_msg = result.error or "未知错误"
                            self._log(f"❌ 构建失败: {error_msg}")
                            progress.root.after(0, lambda: progress.set_error(f"构建失败: {error_msg}"))
                            
                except Exception as e:
                    error_msg = str(e)
                    self._log(f"❌ 构建异常: {error_msg}")
                    import traceback
                    self._log(f"详细错误: {traceback.format_exc()}")
                    progress.root.after(0, lambda: progress.set_error(f"构建异常: {error_msg}"))
            
            # 在后台线程启动构建
            import threading
            build_thread = threading.Thread(target=build_thread, daemon=True)
            build_thread.start()
        
        def _format_size(self, size_bytes: int) -> str:
            """格式化文件大小"""
            if size_bytes is None:
                return "未知"
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024
            return f"{size_bytes:.1f} TB"
        
        def _inspect_installer(self):
            """检查安装器"""
            filename = filedialog.askopenfilename(
                title="选择安装器文件",
                filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
            )
            if filename:
                self._log(f"🔍 检查安装器: {filename}")
                
                # TODO: 实现安装器检查逻辑
                # 这里是占位实现
                
                info = f"""
    安装器信息:
    文件: {filename}
    大小: {Path(filename).stat().st_size} 字节
    产品: Demo App v1.0.0
    压缩: zstd
    文件数: 12
    """
                self._log(info)
        
        def _clear_log(self):
            """清空日志"""
            self.log_text.delete("0.0", "end")
        
        def _show_help(self):
            """显示帮助"""
            help_text = """
    Inspa - Windows 安装器构建工具

    使用步骤:
    1. 选择配置文件 (inspa.yaml)
    2. 验证配置文件格式
    3. 设置输出路径 (可选)
    4. 选择构建选项
    5. 点击"开始构建"

    配置文件示例:
    参见 examples/demo_config.yaml

    更多帮助:
    https://github.com/your-repo/inspa
    """
            messagebox.showinfo("帮助", help_text)
        
        def _log(self, message: str):
            """添加日志消息"""
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_line = f"[{timestamp}] {message}\\n"
            
            self.log_text.insert("end", log_line)
            self.log_text.see("end")
            self.root.update()
        
        def _on_closing(self):
            """窗口关闭事件"""
            self.root.destroy()
        
        def run(self):
            """运行 GUI"""
            self.root.mainloop()
else:
    # 如果GUI不可用，提供存根类
    class BuilderGUI:
        def __init__(self):
            raise ImportError("GUI 依赖未安装，无法启动图形界面")
        
        def run(self):
            raise ImportError("GUI 依赖未安装，无法启动图形界面")


def main():
    """GUI 主函数"""
    if not GUI_AVAILABLE:
        print("错误: GUI 依赖未安装")
        print("请安装依赖: pip install customtkinter")
        return 1
    
    try:
        app = BuilderGUI()
        app.run()
        return 0
    except Exception as e:
        print(f"GUI 启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())