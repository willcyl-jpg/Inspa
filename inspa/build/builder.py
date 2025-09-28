"""
构建器主类

负责整个构建流程的协调，将各个组件组合在一起。
映射需求：FR-BLD-004, FR-BLD-014, FR-BLD-015
"""

import io
import shutil
import time
import traceback
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ..config.schema import InspaConfig
from ..utils import (
    ensure_directory,
    get_temp_dir,
    format_size,
)
from ..utils.logging import info, success, error, warning, debug, LogStage
from .collector import FileCollector, FileInfo
from .compressor import CompressorFactory, CompressionError
from .header import HeaderBuilder, HashCalculator

# 新的快速定位 Footer 魔术字节 (8 bytes)
FOOTER_MAGIC = b'INSPAF01'

# 进度回调类型
ProgressCallback = Callable[[str, int, int, str], None]


class BuildError(Exception):
    """构建错误"""
    pass


@dataclass
class BuildResult:
    """构建结果"""
    success: bool
    output_path: Optional[Path] = None
    output_size: Optional[int] = None
    build_time: Optional[float] = None
    compression_ratio: Optional[float] = None
    error: Optional[str] = None


class Builder:
    """安装器构建器
    
    协调整个构建流程，包括文件收集、压缩、头部生成和最终组装。
    """
    
    def __init__(self, builder_version: str = "0.1.0"):
        """初始化构建器
        
        Args:
            builder_version: 构建器版本号
        """
        self.builder_version = builder_version
        
        # 各个组件
        self.collector = FileCollector()
        self.header_builder = HeaderBuilder(builder_version)
        
        # 构建统计
        self.build_stats = {
            'start_time': 0,
            'end_time': 0,
            'total_files': 0,
            'total_size': 0,
            'compressed_size': 0,
            'compression_ratio': 0.0,
        }
    
    def build(
        self,
        config: InspaConfig,
        output_path: Path,
        progress_callback: Optional[ProgressCallback] = None
    ) -> BuildResult:
        """构建安装器
        
        Args:
            config: 配置对象
            output_path: 输出文件路径
            progress_callback: 进度回调函数
            
        Returns:
            BuildResult: 构建结果
            
        Raises:
            BuildError: 构建失败
        """
        self.build_stats['start_time'] = time.time()
        
        try:
            info(f"开始构建安装器: {output_path}", stage=LogStage.BUILD)
            debug(f"构建配置: algorithm={config.compression.algo.value} level={config.compression.level} inputs={len(config.inputs)}", stage=LogStage.BUILD)
            
            # 步骤 1: 收集文件 (0%-20%)
            if progress_callback:
                progress_callback("收集文件", 0, 100, "扫描输入目录...")
            
            files = self._collect_files(config, progress_callback)
            
            if progress_callback:
                progress_callback("收集文件", 20, 100, f"找到 {len(files)} 个文件")
            
            # 步骤 2: 压缩文件 (20%-60%)  
            if progress_callback:
                progress_callback("压缩文件", 20, 100, "开始压缩...")
            
            compressed_data, actual_algorithm = self._compress_files(config, files, progress_callback)
            
            if progress_callback:
                progress_callback("压缩文件", 60, 100, f"压缩完成，大小: {format_size(len(compressed_data))}")
            
            # 步骤 3: 构建头部 (60%-70%)
            if progress_callback:
                progress_callback("构建头部", 60, 100, "生成安装器头部...")
            
            header_data = self._build_header_data(config, files, compressed_data, actual_algorithm)
            
            if progress_callback:
                progress_callback("构建头部", 70, 100, "头部数据生成完成")
            
            # 步骤 4: 组装安装器 (70%-100%)
            if progress_callback:
                progress_callback("组装安装器", 70, 100, "生成最终安装器...")
            
            final_size = self._assemble_installer(config, header_data, compressed_data, output_path, progress_callback)
            
            # 计算统计信息
            self.build_stats['end_time'] = time.time()
            build_time = self.build_stats['end_time'] - self.build_stats['start_time']
            
            original_size = sum(f.size for f in files if not f.is_directory)
            compression_ratio = (1 - len(compressed_data) / max(1, original_size)) * 100
            
            # 构建成功
            result = BuildResult(
                success=True,
                output_path=output_path,
                output_size=final_size,
                build_time=build_time,
                compression_ratio=compression_ratio
            )
            
            success(f"安装器构建成功: {output_path}", stage=LogStage.BUILD)
            info(f"构建时间: {build_time:.1f}秒")
            info(f"最终大小: {format_size(final_size)}")
            info(f"压缩率: {compression_ratio:.1f}%")
            
            return result
            
        except Exception as e:
            self.build_stats['end_time'] = time.time()
            build_time = self.build_stats['end_time'] - self.build_stats['start_time']
            
            error_msg = str(e)
            error(f"构建失败: {error_msg}", stage=LogStage.BUILD)
            
            return BuildResult(
                success=False,
                build_time=build_time,
                error=error_msg
            )
    
    def get_build_stats(self) -> dict:
        """获取构建统计信息"""
        return self.build_stats.copy()
    def _collect_files(
        self, 
        config: InspaConfig, 
        progress_callback: Optional[ProgressCallback] = None
    ) -> list[FileInfo]:
        """收集要打包的文件"""
        info("收集文件", stage=LogStage.COLLECT)
        
        try:
            all_files = []
            
            # 遍历所有输入路径
            for i, input_path in enumerate(config.inputs):
                if progress_callback:
                    progress_callback("收集文件", int((i / len(config.inputs)) * 20), 100, f"扫描: {input_path.path}")
                
                source_path = Path(input_path.path)
                
                if not source_path.exists():
                    warning(f"输入路径不存在: {source_path}", stage=LogStage.COLLECT)
                    continue
                
                # 创建文件收集器
                # 收集文件
                if source_path.is_file():
                    stat = source_path.stat()
                    file_info = FileInfo(
                        path=source_path.resolve(),
                        relative_path=Path(source_path.name),
                        size=stat.st_size,
                        mtime=stat.st_mtime,
                        is_directory=False
                    )
                    all_files.append(file_info)
                else:
                    dir_files = self.collector.collect_files([input_path], exclude_patterns=config.exclude or [])
                    all_files.extend(dir_files)
            
            # 统计信息
            total_files = len([f for f in all_files if not f.is_directory])
            total_size = sum(f.size for f in all_files if not f.is_directory)
            
            self.build_stats['total_files'] = total_files
            self.build_stats['total_size'] = total_size
            
            success(f"文件收集完成", stage=LogStage.COLLECT)
            info(f"  文件数量: {total_files}")
            info(f"  总大小: {format_size(total_size)}")
            # 在 DEBUG 级别输出前 20 个文件用于诊断
            for idx, f in enumerate([ff for ff in all_files if not ff.is_directory][:20]):
                debug(f"文件[{idx}]: {f.relative_path} size={format_size(f.size)} mtime={int(f.mtime)}", stage=LogStage.COLLECT)
            if total_files > 20:
                debug(f"... 还有 {total_files - 20} 个文件未列出", stage=LogStage.COLLECT)
            
            return all_files
            
        except Exception as e:
            error(f"文件收集失败: {e}", stage=LogStage.COLLECT)
            raise BuildError(f"文件收集失败: {e}") from e
    
    def _compress_files(
        self, 
        config: InspaConfig, 
        files: list[FileInfo], 
        progress_callback: Optional[ProgressCallback]
    ) -> tuple[bytes, str]:
        """压缩文件"""
        info(f"压缩文件 - 算法: {config.compression.algo.value}, 级别: {config.compression.level}", stage=LogStage.COMPRESS)
        
        try:
            # 创建压缩器
            compressor = CompressorFactory.create_compressor(
                config.compression.algo,
                config.compression.level,
                config.compression.fallback_to_zip
            )
            
            actual_algorithm = compressor.get_algorithm().value
            
            if actual_algorithm != config.compression.algo.value:
                warning(f"压缩算法回退: {config.compression.algo.value} -> {actual_algorithm}", stage=LogStage.COMPRESS)
                
            
            # 压缩到内存
            output_buffer = io.BytesIO()
            
            def compress_progress(current: int, total: int, current_file: Optional[str] = None) -> None:
                if progress_callback and total > 0:
                    # 在压缩阶段内部报告进度 (0-100%)
                    file_progress = int((current / total) * 100)
                    
                    message = "压缩中..."
                    if current_file:
                        # 只显示文件名，不显示完整路径
                        filename = Path(current_file).name if current_file else ""
                        message = f"压缩: {filename}"
                    
                    progress_callback("压缩文件", file_progress, 100, message)
            
            compressed_size = compressor.compress_files(files, output_buffer, compress_progress)
            
            compressed_data = output_buffer.getvalue()
            
            original_size = sum(f.size for f in files if not f.is_directory)
            compression_ratio = (1 - len(compressed_data) / max(1, original_size)) * 100
            
            success("压缩完成", stage=LogStage.COMPRESS)
            info(f"  算法: {actual_algorithm}")
            info(f"  原始大小: {format_size(original_size)}")
            info(f"  压缩大小: {format_size(len(compressed_data))}")
            info(f"  压缩率: {compression_ratio:.1f}%")
            debug(f"压缩数据长度={len(compressed_data)} bytes", stage=LogStage.COMPRESS)
            
            return compressed_data, actual_algorithm
            
        except CompressionError as e:
            error(f"压缩失败: {e}", stage=LogStage.COMPRESS)
            raise BuildError(f"压缩失败: {e}") from e
        except Exception as e:
            error(f"压缩过程异常: {e}", stage=LogStage.COMPRESS)
            raise BuildError(f"压缩过程异常: {e}") from e
    
    def _build_header_data(
        self, 
        config: InspaConfig, 
        files: list[FileInfo], 
        compressed_data: bytes, 
        actual_algorithm: str
    ) -> bytes:
        """构建头部数据"""
        info("构建头部数据", stage=LogStage.HEADER)
        
        try:
            # 计算压缩数据哈希
            archive_hash = HashCalculator.hash_data(compressed_data)
            
            from ..config.schema import CompressionAlgorithm
            compression_enum = CompressionAlgorithm(actual_algorithm)
            
            # 构建头部
            original_size = sum(f.size for f in files if not f.is_directory)
            compressed_size = len(compressed_data)
            header_dict = self.header_builder.build_header(
                config=config,
                files=files,
                compression_algo=compression_enum,
                archive_hash=archive_hash,
                original_size=original_size,
                compressed_size=compressed_size
            )
            
            # 序列化为JSON
            header_bytes = self.header_builder.serialize_header(header_dict)
            
            success(f"头部数据构建完成 - 大小: {format_size(len(header_bytes))}", stage=LogStage.HEADER)
            debug(f"头部预览: {header_bytes[:120]!r}...", stage=LogStage.HEADER)
            
            return header_bytes
            
        except Exception as e:
            error(f"构建头部失败: {e}", stage=LogStage.HEADER)
            raise BuildError(f"构建头部失败: {e}") from e
    
    def _build_header(
        self, 
        config: InspaConfig, 
        files: list[FileInfo], 
        actual_algorithm: str, 
        archive_hash: str
    ) -> bytes:
        """构建头部"""
        info("构建头部", stage=LogStage.HEADER)
        
        try:
            from ..config.schema import CompressionAlgorithm
            
            # 转换算法枚举
            compression_enum = CompressionAlgorithm(actual_algorithm)
            
            header_data = self.header_builder.build_header(
                config, files, compression_enum, archive_hash
            )
            
            header_bytes = self.header_builder.serialize_header(header_data)
            
            success(f"头部构建完成 - 大小: {format_size(len(header_bytes))}", stage=LogStage.HEADER)
            
            return header_bytes
            
        except Exception as e:
            error(f"头部构建失败: {e}", stage=LogStage.HEADER)
            raise BuildError(f"头部构建失败: {e}") from e
    
    def _write_installer(self, header: bytes, compressed_data: bytes, output_path: Path, config: InspaConfig) -> None:
        """写入最终安装器文件"""
        info(f"写入安装器: {output_path}", stage=LogStage.WRITE)
        
        try:
            # 确保输出目录存在
            ensure_directory(output_path.parent)
            
            # 获取或创建 Runtime Stub
            stub_data = self._get_runtime_stub(config)
            
            # 写入最终文件
            # 格式: [stub_exe][header_len:8][header][compressed_data][hash:32]
            with open(output_path, 'wb') as f:
                # 1. Runtime Stub
                f.write(stub_data)
                
                # 2. Header 长度 (8 字节小端)
                header_len = len(header)
                f.write(header_len.to_bytes(8, 'little'))
                
                # 3. Header 数据
                f.write(header)
                
                # 4. 压缩数据
                f.write(compressed_data)
                
                # 5. 压缩数据哈希 (32 字节)
                hash_bytes = bytes.fromhex(HashCalculator.hash_data(compressed_data))
                f.write(hash_bytes)
            
            file_size = output_path.stat().st_size
            success(f"安装器写入完成 - 大小: {format_size(file_size)}", stage=LogStage.WRITE)
            
        except Exception as e:
            error(f"写入安装器失败: {e}", stage=LogStage.WRITE)
            raise BuildError(f"写入安装器失败: {e}") from e
    
    def _get_runtime_stub(self, config: InspaConfig) -> bytes:
        """获取 Runtime Stub 数据
        
        动态编译 runtime stub 或使用预编译版本
        """
        info("获取Runtime Stub", stage=LogStage.STUB)
        need_custom = bool(getattr(config, 'resources', None) and config.resources and config.resources.icon)
        # 版本信息始终需要注入
        need_custom = True  # 直接强制动态编译以便写入版本信息和图标
        
        try:
            # 测试模式快速路径: 避免在单元测试里调用 PyInstaller (加速并去除外部依赖)
            import os
            if os.environ.get('INSPA_TEST_MODE') == '1':
                info("检测到测试模式，使用内置伪 stub", stage=LogStage.STUB)
                dummy = b'MZ' + b'\x00' * 58  # 最小 DOS 头 (不可执行但占位) 60字节
                success(f"测试模式 stub 准备完成 - 大小: {len(dummy)}B", stage=LogStage.STUB)
                return dummy
            # 首先尝试使用预编译的 stub
            if not need_custom:
                stub_path = Path(__file__).parent.parent / "runtime_stub" / "dist" / "stub.exe"
                if stub_path.exists():
                    info(f"使用预编译的Runtime Stub: {stub_path}", stage=LogStage.STUB)
                    stub_data = stub_path.read_bytes()
                    success(f"Runtime Stub准备完成 - 大小: {format_size(len(stub_data))}", stage=LogStage.STUB)
                    return stub_data
            
            # 如果没有预编译版本或需要定制（图标/版本信息），动态编译
            info("使用动态编译 Runtime Stub 以注入版本信息和图标", stage=LogStage.STUB)
            stub_data = self._compile_runtime_stub(config)
            success(f"Runtime Stub准备完成 - 大小: {format_size(len(stub_data))}", stage=LogStage.STUB)
            return stub_data
            
        except Exception as e:
            error(f"获取Runtime Stub失败: {e}", stage=LogStage.STUB)
            error(f"详细错误信息:\n{traceback.format_exc()}")
            raise BuildError(f"无法获取 Runtime Stub: {e}")
    
    def _compile_runtime_stub(self, config: InspaConfig) -> bytes:
        """动态编译 Runtime Stub (缺少 PyInstaller 时返回占位 stub)."""
        import subprocess
        import tempfile
        import importlib

        info("开始编译Runtime Stub", stage=LogStage.STUB)
        runtime_stub_dir = Path(__file__).parent.parent / "runtime_stub"
        main_py = runtime_stub_dir / "installer.py"
        if not main_py.exists():
            raise BuildError(f"Runtime stub 源文件不存在: {main_py}")

        # 缺少 PyInstaller -> 占位 stub
        try:
            importlib.import_module("PyInstaller")  # noqa: F401
        except ImportError:
            info("未检测到 PyInstaller, 使用占位 stub (测试/快速模式)", stage=LogStage.STUB)
            dummy = b"MZ" + b"\x00" * 58
            success(f"占位 stub 准备完成 - 大小: {len(dummy)}B", stage=LogStage.STUB)
            return dummy

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_dir = temp_path / "dist"
            try:
                cmd = [
                    sys.executable,
                    "-m",
                    "PyInstaller",
                    "--onefile",
                    "--console",
                    "--distpath", str(output_dir),
                    "--workpath", str(temp_path / "build"),
                    "--specpath", str(temp_path),
                    "--name", "stub",
                ]
                try:
                    if config.install.show_ui and "--console" in cmd:
                        cmd[cmd.index("--console")] = "--noconsole"
                        info("启用 UI: 隐藏控制台窗口", stage=LogStage.STUB)
                    else:
                        info("未启用 UI: 使用控制台窗口", stage=LogStage.STUB)
                except AttributeError:
                    warning("install.show_ui 未定义, 使用默认控制台窗口", stage=LogStage.STUB)
                try:
                    if config.install.require_admin:
                        cmd.append("--uac-admin")
                        info("启用 UAC 提权", stage=LogStage.STUB)
                except AttributeError:
                    warning("install.require_admin 未定义, 跳过 UAC", stage=LogStage.STUB)
                if getattr(config, "resources", None) and config.resources and config.resources.icon:
                    icon_path = str(config.resources.icon)
                    cmd.extend(["--icon", icon_path])
                    info(f"添加图标: {icon_path}", stage=LogStage.STUB)

                version_file = temp_path / "version_info.txt"
                version_info = config.get_version_info()
                def split_ver(v: str) -> str:
                    parts = [p for p in v.split('-')[0].split('.')][:4]
                    while len(parts) < 4:
                        parts.append('0')
                    return ','.join(parts)
                numeric_ver = split_ver(version_info['FileVersion'])
                version_lines = [
                    "# UTF-8\n# Auto-generated version file\n",
                    f"VSVersionInfo(\n  ffi=FixedFileInfo(\n    filevers=({numeric_ver}),\n    prodvers=({numeric_ver}),\n    mask=0x3f,\n    flags=0x0,\n    OS=0x4,\n    fileType=0x1,\n    subtype=0x0,\n    date=(0, 0)\n  ),\n  kids=[\n    StringFileInfo([\n      StringTable(\n        '040904B0',\n        [\n          StringStruct('CompanyName', '{version_info['CompanyName']}'),\n          StringStruct('FileDescription', '{version_info['FileDescription']}'),\n          StringStruct('FileVersion', '{version_info['FileVersion']}'),\n          StringStruct('InternalName', '{version_info['InternalName']}'),\n          StringStruct('LegalCopyright', '{version_info['LegalCopyright']}'),\n          StringStruct('OriginalFilename', '{version_info['OriginalFilename']}'),\n          StringStruct('ProductName', '{version_info['ProductName']}'),\n          StringStruct('ProductVersion', '{version_info['ProductVersion']}'),\n        ]\n      )\n    ]),\n    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n  ]\n)\n"
                ]
                version_file.write_text(''.join(version_lines), encoding='utf-8')
                cmd.extend(["--version-file", str(version_file)])
                cmd.append(str(main_py))
                info("执行 PyInstaller 编译...", stage=LogStage.STUB)
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(temp_path),
                    timeout=180,
                )
                if result.returncode != 0:
                    error("编译失败", stage=LogStage.STUB)
                    error(f"stderr: {result.stderr}")
                    info(f"stdout: {result.stdout}")
                    raise BuildError(f"PyInstaller 编译失败: {result.stderr}")
                stub_exe = output_dir / "stub.exe"
                if not stub_exe.exists():
                    raise BuildError("编译完成但未找到输出文件")
                data = stub_exe.read_bytes()
                success(f"Runtime Stub编译完成 - 大小: {format_size(len(data))}", stage=LogStage.STUB)
                return data
            except subprocess.TimeoutExpired:
                raise BuildError("编译超时")
            except subprocess.CalledProcessError as e:
                raise BuildError(f"编译过程出错: {e}")
            except Exception as e:  # noqa: BLE001
                error(f"编译过程异常: {e}", stage=LogStage.STUB)
                error(f"详细错误信息:\n{traceback.format_exc()}")
                raise BuildError(f"编译 Runtime Stub 失败: {e}")
    
    def _assemble_installer(
        self,
        config: InspaConfig,
        header_data: bytes, 
        compressed_data: bytes, 
        output_path: Path, 
        progress_callback: Optional[ProgressCallback] = None
    ) -> int:
        """组装最终安装器"""
        info(f"组装安装器: {output_path}", stage=LogStage.WRITE)
        
        try:
            # 确保输出目录存在
            ensure_directory(output_path.parent)
            
            if progress_callback:
                progress_callback("组装文件", 70, 100, "生成 Runtime Stub...")
            
            # 获取或创建 Runtime Stub
            stub_data = self._get_runtime_stub(config)
            
            if progress_callback:
                progress_callback("组装文件", 85, 100, "写入最终文件...")
            
            # 预计算各段偏移
            stub_size = len(stub_data)
            header_len = len(header_data)
            # header_offset 应该指向头部长度字段起始位置（即 stub 结束位置），
            # 运行时解析流程: seek(header_offset) -> 读8字节len -> 读header
            # 之前误写为 stub_size + 8 导致解析器读取到 header 的前8字节当作长度，产生不匹配
            header_offset = stub_size  # 指向 8 字节 header_len 字段开头
            compressed_offset = header_offset + 8 + header_len
            compressed_size = len(compressed_data)
            archive_hash = HashCalculator.hash_data(compressed_data)

            # Footer 结构: <8sQQQQ32s>
            # magic, header_offset, header_len, compressed_offset, compressed_size, archive_hash(32字节)
            debug(
                f"Offsets 计算: stub_size={stub_size} header_offset={header_offset} header_len={header_len} compressed_offset={compressed_offset} compressed_size={compressed_size}",
                stage=LogStage.WRITE
            )
            footer_struct = struct.pack(
                '<8sQQQQ32s',
                FOOTER_MAGIC,
                header_offset,
                header_len,
                compressed_offset,
                compressed_size,
                bytes.fromhex(archive_hash)
            )

            # 创建最终文件 (保持向后兼容: 仍写入旧的 hash 32 字节, 然后追加 footer)
            with open(output_path, 'wb') as f:
                # 1. 写入 runtime stub
                f.write(stub_data)
                # 2. 写入头部长度 (8 字节 LE)
                f.write(header_len.to_bytes(8, 'little'))
                # 3. 写入头部数据
                f.write(header_data)
                # 4. 写入压缩数据
                f.write(compressed_data)
                # 5. 旧格式尾部哈希 (供旧解析器扫描验证) 32 字节
                f.write(bytes.fromhex(archive_hash))
                # 6. 新增 Footer 72 字节
                f.write(footer_struct)
            
            final_size = output_path.stat().st_size
            
            if progress_callback:
                progress_callback("组装文件", 100, 100, f"完成，大小 {format_size(final_size)}")
            
            success(f"安装器组装完成 - 大小: {format_size(final_size)}", stage=LogStage.WRITE)
            
            return final_size
            
        except Exception as e:
            error(f"组装安装器失败: {e}", stage=LogStage.WRITE)
            raise BuildError(f"组装安装器失败: {e}") from e