"""
Dialog windows for the Inspa GUI.
"""
import customtkinter as ctk
from .theme import Colors, Fonts, Style

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
        """设置UI（简化：左侧主色竖线 + 状态 pill + 中性进度条）"""
        container = ctk.CTkFrame(self, fg_color='transparent')
        container.pack(fill='both', expand=True)

        # 顶部标题行
        header = ctk.CTkFrame(container, fg_color='transparent')
        header.pack(fill='x', pady=(18, 6), padx=20)

        # 左侧主色竖线
        ctk.CTkFrame(header, width=4, fg_color=Colors.PRIMARY, corner_radius=2, height=38).pack(side='left', fill='y', padx=(0, 10))

        title_wrap = ctk.CTkFrame(header, fg_color='transparent')
        title_wrap.pack(side='left', fill='x', expand=True)
        title_label = ctk.CTkLabel(title_wrap, text="🏗️ 构建安装器", font=Fonts.H1, text_color=Colors.TEXT_PRIMARY)
        title_label.pack(anchor='w')

        # 状态 pill
        self.status_var = ctk.StringVar(value="准备中")
        self.state_pill = ctk.CTkLabel(
            header,
            textvariable=self.status_var,
            font=('', 13, 'bold'),
            text_color=Colors.TEXT_LIGHT,
            fg_color=Colors.PRIMARY,
            corner_radius=14,
            padx=14,
            pady=6
        )
        self.state_pill.pack(side='right')

        # 进度条（固定主色，不跟随状态变色）
        progress_wrap = ctk.CTkFrame(container, fg_color='transparent')
        progress_wrap.pack(fill='x', padx=32, pady=(4, 12))
        self.progress_bar = ctk.CTkProgressBar(progress_wrap, width=400, progress_color=Colors.PRIMARY, fg_color=Colors.SURFACE_LIGHT)
        self.progress_bar.pack(fill='x')
        self.progress_bar.set(0)

        # 日志区域
        self.log_frame = ctk.CTkFrame(container, fg_color=Colors.SURFACE_LIGHT, corner_radius=8)
        self.log_frame.pack(pady=4, padx=25, fill='both', expand=True)
        self.log_text = ctk.CTkTextbox(self.log_frame, width=420, height=120, fg_color=Colors.BACKGROUND, text_color=Colors.TEXT_PRIMARY, border_width=0, font=Fonts.MONO_SMALL)
        self.log_text.pack(pady=10, padx=10, fill='both', expand=True)

        # 按钮行
        btn_frame = ctk.CTkFrame(container, fg_color='transparent')
        btn_frame.pack(pady=10)
        self.cancel_btn = ctk.CTkButton(btn_frame, text="取消", width=100, command=self.cancel_build, **Style.BUTTON_DANGER)
        self.cancel_btn.pack(side='left', padx=10)
        self.close_btn = ctk.CTkButton(btn_frame, text="关闭", width=100, command=self.destroy, **Style.BUTTON_SECONDARY)
    
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
    
    # === 新增: 语义状态切换 ===
    def set_state(self, state: str):
        """状态 pill 语义更新 (running|success|error)"""
        try:
            if state == 'running':
                self.state_pill.configure(text="进行中", fg_color=Colors.PRIMARY, text_color=Colors.TEXT_LIGHT)
            elif state == 'success':
                self.state_pill.configure(text="成功", fg_color=Colors.SUCCESS, text_color=Colors.TEXT_LIGHT)
            elif state == 'error':
                self.state_pill.configure(text="失败", fg_color=Colors.ERROR, text_color=Colors.TEXT_LIGHT)
        except Exception:
            pass


class PostActionDialog(ctk.CTkToplevel):
    """后置脚本配置对话框"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("配置后置脚本")
        self.geometry("500x400")
        self.resizable(False, False)
        
        # 设置模态
        self.transient(parent)
        self.grab_set()
        
        self.action = None
        self.setup_ui()
        self.center_window()
    
    def center_window(self):
        """窗口居中"""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.winfo_screenheight() // 2) - (400 // 2)
        self.geometry(f"500x400+{x}+{y}")
    
    def setup_ui(self):
        """设置UI"""
        main_frame = ctk.CTkFrame(self, fg_color='transparent')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # 脚本类型
        type_label = ctk.CTkLabel(main_frame, text="脚本类型:", font=Fonts.BODY)
        type_label.pack(anchor='w', pady=(0, 5))
        
        self.script_type = ctk.CTkOptionMenu(
            main_frame,
            values=["powershell", "batch"],
            fg_color=Colors.BACKGROUND,
            button_color=Colors.PRIMARY
        )
        self.script_type.pack(fill='x', pady=(0, 10))
        
        # 命令
        cmd_label = ctk.CTkLabel(main_frame, text="命令或脚本路径:", font=Fonts.BODY)
        cmd_label.pack(anchor='w', pady=(0, 5))
        
        self.command = ctk.CTkEntry(main_frame, placeholder_text="输入命令或选择脚本文件", **Style.ENTRY)
        self.command.pack(fill='x', pady=(0, 10))
        
        # 按钮框架
        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(fill='x', pady=20)
        
        # 取消和确定按钮
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            width=100,
            command=self.cancel,
            **Style.BUTTON_SECONDARY
        )
        cancel_btn.pack(side='left', padx=20)
        
        ok_btn = ctk.CTkButton(
            btn_frame,
            text="确定",
            width=100,
            command=self.confirm,
            **Style.BUTTON_PRIMARY
        )
        ok_btn.pack(side='right', padx=20)
    
    def confirm(self):
        """确认配置"""
        if not self.command.get().strip():
            return
            
        self.action = {
            'type': self.script_type.get(),
            'command': self.command.get().strip(),
            'args': None,
            'hidden': True,
            'timeout_sec': 300,
            'show_in_ui': True,
            'run_if': 'always',
            'working_dir': None
        }
        self.destroy()
    
    def cancel(self):
        """取消配置"""
        self.action = None
        self.destroy()
    
    def get_action(self):
        """获取配置的脚本动作"""
        self.wait_window()
        return self.action
