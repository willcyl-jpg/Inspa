"""
GUI 界面模块

使用 CustomTkinter 构建现代化的安装和构建界面
映射需求：NFR-UI-001, NFR-UI-002, NFR-UI-003, FR-GUI-001, FR-GUI-003
"""

import os
import sys
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any

try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox, ttk
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("警告: GUI 依赖未安装，GUI 功能不可用")


class ModernButton(ctk.CTkButton):
    """现代化按钮组件"""
    
    def __init__(self, *args, **kwargs):
        # 设置默认样式
        kwargs.setdefault('height', 36)
        kwargs.setdefault('font', ('Segoe UI', 11))
        kwargs.setdefault('corner_radius', 6)
        super().__init__(*args, **kwargs)


class ModernFrame(ctk.CTkFrame):
    """现代化框架组件"""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('corner_radius', 8)
        super().__init__(*args, **kwargs)


class ProgressDialog(ctk.CTkToplevel):
    """进度对话框"""
    
    def __init__(self, parent, title: str = "处理中"):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x150")
        self.resizable(False, False)
        
        # 居中显示
        self.transient(parent)
        self.grab_set()
        
        # 进度条
        self.progress_var = ctk.StringVar(value="准备中...")
        self.progress_label = ctk.CTkLabel(self, textvariable=self.progress_var, font=('Segoe UI', 11))
        self.progress_label.pack(pady=(20, 10))
        
        self.progress_bar = ctk.CTkProgressBar(self, width=300)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        # 取消按钮
        self.cancel_button = ModernButton(self, text="取消", command=self.destroy)
        self.cancel_button.pack(pady=10)
        
        # 结果标志
        self.cancelled = False
    
    def update_progress(self, value: float, message: str = ""):
        """更新进度"""
        self.progress_bar.set(value)
        if message:
            self.progress_var.set(message)
        self.update()
    
    def destroy(self):
        """关闭对话框"""
        self.cancelled = True
        super().destroy()


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
        self.current_config: Optional[Dict[str, Any]] = None
        
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
            from ..config import load_config, validate_config
            
            # 加载配置
            config = load_config(Path(config_file))
            
            # 验证配置
            validation_result = validate_config(config)
            
            if validation_result.is_valid:
                self._log(f"✅ 配置文件验证成功: {Path(config_file).name}")
                messagebox.showinfo("成功", "配置文件验证成功！")
                self.current_config = config
            else:
                error_msg = "\n".join([f"• {error}" for error in validation_result.errors])
                self._log(f"❌ 配置文件验证失败:")
                for error in validation_result.errors:
                    self._log(f"   • {error}")
                messagebox.showerror("验证失败", f"配置文件存在问题:\n\n{error_msg}")
                
        except Exception as e:
            error_msg = str(e)
            self._log(f"❌ 配置文件验证失败: {error_msg}")
            messagebox.showerror("错误", f"配置文件验证失败:\n{error_msg}")
    
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
                        if messagebox.askyesno("构建完成", f"安装器构建成功！\n\n输出文件: {result.output_path}\n\n是否打开所在目录？"):
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
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
            return
        
        self._log("🔨 开始构建安装器...")
        
        # 创建进度对话框
        progress = ProgressDialog(self.root, "构建安装器")
        
        def build_thread():
            try:
                # TODO: 实现实际的构建逻辑
                # 这里是占位实现
                
                # 模拟构建步骤
                steps = [
                    ("解析配置", 0.1),
                    ("收集文件", 0.3),
                    ("压缩数据", 0.6),
                    ("生成头部", 0.8),
                    ("创建安装器", 1.0)
                ]
                
                for step_name, progress_value in steps:
                    if progress.cancelled:
                        break
                    
                    progress.update_progress(progress_value, f"正在{step_name}...")
                    threading.Event().wait(1)  # 模拟处理时间
                
                if not progress.cancelled:
                    self._log("✅ 安装器构建成功！")
                    messagebox.showinfo("成功", "安装器构建完成！")
                
            except Exception as e:
                self._log(f"❌ 构建失败: {e}")
                messagebox.showerror("错误", f"构建失败:\n{e}")
            finally:
                progress.destroy()
        
        # 在后台线程中运行构建
        threading.Thread(target=build_thread, daemon=True).start()
    
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
        log_line = f"[{timestamp}] {message}\n"
        
        self.log_text.insert("end", log_line)
        self.log_text.see("end")
        self.root.update()
    
    def _on_closing(self):
        """窗口关闭事件"""
        self.root.destroy()
    
    def run(self):
        """运行 GUI"""
        self.root.mainloop()


class InstallerGUI:
    """Inspa 安装器界面"""
    
    def __init__(self, installer_name: str = "应用程序", default_path: Optional[str] = None):
        if not GUI_AVAILABLE:
            raise ImportError("GUI 依赖未安装，无法启动图形界面")
        
        self.installer_name = installer_name
        self.default_path = default_path
        self.cancelled = False
        self.selected_path = None
        
        # 设置外观模式和颜色主题
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        
        # 创建主窗口
        self.root = ctk.CTk()
        self.root.title(f"{installer_name} - 安装向导")
        self.root.geometry("600x450")
        self.root.resizable(False, False)
        
        # 居中显示窗口
        self._center_window()
        
        # 配置 DPI 缩放
        self._configure_dpi()
        
        # 初始化变量
        self.install_path = ctk.StringVar(value=default_path or f"C:\\Program Files\\{installer_name}")
        self.current_step = 0
        self.steps = ["欢迎", "选择安装目录", "正在安装", "完成"]
        
        # 构建界面
        self._build_ui()
        
        # 绑定事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _center_window(self):
        """居中显示窗口"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def _configure_dpi(self):
        """配置 DPI 缩放"""
        try:
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    
    def _build_ui(self):
        """构建用户界面"""
        # 主容器
        main_container = ModernFrame(self.root)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 标题区域
        title_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 20))
        
        self.title_label = ctk.CTkLabel(
            title_frame,
            text=f"安装 {self.installer_name}",
            font=("Segoe UI", 20, "bold")
        )
        self.title_label.pack()
        
        # 步骤指示器
        self.step_frame = ctk.CTkFrame(main_container, height=50)
        self.step_frame.pack(fill="x", pady=(0, 20))
        self.step_frame.pack_propagate(False)
        
        # 内容区域
        self.content_frame = ctk.CTkFrame(main_container)
        self.content_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # 按钮区域
        button_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        button_frame.pack(fill="x")
        
        self.back_button = ModernButton(button_frame, text="上一步", command=self._previous_step)
        self.back_button.pack(side="left")
        
        self.next_button = ModernButton(button_frame, text="下一步", command=self._next_step)
        self.next_button.pack(side="right")
        
        self.cancel_button = ModernButton(button_frame, text="取消", command=self._on_closing)
        self.cancel_button.pack(side="right", padx=(0, 10))
        
        # 显示第一步
        self._show_step(0)
    
    def _show_step_indicator(self):
        """显示步骤指示器"""
        # 清除现有内容
        for widget in self.step_frame.winfo_children():
            widget.destroy()
        
        # 创建步骤指示器
        indicator_frame = ctk.CTkFrame(self.step_frame, fg_color="transparent")
        indicator_frame.pack(expand=True, fill="both")
        
        for i, step_name in enumerate(self.steps):
            # 步骤圆圈
            color = "blue" if i <= self.current_step else "gray"
            step_circle = ctk.CTkLabel(
                indicator_frame,
                text=str(i + 1),
                width=30,
                height=30,
                fg_color=color,
                text_color="white",
                font=("Segoe UI", 12, "bold"),
                corner_radius=15
            )
            step_circle.grid(row=0, column=i * 2, padx=5, pady=10)
            
            # 步骤名称
            step_label = ctk.CTkLabel(
                indicator_frame,
                text=step_name,
                font=("Segoe UI", 10),
                text_color="blue" if i <= self.current_step else "gray"
            )
            step_label.grid(row=1, column=i * 2, padx=5)
            
            # 连接线（除了最后一个）
            if i < len(self.steps) - 1:
                line_color = "blue" if i < self.current_step else "gray"
                line = ctk.CTkLabel(
                    indicator_frame,
                    text="─────",
                    text_color=line_color,
                    font=("Segoe UI", 8)
                )
                line.grid(row=0, column=i * 2 + 1, padx=2, pady=10)
        
        # 配置网格权重
        for i in range(len(self.steps) * 2 - 1):
            indicator_frame.grid_columnconfigure(i, weight=1)
    
    def _show_step(self, step: int):
        """显示指定步骤"""
        self.current_step = step
        self._show_step_indicator()
        
        # 清除内容区域
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        if step == 0:
            self._show_welcome_step()
        elif step == 1:
            self._show_directory_step()
        elif step == 2:
            self._show_installation_step()
        elif step == 3:
            self._show_completion_step()
        
        # 更新按钮状态
        self.back_button.configure(state="disabled" if step == 0 else "normal")
        self.cancel_button.configure(state="disabled" if step == 2 else "normal")
        
        if step == 0:
            self.next_button.configure(text="下一步")
        elif step == 1:
            self.next_button.configure(text="安装")
        elif step == 2:
            self.next_button.configure(state="disabled")
        elif step == 3:
            self.next_button.configure(text="完成")
    
    def _show_welcome_step(self):
        """显示欢迎页面"""
        welcome_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        welcome_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # 欢迎图标或图片（可选）
        welcome_label = ctk.CTkLabel(
            welcome_frame,
            text=f"欢迎使用 {self.installer_name} 安装向导",
            font=("Segoe UI", 16, "bold")
        )
        welcome_label.pack(pady=(40, 20))
        
        description = ctk.CTkLabel(
            welcome_frame,
            text=f"这个向导将指导您在计算机上安装 {self.installer_name}。\n\n"
                 f"建议您在继续之前关闭所有其他应用程序。\n\n"
                 f"点击\"下一步\"继续，或点击\"取消\"退出安装向导。",
            font=("Segoe UI", 11),
            justify="left"
        )
        description.pack(pady=20, padx=20)
    
    def _show_directory_step(self):
        """显示目录选择页面"""
        dir_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        dir_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        title = ctk.CTkLabel(
            dir_frame,
            text="选择安装目录",
            font=("Segoe UI", 16, "bold")
        )
        title.pack(pady=(20, 20))
        
        description = ctk.CTkLabel(
            dir_frame,
            text=f"安装程序将把 {self.installer_name} 安装到以下目录。\n"
                 f"若要安装到不同目录，请点击\"浏览\"并选择其他目录。",
            font=("Segoe UI", 11),
            justify="left"
        )
        description.pack(pady=(0, 20), padx=20)
        
        # 路径选择区域
        path_frame = ctk.CTkFrame(dir_frame)
        path_frame.pack(fill="x", padx=20, pady=10)
        
        path_label = ctk.CTkLabel(path_frame, text="目标目录:", font=("Segoe UI", 11))
        path_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        path_entry_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
        path_entry_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        self.path_entry = ctk.CTkEntry(
            path_entry_frame,
            textvariable=self.install_path,
            font=("Segoe UI", 11),
            height=32
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        browse_button = ModernButton(
            path_entry_frame,
            text="浏览...",
            width=80,
            command=self._browse_directory
        )
        browse_button.pack(side="right")
        
        # 磁盘空间信息（可选）
        space_label = ctk.CTkLabel(
            dir_frame,
            text="所需磁盘空间: 约 200 MB",
            font=("Segoe UI", 10),
            text_color="gray"
        )
        space_label.pack(pady=10)
    
    def _show_installation_step(self):
        """显示安装进度页面"""
        install_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        install_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        title = ctk.CTkLabel(
            install_frame,
            text="正在安装...",
            font=("Segoe UI", 16, "bold")
        )
        title.pack(pady=(40, 30))
        
        # 进度条
        self.progress_var = ctk.StringVar(value="准备安装...")
        self.progress_label = ctk.CTkLabel(
            install_frame,
            textvariable=self.progress_var,
            font=("Segoe UI", 11)
        )
        self.progress_label.pack(pady=(0, 10))
        
        self.progress_bar = ctk.CTkProgressBar(install_frame, width=400, height=20)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        # 安装详情（可选）
        self.detail_label = ctk.CTkLabel(
            install_frame,
            text="",
            font=("Segoe UI", 9),
            text_color="gray"
        )
        self.detail_label.pack(pady=10)
    
    def _show_completion_step(self):
        """显示完成页面"""
        complete_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        complete_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # 成功图标
        success_label = ctk.CTkLabel(
            complete_frame,
            text="✓",
            font=("Segoe UI", 48, "bold"),
            text_color="green"
        )
        success_label.pack(pady=(30, 20))
        
        title = ctk.CTkLabel(
            complete_frame,
            text="安装完成",
            font=("Segoe UI", 16, "bold")
        )
        title.pack(pady=(0, 20))
        
        message = ctk.CTkLabel(
            complete_frame,
            text=f"{self.installer_name} 已成功安装到您的计算机上。\n\n"
                 f"安装位置: {self.install_path.get()}\n\n"
                 f"点击\"完成\"关闭安装向导。",
            font=("Segoe UI", 11),
            justify="center"
        )
        message.pack(pady=10, padx=20)
    
    def _browse_directory(self):
        """浏览目录"""
        directory = filedialog.askdirectory(
            title="选择安装目录",
            initialdir=os.path.dirname(self.install_path.get())
        )
        if directory:
            self.install_path.set(directory)
    
    def _previous_step(self):
        """上一步"""
        if self.current_step > 0:
            self._show_step(self.current_step - 1)
    
    def _next_step(self):
        """下一步"""
        if self.current_step == 1:
            # 验证路径
            path = self.install_path.get().strip()
            if not path:
                messagebox.showerror("错误", "请选择安装目录")
                return
            
            self.selected_path = path
            self._show_step(2)
            # 开始安装
            self._start_installation()
        elif self.current_step == 3:
            # 完成安装，关闭窗口
            self.root.destroy()
        else:
            if self.current_step < len(self.steps) - 1:
                self._show_step(self.current_step + 1)
    
    def _start_installation(self):
        """开始安装（在后台线程中运行）"""
        def install_thread():
            try:
                # 模拟安装过程
                for i in range(101):
                    if self.cancelled:
                        return
                    
                    # 更新进度
                    self.root.after(0, self._update_progress, i/100.0, f"安装进度: {i}%")
                    
                    # 模拟安装延迟
                    threading.Event().wait(0.02)
                
                # 安装完成
                if not self.cancelled:
                    self.root.after(0, self._installation_complete)
                    
            except Exception as e:
                self.root.after(0, self._installation_error, str(e))
        
        # 在新线程中开始安装
        install_thread = threading.Thread(target=install_thread, daemon=True)
        install_thread.start()
    
    def _update_progress(self, value: float, message: str):
        """更新安装进度"""
        self.progress_bar.set(value)
        self.progress_var.set(message)
        
        # 更新详细信息
        if value < 0.3:
            self.detail_label.configure(text="正在解压文件...")
        elif value < 0.7:
            self.detail_label.configure(text="正在复制文件...")
        else:
            self.detail_label.configure(text="正在完成安装...")
    
    def _installation_complete(self):
        """安装完成"""
        self._show_step(3)
    
    def _installation_error(self, error_message: str):
        """安装错误"""
        messagebox.showerror("安装错误", f"安装过程中发生错误:\n{error_message}")
        self._show_step(1)  # 返回目录选择页面
    
    def _on_closing(self):
        """窗口关闭事件"""
        if self.current_step == 2:  # 正在安装
            if messagebox.askquestion("确认", "安装正在进行中，确定要取消吗？") == "yes":
                self.cancelled = True
                self.root.destroy()
        else:
            self.cancelled = True
            self.root.destroy()
    
    def run(self) -> Optional[str]:
        """运行安装向导，返回选择的安装路径，如果取消则返回None"""
        self.root.mainloop()
        return None if self.cancelled else self.selected_path


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