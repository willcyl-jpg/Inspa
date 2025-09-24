"""
安装器运行时GUI界面

为runtime_stub提供图形化安装界面
"""

import sys
from pathlib import Path
from typing import Optional, Callable

try:
    import customtkinter as ctk
    from tkinter import messagebox
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


class InstallerRuntimeGUI:
    """运行时安装器GUI界面
    
    为standalone_main.py提供GUI支持
    """
    
    def __init__(self, app_name: str = "应用程序", default_path: Optional[str] = None):
        if not GUI_AVAILABLE:
            raise ImportError("GUI依赖未安装，无法启动图形界面")
        
        self.app_name = app_name
        self.default_path = default_path
        self.cancelled = False
        self.selected_path = None
        self.progress_callback = None
        
        # 设置外观
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        
        # 创建主窗口
        self.root = ctk.CTk()
        self.root.title(f"{app_name} - 安装向导")
        self.root.geometry("500x350")
        self.root.resizable(False, False)
        
        # 居中显示
        self._center_window()
        
        # 当前状态
        self.state = "directory"  # directory, installing, completed, error
        
        # 控件变量
        self.install_path = ctk.StringVar(value=default_path or f"C:\\Program Files\\{app_name}")
        
        # 构建界面
        self._build_ui()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _center_window(self):
        """居中显示窗口"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def _build_ui(self):
        """构建用户界面"""
        # 主容器
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 标题
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text=f"安装 {self.app_name}",
            font=("Segoe UI", 18, "bold")
        )
        self.title_label.pack(pady=(20, 30))
        
        # 内容区域 - 根据状态动态切换
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # 按钮区域
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.install_button = ctk.CTkButton(
            self.button_frame,
            text="安装",
            font=("Segoe UI", 12),
            height=36,
            command=self._start_installation
        )
        self.install_button.pack(side="right")
        
        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="取消",
            font=("Segoe UI", 12),
            height=36,
            command=self._on_closing
        )
        self.cancel_button.pack(side="right", padx=(0, 10))
        
        # 显示目录选择界面
        self._show_directory_selection()
    
    def _show_directory_selection(self):
        """显示目录选择界面"""
        self.state = "directory"
        
        # 清除内容区域
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # 说明文字
        desc_label = ctk.CTkLabel(
            self.content_frame,
            text=f"选择 {self.app_name} 的安装位置:",
            font=("Segoe UI", 12)
        )
        desc_label.pack(pady=(20, 15))
        
        # 路径输入框
        path_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        path_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.path_entry = ctk.CTkEntry(
            path_frame,
            textvariable=self.install_path,
            font=("Segoe UI", 11),
            height=35
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        browse_button = ctk.CTkButton(
            path_frame,
            text="浏览...",
            font=("Segoe UI", 11),
            width=80,
            height=35,
            command=self._browse_directory
        )
        browse_button.pack(side="right")
        
        # 空间提示
        space_label = ctk.CTkLabel(
            self.content_frame,
            text="所需磁盘空间: 约 200 MB",
            font=("Segoe UI", 10),
            text_color="gray"
        )
        space_label.pack(pady=10)
        
        # 更新按钮状态
        self.install_button.configure(state="normal", text="安装")
        self.cancel_button.configure(state="normal")
    
    def _show_installation_progress(self):
        """显示安装进度界面"""
        self.state = "installing"
        
        # 清除内容区域
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # 进度标题
        progress_title = ctk.CTkLabel(
            self.content_frame,
            text="正在安装...",
            font=("Segoe UI", 14, "bold")
        )
        progress_title.pack(pady=(30, 20))
        
        # 进度条
        self.progress_bar = ctk.CTkProgressBar(
            self.content_frame,
            width=350,
            height=20
        )
        self.progress_bar.pack(pady=(0, 10))
        self.progress_bar.set(0)
        
        # 进度文字
        self.progress_var = ctk.StringVar(value="准备安装...")
        self.progress_label = ctk.CTkLabel(
            self.content_frame,
            textvariable=self.progress_var,
            font=("Segoe UI", 11)
        )
        self.progress_label.pack(pady=(0, 20))
        
        # 更新按钮状态
        self.install_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")
    
    def _show_completion(self, success: bool = True):
        """显示完成界面"""
        self.state = "completed" if success else "error"
        
        # 清除内容区域
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        if success:
            # 成功图标
            success_label = ctk.CTkLabel(
                self.content_frame,
                text="✓",
                font=("Segoe UI", 36, "bold"),
                text_color="green"
            )
            success_label.pack(pady=(20, 15))
            
            # 完成标题
            title_label = ctk.CTkLabel(
                self.content_frame,
                text="安装完成",
                font=("Segoe UI", 16, "bold")
            )
            title_label.pack(pady=(0, 15))
            
            # 完成消息
            message_label = ctk.CTkLabel(
                self.content_frame,
                text=f"{self.app_name} 已成功安装到:\n{self.install_path.get()}",
                font=("Segoe UI", 11),
                justify="center"
            )
            message_label.pack(pady=(0, 20))
            
            # 更新按钮
            self.install_button.configure(text="完成", command=self._finish)
        else:
            # 错误图标
            error_label = ctk.CTkLabel(
                self.content_frame,
                text="✗",
                font=("Segoe UI", 36, "bold"),
                text_color="red"
            )
            error_label.pack(pady=(20, 15))
            
            # 错误标题
            title_label = ctk.CTkLabel(
                self.content_frame,
                text="安装失败",
                font=("Segoe UI", 16, "bold"),
                text_color="red"
            )
            title_label.pack(pady=(0, 15))
            
            # 错误消息
            message_label = ctk.CTkLabel(
                self.content_frame,
                text="安装过程中发生错误",
                font=("Segoe UI", 11)
            )
            message_label.pack(pady=(0, 20))
            
            # 更新按钮
            self.install_button.configure(text="重试", command=self._show_directory_selection)
        
        # 重新启用按钮
        self.install_button.configure(state="normal")
        self.cancel_button.configure(state="normal")
    
    def _browse_directory(self):
        """浏览目录"""
        from tkinter import filedialog
        
        directory = filedialog.askdirectory(
            title="选择安装目录",
            initialdir=self.install_path.get()
        )
        if directory:
            self.install_path.set(directory)
    
    def _start_installation(self):
        """开始安装"""
        # 验证路径
        path = self.install_path.get().strip()
        if not path:
            messagebox.showerror("错误", "请选择安装目录")
            return
        
        self.selected_path = path
        self._show_installation_progress()
        
        # 如果有外部的安装回调，调用它
        if self.progress_callback:
            self.progress_callback(path)
    
    def _finish(self):
        """完成安装"""
        self.root.destroy()
    
    def _on_closing(self):
        """窗口关闭事件"""
        if self.state == "installing":
            if messagebox.askquestion("确认", "安装正在进行中，确定要取消吗？") == "yes":
                self.cancelled = True
                self.root.destroy()
        else:
            self.cancelled = True
            self.root.destroy()
    
    def update_progress(self, value: float, message: str = ""):
        """更新安装进度"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.set(value)
        if hasattr(self, 'progress_var') and message:
            self.progress_var.set(message)
        self.root.update()
    
    def show_error(self, error_message: str):
        """显示错误"""
        self._show_completion(success=False)
    
    def show_success(self):
        """显示成功"""
        self._show_completion(success=True)
    
    def set_progress_callback(self, callback: Callable[[str], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def run(self) -> Optional[str]:
        """运行GUI，返回选择的安装路径，如果取消则返回None"""
        self.root.mainloop()
        return None if self.cancelled else self.selected_path


# 测试函数
def test_gui():
    """测试GUI界面"""
    if not GUI_AVAILABLE:
        print("GUI依赖未安装，无法测试")
        return
    
    gui = InstallerRuntimeGUI("测试应用", "C:\\Program Files\\TestApp")
    
    def fake_install(path):
        import time
        import threading
        
        def install_process():
            for i in range(101):
                gui.update_progress(i/100.0, f"安装进度: {i}%")
                time.sleep(0.02)
            gui.show_success()
        
        thread = threading.Thread(target=install_process)
        thread.daemon = True
        thread.start()
    
    gui.set_progress_callback(fake_install)
    result = gui.run()
    print(f"安装路径: {result}")


if __name__ == "__main__":
    test_gui()