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
import traceback
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, TYPE_CHECKING

# GUI 依赖导入
try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    if not TYPE_CHECKING:
        # 仅在运行时设置为 None，类型检查时保持导入
        ctk = None
        filedialog = None
        messagebox = None
        print("警告: GUI 依赖未安装，GUI 功能不可用")

# 核心模块导入
try:
    from inspa.config.schema import InspaConfig, ProductModel, InstallModel, CompressionAlgorithm
    from inspa.config.loader import load_config
    from inspa.build.builder import Builder as InspaBuilder
    CORE_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入 Inspa 核心模块: {e}")
    # 尝试相对导入
    try:
        from ..config.schema import InspaConfig, ProductModel, InstallModel, CompressionAlgorithm
        from ..config.loader import load_config
        from ..build.builder import Builder as InspaBuilder
        CORE_MODULES_AVAILABLE = True
    except ImportError as e2:
        print(f"警告: 相对导入也失败: {e2}")
        CORE_MODULES_AVAILABLE = False
        if not TYPE_CHECKING:
            # 定义存根类以避免运行时错误
            from typing import Any
            
            class InspaConfig:
                def __init__(self, *args: Any, **kwargs: Any) -> None: ...
            
            class ProductModel:
                def __init__(self, *args: Any, **kwargs: Any) -> None: ...
            
            class InstallModel:
                def __init__(self, *args: Any, **kwargs: Any) -> None: ...
                
            class CompressionAlgorithm:
                ZSTD = "zstd"
                ZIP = "zip"
                
            def load_config(path: Any) -> Any:
                raise NotImplementedError("核心模块未可用")
                
            class InspaBuilder:
                def __init__(self, *args: Any, **kwargs: Any) -> None: ...

# 类型检查时的导入
if TYPE_CHECKING:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox
    from inspa.config.schema import InspaConfig, ProductModel, InstallModel, CompressionAlgorithm
    from inspa.config.loader import load_config
    from inspa.build.builder import Builder as InspaBuilder


# 仅在GUI可用时定义GUI类
if GUI_AVAILABLE and ctk is not None:
    
    # 设置 CustomTkinter 主题和外观 (固定暗色)
    ctk.set_appearance_mode("dark")

    # 引入抽离主题和组件
    from .theme import Colors, Fonts, Style, Spacing
    from .widgets import CollapsibleSection, FieldFrame
    from .dialogs import BuildProgressDialog, PostActionDialog
    from .pages.license_page import LicensePage
    from .pages.ui_page import UIPage
    from .pages.files_page import FilesPage
    from .pages.advanced_page import AdvancedPage
    from .pages.build_page import BuildPage
    from .pages.base_page import BasePage
    from .pages.general_page import GeneralPage
    from .pages.post_install_page import PostInstallPage


    class BuilderGUI:
        """Inspa 构建器主界面"""
        
        def __init__(self):
            self.root = ctk.CTk()
            self.config_data = {}
            
            # 页面定义 - 根据新需求重构
            self._page_classes = {
                "general": ("基本信息", GeneralPage),
                "license": ("许可协议", LicensePage),
                "files": ("文件与目录", FilesPage),
                "post_install": ("安装后", PostInstallPage),
                "advanced": ("高级选项", AdvancedPage),
                "build": ("构建", BuildPage),
                "ui": ("安装界面", UIPage),
            }
            self.nav_buttons: Dict[str, ctk.CTkButton] = {}
            self._page_containers: Dict[str, ctk.CTkScrollableFrame] = {}
            self._page_instances: Dict[str, BasePage] = {}
            self._active_page_key: Optional[str] = None
            
            self.setup_window()
            self.setup_ui()
            self.load_default_config()
            
            if not CORE_MODULES_AVAILABLE:
                self.root.title("Inspa - Windows 安装器构建工具 (核心模块未加载)")
        
        def setup_window(self):
            """设置窗口 (移除渐变/淡入缩放动画)"""
            self.root.title("Inspa - Windows 安装器构建工具")
            self.center_window()
        
        def center_window(self):
            """窗口居中 (无动画)"""
            self.root.update_idletasks()
            w = 1100
            h = 800
            x = (self.root.winfo_screenwidth() // 2) - (w // 2)
            y = (self.root.winfo_screenheight() // 2) - (h // 2)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.root.minsize(800, 600)
        
        def setup_ui(self):
            """设置用户界面 - 统一使用 Grid 布局"""
            self.root.configure(fg_color=Colors.BACKGROUND)
            self.root.grid_columnconfigure(1, weight=1)
            self.root.grid_rowconfigure(0, weight=1)

            # 左侧导航栏
            self.nav_frame = ctk.CTkFrame(
                self.root,
                width=220,
                fg_color=Colors.SURFACE,
                corner_radius=0,
                border_width=0,
            )
            self.nav_frame.grid(row=0, column=0, sticky="ns")
            self.nav_frame.grid_propagate(False)

            # 右侧主内容区
            self.main_frame = ctk.CTkFrame(self.root, fg_color='transparent')
            self.main_frame.grid(row=0, column=1, sticky="nsew")
            self.main_frame.grid_rowconfigure(0, weight=1)
            self.main_frame.grid_columnconfigure(0, weight=1)

            # 创建并叠放所有页面
            for key, (name, PageClass) in self._page_classes.items():
                page_container = ctk.CTkScrollableFrame(self.main_frame, fg_color=Colors.BACKGROUND, corner_radius=0)
                page_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
                
                # 创建页面实例并直接添加到容器中
                page_instance = PageClass(page_container, self)
                
                self._page_containers[key] = page_container
                self._page_instances[key] = page_instance

            self._build_navigation()
            self.setup_status_bar()
            self._show_page('general')

        def _build_navigation(self):
            """构建左侧导航栏 (纯 Grid 布局)。"""
            self.nav_frame.grid_rowconfigure(2, weight=1) # 让按钮区域可扩展

            # Logo
            logo_font = ctk.CTkFont(family=Fonts.FAMILY, size=Fonts.H2[1], weight="bold")
            logo_label = ctk.CTkLabel(self.nav_frame, text="Inspa", font=logo_font, text_color=Colors.PRIMARY, anchor="w")
            logo_label.grid(row=0, column=0, padx=Spacing.L, pady=Spacing.L, sticky="ew")

            # 导入/导出按钮
            config_action_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
            config_action_frame.grid(row=1, column=0, sticky="ew", padx=Spacing.M, pady=(0, Spacing.M))
            config_action_frame.grid_columnconfigure((0, 1), weight=1)
            
            import_button = self.add_button(config_action_frame, "导入", self.import_config, Style.BUTTON_SECONDARY)
            import_button.grid(row=0, column=0, padx=(0, Spacing.S / 2), sticky="ew")
            
            export_button = self.add_button(config_action_frame, "导出", self.export_config, Style.BUTTON_SECONDARY)
            export_button.grid(row=0, column=1, padx=(Spacing.S / 2, 0), sticky="ew")

            # 导航按钮
            button_frame = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
            button_frame.grid(row=2, column=0, sticky="nsew", padx=Spacing.M, pady=(Spacing.M, 0))
            button_frame.grid_columnconfigure(0, weight=1)

            for i, (key, (name, _)) in enumerate(self._page_classes.items()):
                button = self.add_button(button_frame, name, lambda k=key: self._show_page(k), Style.BUTTON_NAV)
                button.grid(row=i, column=0, sticky="ew", pady=(0, Spacing.S / 2))
                self.nav_buttons[key] = button

            # 主题切换
            theme_switch = ctk.CTkSwitch(self.nav_frame, text="浅色模式", command=self._toggle_theme, onvalue="light", offvalue="dark")
            theme_switch.grid(row=3, column=0, padx=Spacing.M, pady=Spacing.M, sticky="s")
            if ctk.get_appearance_mode().lower() == "light":
                theme_switch.select()
            else:
                theme_switch.deselect()

        def _toggle_theme(self):
            """切换主题"""
            new_mode = "light" if ctk.get_appearance_mode().lower() == "dark" else "dark"
            ctk.set_appearance_mode(new_mode)

        def _show_page(self, key_to_show: str):
            """显示指定的页面"""
            # 隐藏所有页面
            for container in self._page_containers.values():
                container.grid_remove()
            
            # 显示选中的页面
            page_container = self._page_containers.get(key_to_show)
            if page_container:
                page_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
                self._active_page_key = key_to_show

            # 更新导航按钮状态
            for key, button in self.nav_buttons.items():
                if key == key_to_show:
                    button.configure(fg_color=Colors.PRIMARY)
                else:
                    button.configure(fg_color="transparent")

        def add_button(self, master, text, command, style: Dict[str, Any]):
            """创建并返回一个统一样式的 ctk 按钮"""
            button = ctk.CTkButton(
                master,
                text=text,
                command=command,
                **style
            )
            return button

        def setup_status_bar(self):
            """设置状态栏"""
            status_bar = ctk.CTkFrame(self.root, height=28, fg_color=Colors.SURFACE_LIGHT, corner_radius=0)
            # 使用 grid 替代 pack
            status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
            self.status_label = ctk.CTkLabel(status_bar, text="就绪", font=Fonts.SMALL, text_color=Colors.TEXT_MUTED)
            self.status_label.pack(side='left', padx=12) # pack 在这里是安全的，因为 status_bar 内部没有其他 grid

        def load_default_config(self):
            """加载默认配置"""
            # 可以在这里从文件加载配置并分发到各个页面
            # for key, page in self._pages.items():
            #     if hasattr(page, 'load_data'):
            #         page.load_data(self.config_data.get(key, {}))
            pass

        def import_config(self):
            """导入 YAML 配置文件"""
            path = filedialog.askopenfilename(
                title="导入配置文件",
                filetypes=[("YAML 文件", "*.yaml *.yml"), ("所有文件", "*.*")]
            )
            if not path:
                return

            try:
                from inspa.config.loader import load_config
                config_data = load_config(Path(path))
                
                # 将 InspaConfig 对象转换为字典
                config_dict = config_data.model_dump(exclude_none=True)

                for key, page in self._page_instances.items():
                    if hasattr(page, 'load_data'):
                        # 传递与页面相关的部分数据
                        page_data = {}
                        if key == 'general':
                            page_data['product'] = config_dict.get('product', {})
                            page_data['metadata'] = config_dict.get('metadata', {})
                        elif key == 'license':
                             page_data['license'] = config_dict.get('install', {}).get('license', {})
                        elif key == 'files':
                            page_data['inputs'] = config_dict.get('inputs', [])
                        elif key == 'post_install':
                            page_data['post_install'] = config_dict.get('post_actions', []) # Fix: post_actions
                        elif key == 'advanced':
                            page_data['advanced'] = {
                                'exclude': config_dict.get('exclude', []),
                                'env': config_dict.get('env', {}),
                                'validation': config_dict.get('validation', {})
                            }
                        elif key == 'build':
                            page_data['compression'] = config_dict.get('compression', {})
                            # output_path is part of the main config, not build page data
                            page_data['output_path'] = config_dict.get('output_path', '')
                        elif key == 'ui':
                            page_data['ui'] = config_dict.get('ui', {})
                        
                        if page_data:
                            page.load_data(page_data)

                self.status_label.configure(text=f"配置已从 {Path(path).name} 导入")
                messagebox.showinfo("成功", "配置文件已成功导入并加载到界面。")

            except Exception as e:
                messagebox.showerror("导入失败", f"无法导入配置文件：\n{e}")
                traceback.print_exc()

        def export_config(self):
            """导出当前UI配置为 YAML 文件"""
            path = filedialog.asksaveasfilename(
                title="导出配置文件",
                defaultextension=".yaml",
                filetypes=[("YAML 文件", "*.yaml *.yml")]
            )
            if not path:
                return

            try:
                config_data = self._gather_config_from_ui()
                
                from ruamel.yaml import YAML
                yaml = YAML()
                yaml.indent(mapping=2, sequence=4, offset=2)

                with open(path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f)
                
                self.status_label.configure(text=f"配置已导出到 {Path(path).name}")
                messagebox.showinfo("成功", f"当前配置已成功导出到：\n{path}")

            except Exception as e:
                messagebox.showerror("导出失败", f"无法导出配置文件：\n{e}")
                traceback.print_exc()

        def browse_output_path(self):
            """浏览并选择输出文件路径"""
            path = filedialog.asksaveasfilename(
                title="选择输出文件路径",
                defaultextension=".exe",
                filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
            )
            if path:
                if 'build' in self._page_instances:
                    build_page = self._page_instances['build']
                    if isinstance(build_page, BuildPage) and hasattr(build_page, 'output_path'):
                        build_page.output_path.delete(0, 'end')
                        build_page.output_path.insert(0, path)

        def build_installer(self):
            """收集配置并启动构建过程"""
            try:
                config_dict = self._gather_config_from_ui()
                output_file_path = config_dict.get("output_path")
                if not output_file_path:
                    messagebox.showerror("错误", "请在“构建”页面指定输出文件路径。")
                    return

                config = InspaConfig(**config_dict)
                
                builder = InspaBuilder()
                progress_dialog = BuildProgressDialog(self.root)
                
                def progress_callback_adapter(status: str, current: int, total: int, message: str):
                    if status == "错误":
                        progress_dialog.show_error(message)
                    elif status == "完成":
                        progress_dialog.show_success(output_file_path)
                    else:
                        progress = current / total if total > 0 else 0
                        progress_dialog.update_progress(progress, status, message)

                build_thread = threading.Thread(
                    target=self._run_build, 
                    args=(builder, config, Path(output_file_path), progress_callback_adapter),
                    daemon=True
                )
                build_thread.start()

            except Exception as e:
                messagebox.showerror("配置错误", f"无法开始构建，错误: {e}")
                traceback.print_exc()

        def _gather_config_from_ui(self, for_export: bool = False) -> dict:
            """从UI收集所有配置"""
            config_data = {}
            for key, page in self._page_instances.items():
                if hasattr(page, 'get_data'):
                    config_data.update(page.get_data())
            
            # 展平数据结构以匹配 InspaConfig
            flat_config = {}
            
            # General Page
            general_data = config_data.get('general', {})
            flat_config['product'] = general_data.get('product', {})
            flat_config['metadata'] = general_data.get('metadata', {})

            # License Page
            license_data = config_data.get('license', {})
            
            # Files Page
            files_data = config_data.get('files', {})
            flat_config['inputs'] = files_data.get('inputs', [])

            # Post-Install Page
            post_install_data = config_data.get('post_install', [])
            flat_config['post_actions'] = post_install_data # Fix: post_actions

            # Advanced Page
            advanced_data = config_data.get('advanced', {})
            flat_config['exclude'] = advanced_data.get('exclude', [])
            flat_config['env'] = advanced_data.get('env', {})
            flat_config['validation'] = advanced_data.get('validation', {})

            # Build Page
            build_data = config_data.get('build', {})
            flat_config['compression'] = build_data.get('compression', {})
            flat_config['output_path'] = build_data.get('output_path', '')

            # UI Page
            ui_data = config_data.get('ui', {})
            flat_config['ui'] = ui_data

            # Install settings are a mix from different pages
            install_settings = flat_config.get('install', {})
            install_settings["license"] = license_data
            flat_config['install'] = install_settings
            
            # Clean up empty optional fields for export
            if for_export:
                # Create a deep copy to avoid modifying the original
                export_dict = json.loads(json.dumps(flat_config))
                
                # Remove root-level keys if they are empty or default
                if not export_dict.get('exclude'): export_dict.pop('exclude', None)
                if not export_dict.get('env'): export_dict.pop('env', None)
                if not export_dict.get('validation'): export_dict.pop('validation', None)
                if not export_dict.get('post_actions'): export_dict.pop('post_actions', None)
                if not export_dict.get('resources'): export_dict.pop('resources', None)
                
                # Remove empty sub-keys
                if 'install' in export_dict and not export_dict['install'].get('license'):
                    export_dict['install'].pop('license', None)
                if not export_dict.get('install'):
                    export_dict.pop('install', None)

                return export_dict


            # For building, we need to ensure the structure is valid for InspaConfig
            # This might require more transformation depending on the final schema
            return flat_config


        def _create_inspa_config(self, data: dict) -> InspaConfig:
            """从收集的数据创建InspaConfig对象"""
            # 这个方法现在可以被 _gather_config_from_ui 和 InspaConfig(**data) 替代
            # 但暂时保留以防需要更复杂的转换逻辑
            return InspaConfig(**data)

        def _run_build(self, builder: InspaBuilder, config: InspaConfig, output_path: Path, progress_callback: Callable):
            """在后台线程中运行构建过程"""
            try:
                result = builder.build(config=config, output_path=output_path, progress_callback=progress_callback)
                if result.success:
                    self.root.after(100, lambda: progress_callback("完成", 100, 100, f"构建成功: {result.output_path}"))
                else:
                    self.root.after(100, lambda: progress_callback("错误", 0, 100, result.error or "未知构建错误"))
            except Exception as e:
                error_msg = f"构建时发生严重错误: {e}"
                traceback.print_exc()
                self.root.after(100, lambda: progress_callback("错误", 0, 100, error_msg))

        def run(self):
            """运行主循环."""
            self.root.mainloop()
