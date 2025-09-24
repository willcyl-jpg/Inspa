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
    
    def _browse_output(self):
        """浏览输出文件"""
        filename = filedialog.asksaveasfilename(
            title="保存安装器",
            defaultextension=".exe",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if filename:
            self.output_path.set(filename)
    
    def _validate_config(self):
        """验证配置文件"""
        config_file = self.config_path.get().strip()
        if not config_file:
            messagebox.showerror("错误", "请先选择配置文件")
            return
        
        self._log("开始验证配置文件...")
        
        # TODO: 实现配置验证逻辑
        # 这里是占位实现
        
        try:
            # 假设验证成功
            self._log(f"✅ 配置文件验证成功: {config_file}")
            messagebox.showinfo("成功", "配置文件验证成功！")
        except Exception as e:
            self._log(f"❌ 配置文件验证失败: {e}")
            messagebox.showerror("错误", f"配置文件验证失败:\n{e}")
    
    def _start_build(self):
        """开始构建"""
        config_file = self.config_path.get().strip()
        if not config_file:
            messagebox.showerror("错误", "请先选择配置文件")
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