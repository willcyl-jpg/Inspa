"""Compact, corrected runtime installer.
功能：GUI（单完成按钮）、解析 footer、解压（zip/zstd）、脚本执行、UAC 提升。
"""
from __future__ import annotations
import io, sys, os, struct, json, zipfile, subprocess, ctypes
from pathlib import Path
from typing import Any, Dict, Optional, Callable, List, Protocol, runtime_checkable, cast
# Predeclare dynamic GUI symbols as Any to satisfy static analyzers
ctk: Any
tk: Any
ttk: Any
messagebox: Any
filedialog: Any
FOOTER_MAGIC,FOOTER_SIZE = b"INSPAF01",72
try:
    import customtkinter as ctk
    from tkinter import messagebox, filedialog
    GUI_AVAILABLE = True
except Exception:
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog
        ctk = None
        GUI_AVAILABLE = True
    except Exception:
        from typing import cast, Any
        GUI_AVAILABLE = False
        ctk = cast(Any, object())
        tk = cast(Any, object())
        ttk = cast(Any, object())
        messagebox = cast(Any, object())
    filedialog = cast(Any, object())


if GUI_AVAILABLE and ctk:
    class InstallerRuntimeGUI:
        """多阶段现代化安装界面。

        步骤: 1 欢迎(路径+许可) → 2 解压 → 3 脚本 → 4 完成
        对外接口保持: set_install_callback / update_progress / show_success / show_error / run
        """
        _STEPNAMES = ["欢迎", "解压", "脚本", "完成"]
        def __init__(self, app_name: str = "应用程序", default_path: Optional[str] = None, license_text: Optional[str] = None, allow_user_path: bool = True, icon_path: Optional[str] = None):
            self.app_name = app_name
            self.default_path = default_path or f"C:/Program Files/{app_name}"
            self.allow_user_path = allow_user_path
            self.license_text = license_text
            self.icon_path = icon_path
            self.cancelled = False
            self.install_callback: Optional[Callable[[str], None]] = None
            self.agree_var: Optional[Any] = None
            self._current_view = 'welcome'
            self._step_labels: list[Any] = []
            self._log_buffer: list[str] = []
            # Sidebar layout tunables
            self._SIDEBAR_WIDTH = 168  # 调整宽度（原 190）
            self._SIDEBAR_OUTER_PADX = 10
            self._SIDEBAR_STEPS_INNER_PADX = 10
            self._SIDEBAR_STEP_LABEL_PADX = 2
            self._SIDEBAR_STEP_LABEL_WIDTH = None  # 可置为固定宽度以对齐数字
            ctk.set_appearance_mode("light")
            self.root = ctk.CTk()
            self.root.title(f"{app_name} 安装程序")
            self.root.geometry("900x600")
            self.root.minsize(880,560)
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            self._define_theme()
            self._build_layout()
            self._build_welcome_view()
            self._activate_step(0)

        # ---------- Theme & Layout ----------
        def _define_theme(self):
            self.colors = {
                'primary': '#1e73e8',
                'primary_hover': '#155fbd',
                'bg': '#f5f7fb',
                'panel': '#ffffff',
                'border': '#e0e6ef',
                'text': '#222',
                'subtext': '#56627a',
                'danger': '#d93025',
                'ok': '#1b9e4b'
            }
        def _color(self, key:str) -> str:
            return self.colors.get(key, '#000')
        def _build_shell_containers(self):
            self.root.configure(bg=self._color('bg'))
            self.sidebar = ctk.CTkFrame(self.root, fg_color=self._color('panel'), corner_radius=0, width=self._SIDEBAR_WIDTH)
            self.sidebar.pack(side='left', fill='y', padx=0, pady=0, anchor='nw')
            try:
                self.sidebar.pack_propagate(False)
            except Exception:
                pass
            self.main_container = ctk.CTkFrame(self.root, fg_color=self._color('bg'))
            self.main_container.pack(side='right', fill='both', expand=True)
            # 移除了标题栏后，直接让步骤区域靠近顶部，仅留少量间距
            # Steps list
            steps_frame = ctk.CTkFrame(self.sidebar, fg_color=self._color('panel'))
            # 更紧凑靠顶：缩小顶部留白 (原 6 -> 2)
            steps_frame.pack(fill='x', padx=4, pady=(2,8), anchor='w')
            self._step_labels.clear()
            for idx, name in enumerate(self._STEPNAMES):
                text_val = f"{idx+1}. {name}"
                lbl_kwargs: dict[str, Any] = {
                    'text': text_val,
                    'anchor': 'w',
                    'justify': 'left',
                    'font': ("Segoe UI", 13),
                    'text_color': self._color('subtext'),
                }
                # 仅当设置固定宽度时才传递，避免 None 触发底层类型转换错误
                if self._SIDEBAR_STEP_LABEL_WIDTH is not None:
                    lbl_kwargs['width'] = int(self._SIDEBAR_STEP_LABEL_WIDTH)
                lbl = ctk.CTkLabel(steps_frame, **lbl_kwargs)
                lbl.pack(anchor='w', pady=2, padx=(4,0))
                self._step_labels.append(lbl)
        def _build_layout(self):
            # Top bar (icon + subtitle) above split
            top_bar = ctk.CTkFrame(self.root, fg_color=self._color('panel'), corner_radius=0, height=70)
            top_bar.pack(fill='x', side='top')
            inner = ctk.CTkFrame(top_bar, fg_color=self._color('panel'))
            inner.pack(fill='both', expand=True, padx=18, pady=8)
            # icon
            if self.icon_path:
                try:
                    from PIL import Image
                    img = Image.open(self.icon_path).resize((48,48))
                    icon = ctk.CTkImage(light_image=img, size=(48,48))
                    ctk.CTkLabel(inner, image=icon, text='').pack(side='left', padx=(0,12))
                except Exception:
                    pass
            txt = ctk.CTkFrame(inner, fg_color=self._color('panel'))
            txt.pack(side='left', fill='x', expand=True)
            ctk.CTkLabel(txt, text=self.app_name, font=("Segoe UI", 20, 'bold'), text_color=self._color('primary')).pack(anchor='w')
            ctk.CTkLabel(txt, text='欢迎使用安装向导', font=("Segoe UI", 13), text_color=self._color('subtext')).pack(anchor='w')
            # containers
            self._build_shell_containers()
        # ---------- Step state ----------
        def _step_index_from_view(self) -> int:
            mapping = {'welcome':0,'progress':1,'scripts':2,'finish':3}
            return mapping.get(self._current_view,0)
        def _activate_step(self, idx:int):
            for i,lbl in enumerate(self._step_labels):
                if i==idx:
                    lbl.configure(text_color=self._color('primary'), font=("Segoe UI", 13, 'bold'))
                else:
                    lbl.configure(text_color=self._color('subtext'), font=("Segoe UI", 13))
        # ---------- Views ----------
        def _clear_main(self):
            for w in self.main_container.winfo_children(): w.destroy()
        def _build_welcome_view(self):
            self._current_view='welcome'; self._clear_main()
            wrap = ctk.CTkFrame(self.main_container, fg_color=self._color('panel'), corner_radius=14)
            wrap.pack(fill='both', expand=True, padx=22, pady=18)
            # Path + validation
            path_section = ctk.CTkFrame(wrap, fg_color=self._color('panel'))
            path_section.pack(fill='x', pady=(18,10), padx=20)
            ctk.CTkLabel(path_section, text='安装路径', font=("Segoe UI", 14, 'bold'), text_color=self._color('primary')).pack(anchor='w')
            self.path_var = ctk.StringVar(value=self.default_path)
            row = ctk.CTkFrame(path_section, fg_color=self._color('panel'))
            row.pack(fill='x', pady=(8,4))
            self._path_entry = ctk.CTkEntry(row, textvariable=self.path_var, fg_color=self._color('bg'), corner_radius=6)
            self._path_entry.pack(side='left', fill='x', expand=True, padx=(0,10))
            self._browse_btn = ctk.CTkButton(row, text='浏览', command=self._browse, fg_color=self._color('primary'), hover_color=self._color('primary_hover'), width=90)
            self._browse_btn.pack(side='left')
            if not self.allow_user_path:
                self._path_entry.configure(state='disabled'); self._browse_btn.configure(state='disabled')
            self._path_warn = ctk.CTkLabel(path_section, text='', text_color=self._color('danger'), font=("Segoe UI", 11))
            self._path_warn.pack(anchor='w')
            self.path_var.trace_add('write', lambda *_: self._validate_path())
            # License
            if self.license_text:
                lic_section = ctk.CTkFrame(wrap, fg_color=self._color('panel'))
                lic_section.pack(fill='both', expand=True, padx=20, pady=(4,8))
                ctk.CTkLabel(lic_section, text='许可协议', font=("Segoe UI", 14, 'bold'), text_color=self._color('primary')).pack(anchor='w')
                box = ctk.CTkTextbox(lic_section, height=180, fg_color=self._color('bg'), text_color=self._color('text'))
                box.pack(fill='both', expand=True, pady=(8,4))
                box.insert('0.0', self.license_text); box.configure(state='disabled')
                self.agree_var = ctk.BooleanVar(value=False)
                ctk.CTkCheckBox(lic_section, text='我已阅读并接受许可协议', variable=self.agree_var, command=self._update_start_state).pack(anchor='w', pady=(4,0))
            else:
                self.agree_var = None
            # Start button
            actions = ctk.CTkFrame(wrap, fg_color=self._color('panel'))
            actions.pack(fill='x', pady=(12,10), padx=20)
            self.start_btn = ctk.CTkButton(actions, text='开始安装', command=self._start_install, fg_color=self._color('primary'), hover_color=self._color('primary_hover'), height=40, font=("Segoe UI", 15, 'bold'))
            self.start_btn.pack(fill='x')
            self._update_start_state()
        def _build_progress_view(self):
            self._current_view='progress'; self._clear_main()
            wrap = ctk.CTkFrame(self.main_container, fg_color=self._color('panel'), corner_radius=14)
            wrap.pack(fill='both', expand=True, padx=22, pady=18)
            ctk.CTkLabel(wrap, text='正在安装', font=("Segoe UI", 18, 'bold'), text_color=self._color('primary')).pack(anchor='w', padx=20, pady=(16,4))
            self.progress = ctk.CTkProgressBar(wrap, height=10, progress_color=self._color('primary'), fg_color=self._color('bg'))
            self.progress.pack(fill='x', padx=20, pady=(6,10))
            self._pb_label = ctk.CTkLabel(wrap, text='', text_color=self._color('subtext'))
            self._pb_label.pack(anchor='w', padx=20)
            # Log area
            log_frame = ctk.CTkFrame(wrap, fg_color=self._color('panel'))
            log_frame.pack(fill='both', expand=True, padx=20, pady=(12,10))
            self.log = ctk.CTkTextbox(log_frame, fg_color=self._color('bg'), text_color=self._color('text'))
            self.log.pack(fill='both', expand=True)
            self.log.configure(state='disabled')
            # Cancel button
            btn_row = ctk.CTkFrame(wrap, fg_color=self._color('panel'))
            btn_row.pack(fill='x', padx=20, pady=(4,4))
            self.cancel_btn = ctk.CTkButton(btn_row, text='取消安装', command=self._on_cancel, fg_color=self._color('danger'), hover_color='#b21f1a')
            self.cancel_btn.pack(side='right')
            # Flush early buffered logs if any
            for line in self._log_buffer:
                self._append_log(line)
            self._log_buffer.clear()
        def _build_finish_view(self):
            self._current_view='finish'; self._clear_main()
            wrap = ctk.CTkFrame(self.main_container, fg_color=self._color('panel'), corner_radius=14)
            wrap.pack(fill='both', expand=True, padx=22, pady=18)
            ctk.CTkLabel(wrap, text='安装完成', font=("Segoe UI", 22, 'bold'), text_color=self._color('primary')).pack(pady=(70,10))
            ctk.CTkLabel(wrap, text='您可以现在关闭此安装程序。', font=("Segoe UI", 14), text_color=self._color('subtext')).pack(pady=(0,20))
            ctk.CTkButton(wrap, text='完成', command=self._on_close, fg_color=self._color('primary'), hover_color=self._color('primary_hover'), width=180, height=42).pack()

        # ---------- Validation & State ----------
        def _validate_path(self):
            if not self.allow_user_path:
                self._path_warn.configure(text='')
                return True
            p = self.path_var.get().strip()
            if not p:
                self._path_warn.configure(text='路径不能为空')
                return False
            invalid_chars = set('<>"|?*')
            if any(c in invalid_chars for c in p):
                self._path_warn.configure(text='包含非法字符')
                return False
            try:
                parent = Path(p).parent
                if not parent.exists():
                    self._path_warn.configure(text='上级目录不存在')
                    return False
                self._path_warn.configure(text='')
                return True
            except Exception:
                self._path_warn.configure(text='路径无效')
                return False
        def _update_start_state(self):
            ok = True
            if self.agree_var is not None and not self.agree_var.get():
                ok = False
            if not self._validate_path():
                ok = False
            if ok:
                self.start_btn.configure(state='normal')
            else:
                self.start_btn.configure(state='disabled')

        # ---------- External API & Actions ----------
        def _browse(self):
            if not self.allow_user_path: return
            d = filedialog.askdirectory(initialdir=self.path_var.get()) if filedialog else None
            if d: self.path_var.set(d)
        def set_install_callback(self, cb:Callable[[str],Any]): self.install_callback = cb
        def _start_install(self):
            if self.agree_var is not None and not self.agree_var.get():
                try: messagebox.showwarning('许可未同意','请先阅读并勾选“我已阅读并接受许可协议”以继续安装。')
                except Exception: pass
                return
            if not self.install_callback: return
            # 切换到进度界面
            self._build_progress_view(); self._activate_step(0)  # 初始：即将进入解压
            import threading
            chosen = self.path_var.get()
            cb = self.install_callback
            if cb is not None:
                threading.Thread(target=lambda: cb(chosen), daemon=True).start()
        def _on_close(self): self.root.destroy(); self.cancelled = True
        def run(self) -> bool: self.root.mainloop(); return not self.cancelled

        # ---------- Progress / Logging (public) ----------
        def update_progress(self, val:float, msg:str=''):
            # 根据阶段： <0.05 仍在准备; 0.05-0.80 解压; 0.80-0.98 脚本; >=0.98 完成
            step_idx = 0
            if val >= 0.05: step_idx = 1
            if val >= 0.80: step_idx = 2
            if val >= 0.98: step_idx = 3
            self._activate_step(step_idx)
            if self._current_view != 'progress' and step_idx < 3:
                # 若还未进入进度视图（例如后台直接调用），自动切换
                self._build_progress_view()
            try:
                if hasattr(self, 'progress'):
                    self.progress.set(max(0,min(1,val)))
                    if hasattr(self, '_pb_label'):
                        self._pb_label.configure(text=f"{int(val*100)}%")
            except Exception:
                pass
            if msg:
                self._append_log(msg)
        def _append_log(self, msg:str):
            # 线程安全追加
            if self._current_view != 'progress':
                self._log_buffer.append(msg)
                return
            def _do():
                try:
                    self.log.configure(state='normal'); self.log.insert('end', msg+'\n'); self.log.see('end'); self.log.configure(state='disabled')
                except Exception:
                    pass
            try:
                self.root.after(0, _do)
            except Exception:
                _do()
        def show_success(self):
            self._activate_step(3)
            self._build_finish_view()
        def show_error(self, msg:str):
            self._append_log('错误: '+msg)
            try: messagebox.showerror('错误', msg)
            except Exception: pass
        def show_cancelled(self):
            # 仅在进度或欢迎状态下调用；构建一个简单提示
            self._current_view='finish'; self._clear_main(); self._activate_step(3)
            wrap = ctk.CTkFrame(self.main_container, fg_color=self._color('panel'), corner_radius=14)
            wrap.pack(fill='both', expand=True, padx=22, pady=18)
            ctk.CTkLabel(wrap, text='已取消', font=("Segoe UI", 22, 'bold'), text_color=self._color('danger')).pack(pady=(70,10))
            ctk.CTkLabel(wrap, text='安装过程被用户取消，已删除所有已安装的文件。', font=("Segoe UI", 14), text_color=self._color('subtext'), wraplength=520, justify='center').pack(pady=(0,30))
            ctk.CTkButton(wrap, text='关闭', command=self._on_close, fg_color=self._color('primary'), hover_color=self._color('primary_hover'), width=180, height=42).pack()
        def _on_cancel(self):
            # GUI 只负责视觉反馈；实际取消由外部 runtime 轮询
            try:
                self.cancel_btn.configure(state='disabled', text='正在取消...')
            except Exception:
                pass
            # 记录日志
            self._append_log('收到取消请求，正在尝试停止...')
            # 标记 GUI 自身取消，以便 run() 返回 False
            self.cancelled = True
else:
    class _InstallerRuntimeGUIFallback:
        def __init__(self, *a, **k):
            raise ImportError('tkinter 不可用')
        def set_install_callback(self, *_a, **_k): ...  # pragma: no cover
        def update_progress(self, *_a, **_k): ...       # pragma: no cover
        def run(self): return False                     # pragma: no cover
    InstallerRuntimeGUI = _InstallerRuntimeGUIFallback  # type: ignore

@runtime_checkable
class _GUIProto(Protocol):
    def update_progress(self, val:float, msg:str): ...
    def _append_log(self, msg:str): ...
    def set_install_callback(self, cb:Callable[[str],None]): ...
    def run(self) -> bool: ...

def _read_license(path:Optional[str]) -> Optional[str]:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    for enc in ('utf-8', 'gbk'):
        try:
            return p.read_text(encoding=enc)
        except Exception:
            pass
    return None

def _read_license_from_install_dir(install_dir: Path, license_file: Optional[str]) -> Optional[str]:
    """从安装目录读取许可证文件
    
    Args:
        install_dir: 安装目录
        license_file: 许可证文件名（相对于安装目录）
        
    Returns:
        Optional[str]: 许可证内容，如果读取失败返回 None
    """
    if not license_file:
        return None
    
    # 如果是绝对路径，尝试直接读取（向后兼容）
    license_path = Path(license_file)
    if license_path.is_absolute():
        if license_path.exists():
            for enc in ('utf-8', 'gbk'):
                try:
                    return license_path.read_text(encoding=enc)
                except Exception:
                    pass
        return None
    
    # 相对路径：相对于安装目录
    full_path = install_dir / license_file
    if not full_path.exists():
        return None
        
    for enc in ('utf-8', 'gbk'):
        try:
            return full_path.read_text(encoding=enc)
        except Exception:
            pass
    return None

def _count_files(h:Dict[str,Any]) -> int:
    return sum(1 for f in h.get('files',[]) if isinstance(f, dict) and not f.get('is_directory', False))

def _estimate_space(h:Dict[str,Any], clen:int) -> int:
    total = sum(i.get('size',0) for i in h.get('files',[]) if isinstance(i, dict) and 'size' in i)
    if total>0: return max(1, total//(1024*1024))
    if clen: 
        import math
        return max(1, math.ceil(clen*1.5/(1024*1024)))
    return 200

class InstallerRuntime:
    def __init__(self, installer_path:Path, silent:bool=False):
        self.installer_path = installer_path
        self.header_data:Optional[Dict[str,Any]] = None
        self.compressed_data:Optional[bytes] = None
        self.silent = silent
        self._parsed = False
        self.cancel_requested = False
    def request_cancel(self):
        self.cancel_requested = True
    def _parse(self):
        if self._parsed: return
        with open(self.installer_path, 'rb') as f:
            f.seek(0,2); size = f.tell()
            if size < FOOTER_SIZE: raise ValueError('文件太小')
            f.seek(size-FOOTER_SIZE); footer = f.read(FOOTER_SIZE)
            magic, hoff, hlen, coff, csz, _ = struct.unpack('<8sQQQQ32s', footer)
            if magic != FOOTER_MAGIC: raise ValueError('无效 footer')
            f.seek(hoff)
            if struct.unpack('<Q', f.read(8))[0] != hlen: raise ValueError('头部长度不匹配')
            header = f.read(hlen); self.header_data = json.loads(header.decode('utf-8'))
            f.seek(coff); self.compressed_data = f.read(csz)
            self._parsed = True
    def _algo(self) -> str:
        if not self.header_data: return 'zip'
        return (self.header_data.get('compression') or {}).get('algo') or 'zip'
    def _extract_zip(self, install_dir:Path, cb:Optional[Callable[[str],None]]):
        assert self.compressed_data is not None
        with zipfile.ZipFile(io.BytesIO(self.compressed_data), 'r') as zf:
            # 预创建所有目录结构以提高性能
            dirs_created = set()
            for info in zf.infolist():
                if info.is_dir():
                    target_dir = install_dir / info.filename.rstrip('/')
                    if str(target_dir) not in dirs_created:
                        target_dir.mkdir(parents=True, exist_ok=True)
                        dirs_created.add(str(target_dir))
                else:
                    # 确保文件父目录存在
                    target_file = install_dir / info.filename
                    target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 解压文件，使用更大的缓冲区
            for info in zf.infolist():
                if self.cancel_requested: break
                if not info.is_dir():
                    target_path = install_dir / info.filename
                    with open(target_path, 'wb') as f:
                        with zf.open(info) as src:
                            while True:
                                if self.cancel_requested: break
                                chunk = src.read(256*1024)  # 256KB 缓冲区
                                if not chunk: break
                                f.write(chunk)
                    # 设置文件时间
                    try:
                        import time
                        mtime = time.mktime(info.date_time + (0, 0, -1))
                        os.utime(target_path, (mtime, mtime))
                    except: pass
                if not info.is_dir() and cb: cb(info.filename)
    def _extract_zstd(self, install_dir:Path, cb:Optional[Callable[[str],None]]):
        try: import zstandard as zstd
        except ImportError: raise RuntimeError('缺少 zstandard')
        assert self.compressed_data is not None
        dctx = zstd.ZstdDecompressor()
        
        # 第一遍：收集所有目录并预创建
        dirs_created = set()
        with dctx.stream_reader(io.BytesIO(self.compressed_data)) as r:
            while True:
                h = r.read(4)
                if not h: break
                plen = int.from_bytes(h, 'little')
                path = r.read(plen).decode('utf-8')
                meta = r.read(17)
                size, mtime, is_dir = struct.unpack('<QQB', meta)
                if is_dir:
                    target_dir = install_dir / path
                    if str(target_dir) not in dirs_created:
                        target_dir.mkdir(parents=True, exist_ok=True)
                        dirs_created.add(str(target_dir))
                else:
                    # 预创建文件父目录
                    target_file = install_dir / path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                # 跳过文件内容（如果不是目录）
                if not is_dir:
                    r.read(size)
        
        # 第二遍：解压文件，使用更大的缓冲区
        with dctx.stream_reader(io.BytesIO(self.compressed_data)) as r:
            while True:
                h = r.read(4)
                if not h: break
                plen = int.from_bytes(h, 'little')
                path = r.read(plen).decode('utf-8')
                if self.cancel_requested: break
                if cb: cb(path)
                meta = r.read(17)
                size, mtime, is_dir = struct.unpack('<QQB', meta)
                tgt = install_dir/Path(path)
                if is_dir: continue  # 目录已创建
                with open(tgt, 'wb') as out:
                    rem = size
                    while rem>0:
                        if self.cancel_requested: break
                        chunk = r.read(min(256*1024, rem))  # 增加到256KB缓冲区
                        if not chunk: break
                        out.write(chunk); rem -= len(chunk)
                try: os.utime(tgt, (mtime, mtime))
                except: pass
                if self.cancel_requested: break
    def _extract_zip_single_file(self, install_dir: Path, target_file: str):
        """只提取指定的单个文件"""
        assert self.compressed_data is not None
        with zipfile.ZipFile(io.BytesIO(self.compressed_data), 'r') as zf:
            for info in zf.infolist():
                if info.filename == target_file and not info.is_dir():
                    target_path = install_dir / info.filename
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(target_path, 'wb') as f:
                        with zf.open(info) as src:
                            while True:
                                chunk = src.read(256*1024)  # 256KB 缓冲区
                                if not chunk: break
                                f.write(chunk)
                    # 设置文件时间
                    try:
                        import time
                        mtime = time.mktime(info.date_time + (0, 0, -1))
                        os.utime(target_path, (mtime, mtime))
                    except: pass
                    break
    
    def _extract_zstd_single_file(self, install_dir: Path, target_file: str):
        """只提取指定的单个 Zstd 文件"""
        try: import zstandard as zstd
        except ImportError: raise RuntimeError('缺少 zstandard')
        assert self.compressed_data is not None
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(io.BytesIO(self.compressed_data)) as r:
            while True:
                h = r.read(4)
                if not h: break
                plen = int.from_bytes(h, 'little')
                path = r.read(plen).decode('utf-8')
                if path == target_file:
                    # 找到了目标文件，提取它
                    meta = r.read(17)
                    size, mtime, is_dir = struct.unpack('<QQB', meta)
                    if not is_dir:
                        tgt = install_dir / Path(path)
                        tgt.parent.mkdir(parents=True, exist_ok=True)
                        with open(tgt, 'wb') as out:
                            rem = size
                            while rem > 0:
                                chunk = r.read(min(256*1024, rem))  # 增加到256KB缓冲区
                                if not chunk: break
                                out.write(chunk)
                                rem -= len(chunk)
                        try: os.utime(tgt, (mtime, mtime))
                        except: pass
                    break
                else:
                    # 跳过这个文件
                    meta = r.read(17)
                    size, mtime, is_dir = struct.unpack('<QQB', meta)
                    if not is_dir:
                        r.read(size)  # 跳过文件内容
    
    def extract(self, install_dir:Path, cb:Optional[Callable[[str],None]]=None):
        if not self.compressed_data: raise RuntimeError('无压缩数据')
        if self._algo() == 'zstd': self._extract_zstd(install_dir, cb)
        else: self._extract_zip(install_dir, cb)
    def _get_scripts(self) -> List[Dict[str,Any]]:
        return self.header_data.get('scripts', []) if self.header_data else []
    def _run_scripts(self, install_dir:Path, cb:Optional[Callable[[str],None]]=None):
        scripts = self._get_scripts(); si = None
        if os.name == 'nt': si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = subprocess.SW_HIDE
        for s in scripts:
            if self.cancel_requested:
                if cb: cb('已取消：跳过后续脚本')
                break
            cmd = s.get('command')
            if not cmd: continue
            args = s.get('args') or []
            try:
                p = subprocess.Popen([cmd]+args, cwd=str(install_dir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', startupinfo=si)
                if p.stdout and cb:
                    for line in iter(p.stdout.readline, ''):
                        if self.cancel_requested:
                            try: p.terminate()
                            except Exception: pass
                            if cb: cb('脚本执行已终止')
                            break
                        cb(line.rstrip('\n'))
                p.wait(timeout=int(s.get('timeout_sec', 300)))
            except Exception as e:
                if cb: cb(f'SCRIPT ERROR: {e}')
    def run_install(self, install_dir:Optional[str|Path]=None, gui:Optional[Any]=None, allow_user_path:Optional[bool]=None) -> bool:
        try:
            self._parse()
            if not self.header_data: return False
            # Determine install dir: priority: header.default_path > provided install_dir (if allowed) > fallback installed_app
            header_install = (self.header_data or {}).get('install') or {}
            header_default = header_install.get('default_path')
            header_allow = header_install.get('allow_user_path') if 'allow_user_path' in header_install else None
            if header_default:
                install_dir = Path(header_default)
            else:
                if install_dir and (allow_user_path is not False):
                    install_dir = Path(install_dir)
                else:
                    install_dir = Path.cwd()/"installed_app"
            install_dir.mkdir(parents=True, exist_ok=True)
            total = _count_files(self.header_data)
            done = 0
            def cb(pth:str):
                nonlocal done
                done += 1
                if gui: gui.update_progress(0.05+0.75*(done/total if total else 1), f'解压 {done}/{total}: {pth}')
            self.extract(install_dir, cb)
            if self.cancel_requested:
                # 强行删除已安装的文件
                if gui: gui._append_log('正在删除已安装的文件...')
                try:
                    import shutil
                    shutil.rmtree(install_dir, ignore_errors=True)
                    if gui: gui._append_log('已删除安装目录')
                except Exception as e:
                    if gui: gui._append_log(f'删除文件时出错: {e}')
                if gui: gui.show_cancelled()
                return False
            if gui: gui.update_progress(0.85, '运行脚本')
            self._run_scripts(install_dir, lambda t: gui._append_log(t) if gui else None)
            if self.cancel_requested:
                # 强行删除已安装的文件
                if gui: gui._append_log('正在删除已安装的文件...')
                try:
                    import shutil
                    shutil.rmtree(install_dir, ignore_errors=True)
                    if gui: gui._append_log('已删除安装目录')
                except Exception as e:
                    if gui: gui._append_log(f'删除文件时出错: {e}')
                if gui: gui.show_cancelled()
                return False
            if gui: gui.update_progress(1.0, '完成'); gui.show_success()
            return True
        except Exception as e:
            if gui: gui.show_error(str(e))
            return False

if __name__ == '__main__':
    is_admin = lambda: ctypes.windll.shell32.IsUserAnAdmin() != 0 if os.name == 'nt' else True
    def _elevate_and_exec(path: str, params: str, cwd: str) -> bool:
        """Use ShellExecuteExW to elevate and run a process. Returns True if launched."""
        try:
            # Windows-only: prepare SHELLEXECUTEINFO structure
            SEE_MASK_NOCLOSEPROCESS = 0x00000040
            SW_SHOWNORMAL = 1
            from ctypes import wintypes
            class SHELLEXECUTEINFOW(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("fMask", wintypes.ULONG),
                    ("hwnd", wintypes.HWND),
                    ("lpVerb", wintypes.LPCWSTR),
                    ("lpFile", wintypes.LPCWSTR),
                    ("lpParameters", wintypes.LPCWSTR),
                    ("lpDirectory", wintypes.LPCWSTR),
                    ("nShow", ctypes.c_int),
                    ("hInstApp", wintypes.HINSTANCE),
                    ("lpIDList", ctypes.c_void_p),
                    ("lpClass", wintypes.LPCWSTR),
                    ("hkeyClass", wintypes.HKEY),
                    ("dwHotKey", wintypes.DWORD),
                    ("hIcon", wintypes.HANDLE),
                    ("hProcess", wintypes.HANDLE),
                ]
            sei = SHELLEXECUTEINFOW()
            sei.cbSize = ctypes.sizeof(sei)
            sei.fMask = SEE_MASK_NOCLOSEPROCESS
            sei.hwnd = None
            sei.lpVerb = 'runas'
            sei.lpFile = path
            sei.lpParameters = params
            sei.lpDirectory = cwd
            sei.nShow = SW_SHOWNORMAL
            # Call ShellExecuteExW
            ok = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei))
            if not ok:
                return False
            # Optionally wait a short time for the child process to be created
            try:
                # Wait 200ms for the child to start; do not block excessively
                ctypes.windll.kernel32.WaitForSingleObject(sei.hProcess, 200)
            except Exception:
                pass
            return True
        except Exception:
            return False

    # Instantiate runtime early to inspect header and check whether admin is required
    from pathlib import Path
    rt = InstallerRuntime(Path(sys.argv[0]))
    try:
        rt._parse()
    except Exception:
        # ignore parse errors here; we'll handle later
        pass
    header_install = (rt.header_data or {}).get('install', {}) if rt.header_data else {}
    require_admin = header_install.get('require_admin') if 'require_admin' in header_install else True
    if os.name == 'nt' and require_admin and not is_admin():
        argv0 = Path(sys.argv[0])
        if argv0.suffix.lower() == '.exe' and argv0.exists():
            exe_to_run = str(argv0)
            params = ' '.join(['"' + a + '"' if ' ' in a else a for a in sys.argv[1:]])
        else:
            exe_to_run = sys.executable
            params = '"' + str(argv0) + '"' + ((' ' + ' '.join(['"' + a + '"' if ' ' in a else a for a in sys.argv[1:]])) if len(sys.argv) > 1 else '')
        cwd = os.getcwd()
        launched = _elevate_and_exec(exe_to_run, params, cwd)
        if launched:
            # elevated child started, exit parent
            sys.exit(0)
        else:
            # User declined elevation or elevation failed; if admin is required we must not continue
            try:
                # print to stderr; GUI not yet shown
                print('需要管理员权限，用户拒绝或提升失败，安装已取消。', file=sys.stderr)
            except Exception:
                pass
            sys.exit(2)
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--dir', type=str, default=None); p.add_argument('--cli', action='store_true')
    a = p.parse_args(); rt = InstallerRuntime(Path(sys.argv[0])); ok = False
    # 检查是否强制使用 CLI 模式
    force_cli = a.cli
    if not force_cli and GUI_AVAILABLE:
        try:
            rt._parse()
        except:
            pass
        header_install = (rt.header_data or {}).get('install', {}) if rt.header_data else {}
        license_file = header_install.get('license_file')
        allow_user = header_install.get('allow_user_path') if 'allow_user_path' in header_install else True
        
        # 读取许可证内容
        lic = None
        if license_file:
            # 首先尝试从header中获取嵌入的license内容
            header_install = (rt.header_data or {}).get('install', {})
            lic = header_install.get('license_content')
            
            if not lic:
                # 如果header中没有嵌入的内容，则尝试从压缩数据中提取
                license_path = Path(license_file)
                if not license_path.is_absolute():
                    # 临时解压许可证文件
                    import tempfile
                    import shutil
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir)
                        try:
                            # 只解压许可证文件
                            if rt._algo() == 'zstd':
                                rt._extract_zstd_single_file(temp_path, license_file)
                            else:
                                rt._extract_zip_single_file(temp_path, license_file)
                            lic = _read_license_from_install_dir(temp_path, license_file)
                        except Exception as e:
                            print(f"读取许可证文件失败: {e}", file=sys.stderr)
                else:
                    # 绝对路径，直接读取（向后兼容）
                    lic = _read_license(str(license_path))
        # Ensure header default_path is offered to GUI (and will be enforced by run_install)
        header_default = header_install.get('default_path')
        gui_default = header_default or (a.dir if a.dir else None)
        icon_path = header_install.get('icon_path')
        gui = InstallerRuntimeGUI(
            app_name=(rt.header_data or {}).get('product', {}).get('name') if rt.header_data else '应用程序',
            default_path=gui_default,
            license_text=lic,
            allow_user_path=bool(allow_user),
            icon_path=icon_path,
        )
        # Callback should respect header allow_user_path
        gui.set_install_callback(lambda d: rt.run_install(d, gui, allow_user_path=bool(allow_user)))
        # 将 GUI 的取消意图传递给 runtime（通过轮询标志实现软中断）
        def _poll_cancel():
            # 若 GUI 标记了 cancelled 且 runtime 未设置取消，则发出 request_cancel
            try:
                if gui.cancelled and not rt.cancel_requested:
                    rt.request_cancel()
                if not gui.cancelled and not rt.cancel_requested:
                    # 继续轮询直到安装完成或设置 cancelled
                    gui.root.after(300, _poll_cancel)
            except Exception:
                pass
        try:
            gui.root.after(300, _poll_cancel)
        except Exception:
            pass
        ok = gui.run()
    if not ok:
        ok = rt.run_install(a.dir, None)
    sys.exit(0 if ok else 2)