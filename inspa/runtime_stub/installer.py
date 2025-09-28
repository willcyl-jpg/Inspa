"""Unified runtime installer module.

合并原 `core.py` 与 `gui.py`:
 - InstallerRuntime: 解析 / 解压 / 脚本执行 (原 core)
 - 可选 GUI: InstallerRuntimeGUI + run_gui_installation (原 gui)

对外公共 API:
    from inspa.runtime_stub import InstallerRuntime, run_gui_installation, GUI_AVAILABLE

兼容说明:
 - 原文件 core.py / gui.py 已被移除，此模块集中维护
 - `run_installation(use_gui=True)` 会自动尝试 GUI
 - 仍可单独调用 run_gui_installation(runtime)

"""
from __future__ import annotations

# pyright: reportAttributeAccessIssue=false, reportOptionalMemberAccess=false

from pathlib import Path
from typing import Any, Dict, Optional, Callable, List, TYPE_CHECKING, Iterable, Tuple
import os
import json
import struct
import sys
import io
import zipfile
import subprocess

FOOTER_MAGIC = b"INSPAF01"
FOOTER_SIZE = 8 + 8 + 8 + 8 + 8 + 32  # <8sQQQQ32s>

# 为可选 GUI 组件预声明 Any 类型，避免 mypy 在缺失依赖环境下的属性访问告警
ctk: Any  # type: ignore
messagebox: Any  # type: ignore
filedialog: Any  # type: ignore

# ----------------------------- GUI 可选依赖检测 -----------------------------
GUI_AVAILABLE = False
try:  # pragma: no cover
    import customtkinter as ctk  # type: ignore
    from tkinter import messagebox, filedialog  # type: ignore
    from PIL import Image  # type: ignore  # noqa: F401 (兼容保留)
    GUI_AVAILABLE = True
except Exception:  # pragma: no cover
    ctk = None  # type: ignore
    messagebox = None  # type: ignore
    filedialog = None  # type: ignore
    if TYPE_CHECKING:  # 占位类型
        import customtkinter as ctk  # type: ignore
        from PIL import Image  # type: ignore

# ----------------------------- 核心运行时 ----------------------------------
class InstallerRuntime:
    """核心安装运行时 (无 GUI 依赖)"""

    def __init__(self, installer_path: Path, silent: bool = False):
        self.installer_path = installer_path
        self.header_data: Optional[Dict[str, Any]] = None
        self.compressed_data: Optional[bytes] = None
        self.silent = silent
        self._parsed = False

    def run_installation(
        self,
        silent: bool = False,
        custom_install_dir: Optional[str] = None,
        use_gui: bool = False,
        gui_script_output: bool = True,  # 兼容旧签名占位
    ) -> bool:
        if use_gui and GUI_AVAILABLE:
            try:
                return run_gui_installation(self, custom_install_dir)
            except Exception:
                if not silent:
                    print("GUI 失败或不可用，降级为命令行模式")
        try:
            if not silent:
                print("开始安装流程\n正在解析安装器...")
            self._parse_installer()
            if not self.header_data:
                if not silent:
                    print("错误: 无法解析安装器头部")
                return False
            install_dir = self._determine_install_dir(custom_install_dir)
            if not silent:
                print(f"安装目录: {install_dir}")
            install_dir.mkdir(parents=True, exist_ok=True)
            self._extract_files(install_dir, silent)
            self._run_install_scripts(install_dir, silent)
            if not silent:
                print("安装完成！")
            return True
        except Exception as e:  # noqa: BLE001
            if not silent:
                print(f"安装失败: {e}")
            return False

    # 解析 ---------------------------------------------------------------
    def _parse_installer(self) -> None:
        if self._parsed:
            return
        try:
            header_offset = header_len = 0
            with open(self.installer_path, "rb") as f:
                f.seek(0, 2)
                file_size = f.tell()
                # 新 Footer
                if file_size >= FOOTER_SIZE:
                    try:
                        f.seek(file_size - FOOTER_SIZE)
                        footer = f.read(FOOTER_SIZE)
                        magic, header_offset, header_len, compressed_offset, compressed_size, _ = struct.unpack(
                            "<8sQQQQ32s", footer
                        )
                        if magic == FOOTER_MAGIC and header_offset + header_len <= file_size:
                            f.seek(header_offset)
                            if struct.unpack("<Q", f.read(8))[0] != header_len:
                                raise ValueError("头部长度字段不匹配")
                            header_bytes = f.read(header_len)
                            if len(header_bytes) != header_len:
                                raise ValueError("头部数据读取不完整")
                            self.header_data = json.loads(header_bytes.decode("utf-8"))
                            f.seek(compressed_offset)
                            self.compressed_data = f.read(compressed_size)
                            if not self.silent:
                                print("使用 Footer 快速解析成功")
                            self._parsed = True
                            return
                    except Exception:
                        pass  # 回退旧格式
                # 旧格式线性探测
                if file_size < 32:
                    raise ValueError("文件太小")
                f.seek(-32, 2); f.read(32)  # 忽略旧 hash
                found = False
                for stub_guess in range(100 * 1024, file_size - 1024, 1024):
                    f.seek(stub_guess)
                    raw_len = f.read(8)
                    if len(raw_len) != 8:
                        continue
                    cand_len = struct.unpack("<Q", raw_len)[0]
                    if 100 <= cand_len <= 100 * 1024:
                        compressed_size = file_size - 32 - stub_guess - 8 - cand_len
                        if compressed_size > 0:
                            header_offset = stub_guess
                            header_len = cand_len
                            found = True
                            break
                if not found:
                    raise ValueError("无法定位旧格式头部")
                f.seek(header_offset + 8)
                header_bytes = f.read(header_len)
                if len(header_bytes) != header_len:
                    raise ValueError("旧格式头部截断")
                self.header_data = json.loads(header_bytes.decode("utf-8"))
                comp_start = header_offset + 8 + header_len
                f.seek(comp_start)
                self.compressed_data = f.read(file_size - 32 - comp_start)
                if not self.silent:
                    print("旧格式解析成功")
                self._parsed = True
        except Exception as e:  # noqa: BLE001
            if not self.silent:
                print(f"解析安装器失败: {e}")
            raise

    # 安装目录 -----------------------------------------------------------
    def _determine_install_dir(self, custom_dir: Optional[str]) -> Path:
        if custom_dir:
            return Path(custom_dir)
        if self.header_data:
            install_cfg = None
            if "install" in self.header_data and isinstance(self.header_data.get("install"), dict):
                install_cfg = self.header_data["install"]
            elif "config" in self.header_data and isinstance(self.header_data.get("config"), dict):
                install_cfg = self.header_data["config"].get("install")
            if install_cfg and isinstance(install_cfg, dict):
                default_path = install_cfg.get("default_path")
                if default_path:
                    return Path(os.path.expandvars(default_path))
        return Path.cwd() / "installed_app"

    # 解压 ---------------------------------------------------------------
    def _extract_files(
        self,
        install_dir: Path,
        silent: bool = False,
        file_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        if not self.compressed_data:
            raise RuntimeError("没有压缩数据可解压")
        algo = "zip"
        if self.header_data:
            comp_block = self.header_data.get("compression", {}) or {}
            algo = comp_block.get("algo") or algo
            if algo == "zip" and "config" in self.header_data:  # 旧结构兼容
                algo = self.header_data["config"].get("compression", {}).get("algo", "zip")
        if not silent:
            print(f"正在解压文件... (算法: {algo})")
        if algo == "zstd":
            self._extract_zstd(install_dir, file_callback)
        else:
            self._extract_zip(install_dir, file_callback)
        if not silent:
            print(f"文件解压完成到: {install_dir}")

    def _extract_zstd(self, install_dir: Path, file_callback: Optional[Callable[[str], None]]) -> None:
        # compressed_data 在 _extract_files 之前已经检查，这里断言用于类型收窄
        assert self.compressed_data is not None, "compressed_data 未初始化"
        if "zstandard" not in sys.modules:
            try:
                import zstandard as zstd  # type: ignore
            except Exception as e:  # pragma: no cover
                raise RuntimeError(f"无法加载 zstandard 库: {e}")
        else:
            zstd = sys.modules["zstandard"]  # type: ignore
        dctx = zstd.ZstdDecompressor()
        reader = dctx.stream_reader(io.BytesIO(self.compressed_data))
        try:
            while True:
                header = reader.read(4)
                if not header or len(header) < 4:
                    break
                path_len = int.from_bytes(header, "little")
                if path_len <= 0 or path_len > 4096:
                    break
                path_bytes = reader.read(path_len)
                if len(path_bytes) != path_len:
                    break
                rel_path = path_bytes.decode("utf-8")
                if file_callback:
                    try:
                        file_callback(rel_path)
                    except Exception:
                        pass
                meta = reader.read(17)
                if len(meta) != 17:
                    break
                size, mtime, is_dir_flag = struct.unpack("<QQB", meta)
                target_path = install_dir / rel_path
                if is_dir_flag:
                    target_path.mkdir(parents=True, exist_ok=True)
                    continue
                target_path.parent.mkdir(parents=True, exist_ok=True)
                remaining = size
                with open(target_path, "wb") as out_f:
                    while remaining > 0:
                        chunk = reader.read(min(64 * 1024, remaining))
                        if not chunk:
                            break
                        out_f.write(chunk)
                        remaining -= len(chunk)
                try:
                    os.utime(target_path, (mtime, mtime))
                except Exception:
                    pass
        finally:
            try:
                reader.close()
            except Exception:
                pass

    def _extract_zip(self, install_dir: Path, file_callback: Optional[Callable[[str], None]]) -> None:
        assert self.compressed_data is not None, "compressed_data 未初始化"
        with zipfile.ZipFile(io.BytesIO(self.compressed_data), "r") as zf:
            for info in zf.infolist():
                zf.extract(info, install_dir)
                if not info.is_dir() and file_callback:
                    try:
                        file_callback(info.filename)
                    except Exception:
                        pass

    # 脚本执行 -----------------------------------------------------------
    def _run_install_scripts(self, install_dir: Path, silent: bool = False) -> None:
        if not self.header_data:
            return
        scripts: List[Dict[str, Any]] = []
        if "scripts" in self.header_data and isinstance(self.header_data["scripts"], list):
            scripts = self.header_data["scripts"]  # 新结构
        elif "config" in self.header_data:
            return  # 旧结构忽略
        if not scripts:
            return
        for script in scripts:
            try:
                cmd_type = script.get("type")
                command = script.get("command")
                if not command:
                    continue
                if not silent:
                    print(f"运行安装脚本: {command}")
                if cmd_type == "batch":
                    subprocess.run([command] + (script.get("args") or []), cwd=install_dir, check=True)
                elif cmd_type == "powershell":
                    subprocess.run(
                        [
                            "powershell",
                            "-NoLogo",
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            command,
                        ]
                        + (script.get("args") or []),
                        cwd=install_dir,
                        check=True,
                    )
                else:  # 直接执行
                    subprocess.run([command] + (script.get("args") or []), cwd=install_dir, check=True)
            except subprocess.CalledProcessError as e:  # noqa: PERF203
                if not silent:
                    print(f"脚本执行失败: {e}")

    # 简化脚本执行 (GUI 用) -----------------------------------------------
    def _run_scripts_simple(self, install_dir: Path) -> None:
        if not self.header_data:
            return
        scripts = self.header_data.get("scripts")
        if not isinstance(scripts, list):
            return
        for script in scripts:
            try:
                cmd_type = script.get("type")
                command = script.get("command")
                if not command:
                    continue
                args: List[str] = script.get("args") or []
                working_dir = script.get("working_dir")
                cwd = install_dir
                if working_dir:
                    wd = install_dir / working_dir
                    if wd.exists():
                        cwd = wd
                if cmd_type == "powershell":
                    if command.lower().endswith(".ps1") and (cwd / command).exists():
                        full = (cwd / command) if not Path(command).is_absolute() else Path(command)
                        run_cmd = [
                            "powershell",
                            "-NoLogo",
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(full),
                        ] + args
                    else:
                        run_cmd = [
                            "powershell",
                            "-NoLogo",
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-Command",
                            command,
                        ] + args
                elif cmd_type == "batch":
                    run_cmd = ["cmd.exe", "/c", command] + args
                else:
                    continue
                subprocess.run(run_cmd, cwd=str(cwd), timeout=int(script.get("timeout_sec", 300)))
            except Exception:  # noqa: BLE001
                continue

# ----------------------------- GUI 部分 ------------------------------------
class InstallerRuntimeGUI:  # 轻量 GUI
    def __init__(
        self,
        app_name: str = "应用程序",
        default_path: Optional[str] = None,
        required_space_mb: int = 200,
        license_text: Optional[str] = None,
        welcome_message: Optional[str] = None,
    ):
        if not GUI_AVAILABLE:
            raise ImportError("GUI依赖未安装，无法启动图形界面")
        self.app_name = app_name
        self.default_path = default_path or f"C:/Program Files/{app_name}"
        self.required_space_mb = required_space_mb
        self.license_text = license_text
        self.welcome_message = welcome_message or f"欢迎使用 {app_name} 安装程序。请确认安装路径并阅读许可协议。"
        self.cancelled = False
        self.install_path = self.default_path
        self.install_callback: Optional[Callable[[str], None]] = None
        # 同时兼容未导入 tkinter 时的类型：运行期赋值 BooleanVar, 这里标注 Optional[Any]
        self.agree_var: Optional[Any] = None  # noqa: ANN401 (GUI 动态类型)

        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        self.root = ctk.CTk()
        self.root.title(app_name)
        self.root.geometry("520x420")
        self.root.resizable(False, False)
        self._center_window()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()
        self._switch_state("ready")

    def _center_window(self) -> None:
        self.root.update_idletasks()
        w = self.root.winfo_width(); h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(self.root, height=70, corner_radius=0, fg_color=("gray90", "gray20"))
        header.grid(row=0, column=0, sticky="ew")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text=self.app_name, font=ctk.CTkFont(size=20, weight="bold")).pack(side="left", padx=20)
        self.footer = ctk.CTkFrame(self.root, height=70, corner_radius=0)
        self.footer.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.footer.grid_columnconfigure(0, weight=1)
        self.ready_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.installing_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.finished_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self._build_ready(); self._build_installing(); self._build_finished()

    def _build_ready(self) -> None:
        frame = self.ready_frame
        box = ctk.CTkFrame(frame, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=30, pady=20)
        if self.welcome_message:
            ctk.CTkLabel(box, text=self.welcome_message, justify="left", wraplength=440).pack(anchor="w", pady=(5, 10))
        if self.license_text:
            ctk.CTkLabel(box, text="许可协议：", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
            lic = ctk.CTkTextbox(box, height=120, wrap="word")
            lic.pack(fill="x", pady=(4, 4)); lic.insert("0.0", self.license_text); lic.configure(state="disabled")
            from tkinter import BooleanVar
            self.agree_var = BooleanVar(value=False)
            self.agree_cb = ctk.CTkCheckBox(box, text="我已阅读并同意许可协议", variable=self.agree_var, command=self._toggle_agree)
            self.agree_cb.pack(anchor="w", pady=(0, 8))
        from tkinter import StringVar
        path_row = ctk.CTkFrame(box, fg_color="transparent"); path_row.pack(fill="x", pady=(4, 4))
        ctk.CTkLabel(path_row, text="安装路径:").pack(side="left")
        self.path_var = StringVar(value=self.default_path)
        self.path_entry = ctk.CTkEntry(path_row, textvariable=self.path_var, width=320); self.path_entry.pack(side="left", padx=5)
        ctk.CTkButton(path_row, text="浏览", width=60, command=self._browse).pack(side="left")
        self.start_btn = ctk.CTkButton(box, text="开始安装", command=self._start_install); self.start_btn.pack(pady=(15, 0))
        if self.agree_var is not None:
            self.start_btn.configure(state="disabled")

    def _build_installing(self) -> None:
        frame = self.installing_frame
        box = ctk.CTkFrame(frame, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=30, pady=60)
        from tkinter import StringVar
        self.progress_var = StringVar(value="准备中...")
        self.progress_bar = ctk.CTkProgressBar(box, width=420); self.progress_bar.pack(pady=(0, 10)); self.progress_bar.set(0)
        ctk.CTkLabel(box, textvariable=self.progress_var).pack()

    def _build_finished(self) -> None:
        frame = self.finished_frame
        box = ctk.CTkFrame(frame, fg_color="transparent"); box.pack(fill="both", expand=True, padx=30, pady=60)
        self.finish_label = ctk.CTkLabel(box, text="安装完成", font=ctk.CTkFont(size=16, weight="bold")); self.finish_label.pack(pady=(0, 10))
        ctk.CTkButton(box, text="关闭", command=self._on_close).pack()

    def _toggle_agree(self) -> None:
        if self.agree_var is not None:
            self.start_btn.configure(state="normal" if self.agree_var.get() else "disabled")

    def _browse(self) -> None:
        if filedialog:
            d = filedialog.askdirectory(initialdir=self.path_var.get())
            if d:
                self.path_var.set(d)

    def _start_install(self) -> None:
        if self.agree_var is not None and not self.agree_var.get():
            if messagebox:
                messagebox.showwarning("提示", "请先同意许可协议")
            return
        self.install_path = self.path_var.get().strip()
        if not self.install_path:
            if messagebox:
                messagebox.showerror("错误", "安装路径不能为空")
            return
        self._switch_state("installing")
        cb = self.install_callback
        if cb is not None:
            import threading
            def _task():
                try:
                    cb(self.install_path)
                except Exception as e:  # pragma: no cover
                    if messagebox:
                        messagebox.showerror("错误", str(e))
            threading.Thread(target=_task, daemon=True).start()

    def update_progress(self, value: float, message: str) -> None:
        if hasattr(self, "progress_bar"):
            self.progress_bar.set(max(0.0, min(1.0, value)))
        if hasattr(self, "progress_var"):
            self.progress_var.set(message)
        self.root.update_idletasks()

    def show_success(self) -> None:
        self._switch_state("finished"); self.finish_label.configure(text="安装完成")

    def show_error(self, msg: str) -> None:
        self._switch_state("finished"); self.finish_label.configure(text=f"安装失败: {msg}")

    def set_install_callback(self, cb: Callable[[str], None]) -> None:
        self.install_callback = cb

    def run(self) -> bool:
        self.root.mainloop(); return not self.cancelled

    def _switch_state(self, state: str) -> None:
        for f in (self.ready_frame, self.installing_frame, self.finished_frame):
            f.grid_remove()
        mapping = {
            "ready": self.ready_frame,
            "installing": self.installing_frame,
            "finished": self.finished_frame,
        }
        frame = mapping.get(state, self.ready_frame)
        frame.grid(row=1, column=0, sticky="nsew")

    def _on_close(self) -> None:
        if hasattr(self, "progress_bar") and self.progress_bar.get() < 1.0:
            if messagebox and messagebox.askokcancel("确认", "安装尚未完成，确定要退出吗?"):
                self.cancelled = True; self.root.destroy(); return
            if self.progress_bar.get() < 1.0:
                return
        self.root.destroy()


def run_gui_installation(runtime: InstallerRuntime, custom_install_dir: Optional[str] = None) -> bool:
    if not GUI_AVAILABLE or InstallerRuntimeGUI is None:  # type: ignore[arg-type]
        return False

    def _read_license(license_path: Optional[str]) -> Optional[str]:
        if not license_path:
            return None
        p = Path(license_path)
        if not p.exists():
            return None
        for enc in ("utf-8", "gbk"):
            try:
                return p.read_text(encoding=enc)
            except Exception:
                continue
        return "无法读取许可文件"

    def _estimate_required_space(header: Dict[str, Any], compressed_len: int | None) -> int:
        total_size = 0
        files_meta = header.get("files")
        if isinstance(files_meta, list):
            for item in files_meta:
                if isinstance(item, dict) and "size" in item:
                    try:
                        total_size += int(item["size"])  # noqa: PLW2901
                    except Exception:
                        pass
        if total_size > 0:
            return max(1, int(total_size / (1024 * 1024)))
        if compressed_len:
            try:
                return max(1, int(compressed_len * 1.5 / (1024 * 1024)))
            except Exception:
                return 200
        return 200

    try:
        if not getattr(runtime, "_parsed", False):  # noqa: SLF001
            runtime._parse_installer()  # type: ignore[attr-defined]
        header: Dict[str, Any] = getattr(runtime, "header_data", {}) or {}  # type: ignore[attr-defined]
        if not header:
            return False
        product = header.get("product") if isinstance(header.get("product"), dict) else None
        config_block = header.get("config") if isinstance(header.get("config"), dict) else None
        app_name = (
            (product or {}).get("name")
            or (config_block or {}).get("app", {}).get("name")
            or "应用程序"
        )
        install_cfg = header.get("install") if isinstance(header.get("install"), dict) else None
        if not install_cfg and config_block:
            ic = config_block.get("install")
            if isinstance(ic, dict):
                install_cfg = ic
        default_path = install_cfg.get("default_path") if install_cfg else None
        license_file = install_cfg.get("license_file") if install_cfg else None
        if custom_install_dir:
            default_path = custom_install_dir
        license_text = _read_license(license_file)
        required_space_mb = _estimate_required_space(header, len(getattr(runtime, "compressed_data", b"")))  # type: ignore[attr-defined]
        gui = InstallerRuntimeGUI(
            app_name=app_name,
            default_path=default_path,
            required_space_mb=required_space_mb or 200,
            license_text=license_text,
            welcome_message=f"欢迎安装 {app_name}",
        )

        def install_callback(chosen_path: str) -> None:
            try:
                install_dir = Path(chosen_path)
                install_dir.mkdir(parents=True, exist_ok=True)
                gui.update_progress(0.05, "准备中...")
                total_files = 0
                processed_files = 0
                try:
                    hd_local: Dict[str, Any] = getattr(runtime, "header_data", {})  # type: ignore[attr-defined]
                    files_meta = hd_local.get("files")
                    if isinstance(files_meta, list):
                        total_files = sum(
                            1
                            for fmeta in files_meta
                            if isinstance(fmeta, dict)
                            and not fmeta.get("is_directory")
                        ) or 0
                except Exception:
                    total_files = 0

                def file_cb(rel_path: str):
                    nonlocal processed_files, total_files
                    if total_files <= 0:
                        return
                    processed_files += 1
                    base_start, base_end = 0.05, 0.80
                    span = base_end - base_start
                    ratio = min(1.0, processed_files / max(1, total_files))
                    gui.update_progress(base_start + span * ratio, f"解压 {processed_files}/{total_files}: {rel_path}")

                runtime._extract_files(install_dir, silent=True, file_callback=file_cb)  # type: ignore[attr-defined]
                if total_files == 0:
                    gui.update_progress(0.80, "文件解压完成")
                gui.update_progress(0.85, "执行脚本...")
                runtime._run_scripts_simple(install_dir)  # type: ignore[attr-defined]
                gui.update_progress(0.95, "脚本完成")
                gui.update_progress(1.0, "安装完成")
                gui.show_success()
            except Exception as e:  # pragma: no cover
                gui.show_error(str(e))

        gui.set_install_callback(install_callback)
        result = gui.run()
        return bool(result)
    except Exception:
        return False

__all__ = [
    "InstallerRuntime",
    "InstallerRuntimeGUI",
    "run_gui_installation",
    "GUI_AVAILABLE",
    "FOOTER_MAGIC",
    "FOOTER_SIZE",
]

if __name__ == "__main__":  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=str, default=None)
    ns = ap.parse_args()
    rt = InstallerRuntime(Path(sys.argv[0]))
    ok = run_gui_installation(rt, ns.dir)
    sys.exit(0 if ok else 2)
