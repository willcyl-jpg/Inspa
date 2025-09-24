"""
Runtime Stub - 独立版本

这是一个可以独立编译的 runtime stub，不依赖 inspa 包的其他部分。
用于创建自解压安装器的可执行部分。
"""

import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional

# GUI支持 - 可选依赖
try:
    import customtkinter as ctk
    from tkinter import messagebox, filedialog
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Inspa 安装器",
        add_help=False
    )
    
    parser.add_argument(
        "-S", "--silent", 
        action="store_true",
        help="静默安装模式"
    )
    
    parser.add_argument(
        "-D", "--dir",
        type=str,
        help="自定义安装目录"
    )
    
    return parser.parse_args()


class InstallerRuntime:
    """安装器运行时"""
    
    def __init__(self, installer_path: Path):
        self.installer_path = installer_path
        self.header_data: Optional[Dict[str, Any]] = None
        self.compressed_data: Optional[bytes] = None
        
    def run_installation(
        self, 
        silent: bool = False, 
        custom_install_dir: Optional[str] = None,
        use_gui: bool = False
    ) -> bool:
        """运行安装"""
        # 如果请求GUI但GUI不可用，回退到命令行模式
        if use_gui and not GUI_AVAILABLE:
            if not silent:
                print("GUI不可用，使用命令行模式")
            use_gui = False
        
        # 使用GUI模式
        if use_gui:
            return self._run_gui_installation(custom_install_dir)
        
        # 命令行模式
        try:
            if not silent:
                print("开始安装流程")
                print("正在解析安装器...")
            
            # 解析安装器文件
            self._parse_installer()
            
            if not self.header_data:
                if not silent:
                    print("错误: 无法解析安装器头部")
                return False
            
            # 确定安装目录
            install_dir = self._determine_install_dir(custom_install_dir)
            if not silent:
                print(f"安装目录: {install_dir}")
            
            # 创建安装目录
            install_dir.mkdir(parents=True, exist_ok=True)
            
            # 解压文件
            self._extract_files(install_dir, silent)
            
            # 运行安装脚本（如果有）
            self._run_install_scripts(install_dir, silent)
            
            if not silent:
                print("安装完成！")
                
            return True
            
        except Exception as e:
            if not silent:
                print(f"安装失败: {e}")
            return False
    
    def _parse_installer(self) -> None:
        """解析安装器文件，提取头部信息和压缩数据"""
        try:
            with open(self.installer_path, 'rb') as f:
                # 移动到文件末尾
                f.seek(0, 2)
                file_size = f.tell()
                
                # 读取最后32字节的哈希值
                f.seek(-32, 2)
                stored_hash = f.read(32).hex()
                
                # 计算stub大小：找到header_len开始的位置
                # 从后往前找：32字节hash + compressed_data + header + 8字节header_len
                # 先尝试从不同位置读取header_len，找到合理的值
                
                # 读取压缩数据直到找到header_len位置
                found_header = False
                for stub_size_guess in range(100*1024, file_size - 1024, 1024):  # 从100KB开始每1KB尝试
                    try:
                        # 尝试读取header_len
                        f.seek(stub_size_guess)
                        header_len_bytes = f.read(8)
                        if len(header_len_bytes) < 8:
                            continue
                        
                        header_len = struct.unpack('<Q', header_len_bytes)[0]
                        
                        # 检查header_len是否合理 (100B-100KB)
                        if 100 <= header_len <= 100*1024:
                            # 验证文件大小是否匹配：stub + 8 + header + compressed + 32
                            compressed_size = file_size - 32 - stub_size_guess - 8 - header_len
                            if compressed_size > 0:  # 压缩数据大小必须为正
                                found_header = True
                                stub_size = stub_size_guess
                                break
                    except (struct.error, OSError):
                        continue
                
                if not found_header:
                    raise ValueError("无法找到有效的头部信息")
                
                # 现在解析各个部分
                # 1. 读取header
                f.seek(stub_size + 8)  # 跳过stub和header_len
                header_bytes = f.read(header_len)
                
                if len(header_bytes) != header_len:
                    raise ValueError(f"头部数据读取不完整: 期望{header_len}字节，实际{len(header_bytes)}字节")
                
                # 2. 解析JSON头部
                try:
                    header_str = header_bytes.decode('utf-8')
                    self.header_data = json.loads(header_str)
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    raise ValueError(f"头部JSON解析失败: {e}")
                
                # 3. 读取压缩数据
                compressed_start = stub_size + 8 + header_len
                compressed_end = file_size - 32  # 排除32字节hash
                compressed_size = compressed_end - compressed_start
                
                f.seek(compressed_start)
                self.compressed_data = f.read(compressed_size)
                
                # 4. 验证压缩数据哈希
                actual_hash = hashlib.sha256(self.compressed_data).hexdigest()
                if actual_hash != stored_hash:
                    if not self.silent:
                        print(f"警告: 压缩数据哈希不匹配")
                
                if not self.silent:
                    print(f"头部解析成功:")
                    print(f"- Stub大小: {stub_size/1024:.1f}KB")
                    print(f"- 头部大小: {header_len/1024:.1f}KB") 
                    print(f"- 压缩数据大小: {compressed_size/1024/1024:.1f}MB")
                
        except Exception as e:
            if not self.silent:
                print(f"解析安装器失败: {e}")
            raise
    
    def _determine_install_dir(self, custom_dir: Optional[str]) -> Path:
        """确定安装目录"""
        if custom_dir:
            return Path(custom_dir)
        
        # 使用配置中的默认路径
        if self.header_data and 'config' in self.header_data:
            config = self.header_data['config']
            if 'install' in config and 'default_path' in config['install']:
                default_path = config['install']['default_path']
                # 扩展环境变量
                expanded_path = os.path.expandvars(default_path)
                return Path(expanded_path)
        
        # 默认安装到当前目录的子文件夹
        return Path.cwd() / "installed_app"
    
    def _extract_files(self, install_dir: Path, silent: bool = False) -> None:
        """解压文件"""
        if not silent:
            print("正在解压文件...")
        
        if not self.compressed_data:
            raise Exception("没有压缩数据可解压")
        
        # 创建临时文件来处理压缩数据
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(self.compressed_data)
            temp_file_path = temp_file.name
        
        try:
            # 解压 ZIP 文件
            with zipfile.ZipFile(temp_file_path, 'r') as zip_file:
                zip_file.extractall(install_dir)
            
            if not silent:
                print(f"文件解压完成到: {install_dir}")
        finally:
            # 清理临时文件
            os.unlink(temp_file_path)
    
    def _run_install_scripts(self, install_dir: Path, silent: bool = False) -> None:
        """运行安装脚本"""
        if not self.header_data or 'config' not in self.header_data:
            return
        
        config = self.header_data['config']
        
        # 运行安装后脚本
        if 'install' in config and 'post_install_script' in config['install']:
            script_name = config['install']['post_install_script']
            script_path = install_dir / script_name
            
            if script_path.exists():
                if not silent:
                    print(f"运行安装脚本: {script_name}")
                try:
                    if script_path.suffix.lower() == '.bat':
                        subprocess.run([str(script_path)], cwd=install_dir, check=True)
                    elif script_path.suffix.lower() == '.ps1':
                        subprocess.run(['powershell', '-File', str(script_path)], cwd=install_dir, check=True)
                    else:
                        subprocess.run([str(script_path)], cwd=install_dir, check=True)
                    if not silent:
                        print("脚本执行完成")
                except subprocess.CalledProcessError as e:
                    if not silent:
                        print(f"脚本执行失败: {e}")

    def _run_gui_installation(self, custom_install_dir: Optional[str] = None) -> bool:
        """运行GUI安装模式"""
        if not GUI_AVAILABLE:
            return False
        
        try:
            # 解析安装器文件
            self._parse_installer()
            
            if not self.header_data:
                messagebox.showerror("错误", "无法解析安装器文件")
                return False
            
            # 获取应用名称和默认路径
            app_name = "应用程序"
            default_path = None
            
            if self.header_data and 'config' in self.header_data:
                config = self.header_data['config']
                
                # 获取应用名称
                if 'app' in config and 'name' in config['app']:
                    app_name = config['app']['name']
                
                # 获取默认安装路径
                if 'install' in config and 'default_path' in config['install']:
                    default_path = os.path.expandvars(config['install']['default_path'])
            
            # 如果有自定义路径，使用它
            if custom_install_dir:
                default_path = custom_install_dir
            
            # 创建GUI界面
            gui = SimpleInstallerGUI(app_name, default_path)
            
            # 设置安装回调
            def install_callback(install_path):
                try:
                    # 创建安装目录
                    install_dir = Path(install_path)
                    install_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 解压文件
                    gui.update_progress(0.2, "正在解压文件...")
                    self._extract_files(install_dir, silent=True)
                    
                    # 运行安装脚本
                    gui.update_progress(0.8, "正在配置...")
                    self._run_install_scripts(install_dir, silent=True)
                    
                    # 完成
                    gui.update_progress(1.0, "安装完成")
                    gui.show_success()
                    
                except Exception as e:
                    gui.show_error(str(e))
            
            gui.set_install_callback(install_callback)
            
            # 运行GUI
            result_path = gui.run()
            return result_path is not None
            
        except Exception as e:
            if GUI_AVAILABLE:
                messagebox.showerror("安装错误", f"安装过程中发生错误: {e}")
            return False


class SimpleInstallerGUI:
    """简化的安装器GUI界面"""
    
    def __init__(self, app_name: str = "应用程序", default_path: Optional[str] = None):
        self.app_name = app_name
        self.default_path = default_path or f"C:\\Program Files\\{app_name}"
        self.cancelled = False
        self.selected_path = None
        self.install_callback = None
        
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
        
        # 变量
        self.install_path = ctk.StringVar(value=self.default_path)
        self.state = "directory"  # directory, installing, completed
        
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
        
        # 内容区域
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
    
    def _show_completion(self, success: bool = True, message: str = ""):
        """显示完成界面"""
        self.state = "completed"
        
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
            message_text = f"{self.app_name} 已成功安装到:\n{self.install_path.get()}"
            message_label = ctk.CTkLabel(
                self.content_frame,
                text=message_text,
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
                text=message or "安装过程中发生错误",
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
        
        # 如果有安装回调，调用它
        if self.install_callback:
            import threading
            def install_thread():
                self.install_callback(path)
            
            thread = threading.Thread(target=install_thread)
            thread.daemon = True
            thread.start()
    
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
        self._show_completion(success=False, message=error_message)
    
    def show_success(self):
        """显示成功"""
        self._show_completion(success=True)
    
    def set_install_callback(self, callback):
        """设置安装回调函数"""
        self.install_callback = callback
    
    def run(self) -> Optional[str]:
        """运行GUI，返回选择的安装路径，如果取消则返回None"""
        self.root.mainloop()
        return None if self.cancelled else self.selected_path


def main() -> int:
    """主入口函数"""
    args = parse_arguments()
    
    try:
        # 获取当前可执行文件路径
        if getattr(sys, 'frozen', False):
            # PyInstaller 编译后的环境
            installer_path = Path(sys.executable)
        else:
            installer_path = Path(sys.argv[0])
        
        # 创建运行时实例
        runtime = InstallerRuntime(installer_path)
        
        # 检查是否应该使用GUI模式
        use_gui = False
        if not args.silent:
            # 先解析头部信息以获取配置
            try:
                runtime._parse_installer()
                if runtime.header_data and 'config' in runtime.header_data:
                    config = runtime.header_data['config']
                    if 'install' in config and config['install'].get('show_ui', False):
                        use_gui = True
            except Exception:
                # 如果解析失败，继续使用命令行模式
                pass
        
        # 运行安装
        success = runtime.run_installation(
            silent=args.silent,
            custom_install_dir=args.dir,
            use_gui=use_gui
        )
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("安装被用户中断")
        return 2
    except Exception as e:
        print(f"安装过程发生异常: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())