"""
安装器运行时

负责实际的安装逻辑，包括头部解析、文件解压、脚本执行等。
这是一个自包含的模块，旨在通过 PyInstaller 编译成独立的可执行文件。
因此，它不能有任何对 `inspa` 项目其他部分的相对导入。
"""

import io
import json
import os
import shutil
import struct
import subprocess
import tempfile
import time
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, BinaryIO, Protocol

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

# --- 运行时特定的定义 ---
# 这些定义与构建器中的组件相匹配，但为了独立性而在此处复制。

# 1. 日志和路径辅助函数
class LogStage(Enum):
    PARSE = "parse"
    VALIDATE = "validate"
    EXTRACT = "extract"
    SCRIPT = "script"
    ENV = "env"
    COMPLETE = "complete"

def get_stage_logger(stage: LogStage):
    import logging
    return logging.getLogger(f"inspa.runtime.{stage.value}")

def expand_path(path_str: str) -> Path:
    return Path(os.path.expandvars(path_str))

def ensure_directory(path: Path):
    path.mkdir(parents=True, exist_ok=True)

# 2. 数据结构和常量
FOOTER_MAGIC = b'INSPAF01'
FOOTER_SIZE = 72  # struct.calcsize('<8sQQQQ32s')

class CompressionAlgorithm(str, Enum):
    ZSTD = "zstd"
    ZIP = "zip"

@dataclass
class FileInfo:
    path: Path
    relative_path: Path
    size: int
    mtime: float
    is_directory: bool

# 3. 异常类
class InstallationError(Exception):
    """安装过程中的一般错误"""
    pass

class DecompressionError(Exception):
    """解压失败时的特定错误"""
    pass

# 4. 压缩器组件
class ProgressCallback(Protocol):
    def __call__(self, current: int, total: int, current_file: Optional[str] = None) -> None: ...

class Decompressor(ABC):
    @abstractmethod
    def decompress_to_directory(
        self, input_stream: BinaryIO, output_dir: Path, progress_callback: Optional[ProgressCallback] = None
    ) -> int: ...

class ZstdDecompressor(Decompressor):
    def __init__(self):
        if not ZSTD_AVAILABLE:
            raise DecompressionError("zstandard 库未安装，无法解压 Zstd 数据")
        self._dctx = zstd.ZstdDecompressor()

    def decompress_to_directory(self, input_stream: BinaryIO, output_dir: Path, progress_callback: Optional[ProgressCallback] = None) -> int:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            decompressed_bytes = 0
            with self._dctx.stream_reader(input_stream) as reader:
                while True:
                    file_info = self._read_file_header(reader)
                    if not file_info: break
                    
                    if file_info.is_directory:
                        (output_dir / file_info.relative_path).mkdir(parents=True, exist_ok=True)
                    else:
                        file_path = output_dir / file_info.relative_path
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(file_path, 'wb') as f:
                            remaining = file_info.size
                            while remaining > 0:
                                chunk = reader.read(min(64 * 1024, remaining))
                                if not chunk: break
                                f.write(chunk)
                                remaining -= len(chunk)
                        os.utime(file_path, (file_info.mtime, file_info.mtime))
                    decompressed_bytes += file_info.size
            return decompressed_bytes
        except Exception as e:
            raise DecompressionError(f"Zstd 解压失败: {e}") from e

    def _read_file_header(self, reader: BinaryIO) -> Optional[FileInfo]:
        try:
            path_len_bytes = reader.read(4)
            if not path_len_bytes: return None
            path_len = int.from_bytes(path_len_bytes, 'little')
            path_bytes = reader.read(path_len)
            path = path_bytes.decode('utf-8')
            meta_bytes = reader.read(17) # 8 (size) + 8 (mtime) + 1 (is_dir)
            size, mtime, is_dir_flag = struct.unpack('<QQB', meta_bytes)
            return FileInfo(Path(path), Path(path), size, float(mtime), is_dir_flag != 0)
        except (struct.error, UnicodeDecodeError):
            return None

class ZipDecompressor(Decompressor):
    def decompress_to_directory(self, input_stream: BinaryIO, output_dir: Path, progress_callback: Optional[ProgressCallback] = None) -> int:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            decompressed_bytes = 0
            with zipfile.ZipFile(input_stream, 'r') as zf:
                for info in zf.infolist():
                    if '..' in info.filename or info.filename.startswith('/'): continue
                    extract_path = output_dir / info.filename
                    if info.is_dir():
                        extract_path.mkdir(parents=True, exist_ok=True)
                    else:
                        extract_path.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(info) as src, open(extract_path, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                        decompressed_bytes += info.file_size
            return decompressed_bytes
        except Exception as e:
            raise DecompressionError(f"Zip 解压失败: {e}") from e

class DecompressorFactory:
    @staticmethod
    def create_decompressor(algorithm: CompressionAlgorithm) -> Decompressor:
        if algorithm == CompressionAlgorithm.ZSTD:
            return ZstdDecompressor()
        elif algorithm == CompressionAlgorithm.ZIP:
            return ZipDecompressor()
        else:
            raise DecompressionError(f"不支持的解压算法: {algorithm}")

# --- 核心安装器运行时类 ---

class InstallerRuntime:
    def __init__(self, installer_path: Path):
        self.installer_path = installer_path
        self.logger = get_stage_logger(LogStage.PARSE)
        self.header_data: Optional[Dict[str, Any]] = None
        self.compressed_data: Optional[bytes] = None
        self.install_dir: Optional[Path] = None
        self.temp_dir: Optional[Path] = None

    def run_installation(self, silent: bool = False, custom_install_dir: Optional[str] = None) -> bool:
        try:
            self.logger.info(f"开始安装流程 (静默: {silent})")
            if not self._parse_installer(): return False
            if not self._determine_install_path(custom_install_dir, silent): return False
            if not self._create_temp_directory(): return False
            if not self._extract_files(): return False
            if not self._execute_scripts(): return False
            if not self._setup_environment(): return False
            self._finalize_installation()
            self.logger.info(f"安装完成: {self.install_dir}")
            return True
        except Exception as e:
            self.logger.exception(f"安装过程发生未处理的异常: {e}")
            return False
        finally:
            self._cleanup()

    def _parse_installer(self) -> bool:
        self.logger.info(f"解析安装器文件: {self.installer_path}")
        try:
            with open(self.installer_path, 'rb') as f:
                f.seek(0, io.SEEK_END)
                if f.tell() < FOOTER_SIZE: raise InstallationError("文件太小")
                f.seek(f.tell() - FOOTER_SIZE)
                magic, h_off, h_len, c_off, c_size, _ = struct.unpack('<8sQQQQ32s', f.read(FOOTER_SIZE))
                if magic != FOOTER_MAGIC: raise InstallationError("无效的 Magic")
                f.seek(h_off)
                if struct.unpack('<Q', f.read(8))[0] != h_len: raise InstallationError("头部长度不匹配")
                self.header_data = json.loads(f.read(h_len).decode('utf-8'))
                f.seek(c_off)
                self.compressed_data = f.read(c_size)
                self.logger.info("安装器解析完成")
                return True
        except (IOError, struct.error, json.JSONDecodeError, InstallationError) as e:
            self.logger.error(f"解析安装器失败: {e}")
            return False

    def _determine_install_path(self, custom_path: Optional[str], silent: bool) -> bool:
        logger = get_stage_logger(LogStage.VALIDATE)
        if not self.header_data: return False
        if custom_path:
            self.install_dir = Path(custom_path)
            logger.info(f"使用用户指定路径: {self.install_dir}")
        else:
            default_path = self.header_data.get("install", {}).get("default_path", "C:/Temp/InspaInstall")
            self.install_dir = expand_path(default_path)
            logger.info(f"使用默认安装路径: {self.install_dir}")
        try:
            ensure_directory(self.install_dir)
            return True
        except Exception as e:
            logger.error(f"无法创建安装目录 {self.install_dir}: {e}")
            return False

    def _create_temp_directory(self) -> bool:
        try:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="inspa_"))
            self.logger.info(f"创建临时目录: {self.temp_dir}")
            return True
        except Exception as e:
            self.logger.error(f"创建临时目录失败: {e}")
            return False

    def _extract_files(self) -> bool:
        logger = get_stage_logger(LogStage.EXTRACT)
        logger.info("开始解压文件")
        if not all([self.header_data, self.compressed_data, self.temp_dir]): return False
        try:
            algo_str = self.header_data.get("compression", {}).get("algo", "zip")
            decompressor = DecompressorFactory.create_decompressor(CompressionAlgorithm(algo_str))
            decompressor.decompress_to_directory(io.BytesIO(self.compressed_data), self.temp_dir)
            logger.info(f"文件解压完成到: {self.temp_dir}")
            return True
        except (DecompressionError, ValueError) as e:
            logger.error(f"文件解压失败: {e}")
            return False

    def _execute_scripts(self) -> bool:
        logger = get_stage_logger(LogStage.SCRIPT)
        if not self.header_data: return False
        scripts = self.header_data.get("scripts", [])
        if not scripts:
            logger.info("无需执行脚本")
            return True
        logger.info(f"开始执行 {len(scripts)} 个脚本")
        for script in scripts:
            try:
                if not self._execute_single_script(script):
                    logger.warning(f"脚本执行失败但继续: {script.get('command')}")
            except Exception as e:
                logger.error(f"脚本执行异常: {e}")
        logger.info("脚本执行完成")
        return True

    def _execute_single_script(self, script: Dict[str, Any]) -> bool:
        script_type = script.get("type", "")
        command = script.get("command")
        if not command:
            self.logger.warning("脚本命令为空")
            return False

        working_dir = script.get("working_dir")
        cwd = self.install_dir
        if working_dir and cwd:
            # 相对目录支持
            proposed = cwd / working_dir
            if proposed.exists():
                cwd = proposed
            else:
                self.logger.warning(f"工作目录不存在: {proposed}，使用安装根目录")

        cmd: list[str] | None = None
        command_path: str = ""
        try:
            if script_type == "powershell":
                # 判断是文件还是内联命令：存在且以 .ps1 结尾则视为文件；否则改用 -Command
                is_file = False
                if command.lower().endswith('.ps1'):
                    possible = (cwd / command) if not Path(command).is_absolute() else Path(command)
                    if possible.exists():
                        is_file = True
                        command_path = str(possible)
                    else:
                        # 仍允许按内联处理
                        pass
                if is_file:
                    cmd = ["powershell", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", command_path]
                else:
                    # 内联命令
                    cmd = ["powershell", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
            elif script_type == "batch":
                # 直接交给 cmd /c，支持 echo / 调用 .bat / .cmd
                cmd = ["cmd.exe", "/c", command]
            else:
                self.logger.warning(f"不支持的脚本类型: {script_type}")
                return False

            kwargs: Dict[str, Any] = {
                'cwd': cwd,
                'timeout': script.get("timeout_sec", 300),
                'capture_output': True,
                'text': True
            }
            if script.get("hidden", True) and os.name == 'nt':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

            if cmd is None:
                self.logger.error("内部错误：命令未生成")
                return False
            result = subprocess.run(cmd, **kwargs)
            if result.returncode == 0:
                if script.get("show_in_ui", True):
                    out_preview = (result.stdout or '').strip().splitlines()[-1:] if result.stdout else []
                    if out_preview:
                        self.logger.info(f"脚本输出尾行: {out_preview[0]}")
                self.logger.info(f"脚本执行成功: {cmd}")
                return True
            else:
                self.logger.error(
                    f"脚本执行失败 (代码: {result.returncode})\n命令: {cmd}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
                )
                return False
        except FileNotFoundError as e:
            self.logger.error(f"脚本执行失败，命令或解释器不存在: {e}")
            return False
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"脚本执行超时: {cmd} (timeout={e.timeout}s)")
            return False
        except Exception as e:
            self.logger.error(f"脚本执行异常: {cmd}, 错误: {e}")
            return False

    def _setup_environment(self) -> bool:
        # 占位符：环境变量设置逻辑
        self.logger.info("跳过环境变量设置 (未实现)")
        return True

    def _finalize_installation(self) -> None:
        logger = get_stage_logger(LogStage.COMPLETE)
        logger.info("完成安装，移动文件...")
        if self.temp_dir and self.install_dir:
            try:
                # shutil.copytree 在 Python < 3.8 不支持 dirs_exist_ok
                # 使用更兼容的方式
                for src_dir, dirs, files in os.walk(self.temp_dir):
                    dst_dir = str(src_dir).replace(str(self.temp_dir), str(self.install_dir), 1)
                    if not os.path.exists(dst_dir):
                        os.makedirs(dst_dir)
                    for file_ in files:
                        src_file = os.path.join(src_dir, file_)
                        dst_file = os.path.join(dst_dir, file_)
                        if os.path.exists(dst_file):
                            os.remove(dst_file)
                        shutil.move(src_file, dst_dir)

                logger.info(f"文件已移动到: {self.install_dir}")
            except (IOError, shutil.Error) as e:
                logger.error(f"文件移动失败: {e}")
                raise InstallationError(f"无法将文件移动到最终位置: {e}") from e

    def _cleanup(self) -> None:
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"临时目录已清理: {self.temp_dir}")
            except Exception as e:
                self.logger.warning(f"清理临时目录失败: {e}")