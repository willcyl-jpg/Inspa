"""
构建器主类

负责整个构建流程的协调，将各个组件组合在一起。
映射需求：FR-BLD-004, FR-BLD-014, FR-BLD-015
"""

import io
import shutil
import time
import traceback
from pathlib import Path
from typing import Callable, Optional

from ..config.schema import InspaConfig
from ..utils import (
    get_stage_logger,
    LogStage,
    ensure_directory,
    get_temp_dir,
    format_size,
)
from .collector import FileCollector, FileInfo
from .compressor import CompressorFactory, CompressionError
from .header import HeaderBuilder, HashCalculator


# 进度回调类型
ProgressCallback = Callable[[str, int, int, str], None]


class BuildError(Exception):
    """构建错误"""
    pass


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
        self.logger = get_stage_logger(LogStage.INIT)
        
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
    ) -> None:
        """构建安装器
        
        Args:
            config: 配置对象
            output_path: 输出文件路径
            progress_callback: 进度回调函数
            
        Raises:
            BuildError: 构建失败
        """
        self.build_stats['start_time'] = time.time()
        
        try:
            self.logger.info("开始构建安装器", output_path=str(output_path))
            
            # 步骤 1: 收集文件
            if progress_callback:
                progress_callback("收集文件", 0, 100, "扫描输入目录...")
            
            files = self._collect_files(config)
            
            if progress_callback:
                progress_callback("收集文件", 100, 100, f"收集完成，找到 {len(files)} 个文件")
            
            # 步骤 2: 压缩文件
            if progress_callback:
                progress_callback("压缩文件", 0, 100, "初始化压缩器...")
            
            compressed_data, actual_algorithm = self._compress_files(config, files, progress_callback)
            
            if progress_callback:
                progress_callback("压缩文件", 100, 100, f"压缩完成，大小 {format_size(len(compressed_data))}")
            
            # 步骤 3: 计算哈希
            if progress_callback:
                progress_callback("计算哈希", 0, 100, "计算完整性哈希...")
            
            archive_hash = HashCalculator.hash_data(compressed_data)
            
            if progress_callback:
                progress_callback("计算哈希", 100, 100, f"哈希计算完成")
            
            # 步骤 4: 构建头部
            if progress_callback:
                progress_callback("构建头部", 0, 100, "生成头部信息...")
            
            header = self._build_header(config, files, actual_algorithm, archive_hash)
            
            if progress_callback:
                progress_callback("构建头部", 100, 100, "头部信息构建完成")
            
            # 步骤 5: 写入最终文件
            if progress_callback:
                progress_callback("生成安装器", 0, 100, "写入安装器文件...")
            
            self._write_installer(header, compressed_data, output_path, config)
            
            if progress_callback:
                progress_callback("生成安装器", 100, 100, "安装器写入完成")
            
            if progress_callback:
                progress_callback("完成", 100, 100, "构建成功完成")
            
            # 更新统计信息
            self.build_stats['end_time'] = time.time()
            self.build_stats['total_files'] = len([f for f in files if not f.is_directory])
            self.build_stats['total_size'] = sum(f.size for f in files if not f.is_directory)
            self.build_stats['compressed_size'] = len(compressed_data)
            
            if self.build_stats['total_size'] > 0:
                self.build_stats['compression_ratio'] = (
                    1.0 - self.build_stats['compressed_size'] / self.build_stats['total_size']
                ) * 100
            
            self.logger.info(
                "构建完成",
                duration=f"{self.build_stats['end_time'] - self.build_stats['start_time']:.2f}s",
                total_files=self.build_stats['total_files'],
                original_size=format_size(self.build_stats['total_size']),
                compressed_size=format_size(self.build_stats['compressed_size']),
                compression_ratio=f"{self.build_stats['compression_ratio']:.1f}%"
            )
            
        except Exception as e:
            self.build_stats['end_time'] = time.time()
            self.logger.error("构建失败", error=str(e), traceback=traceback.format_exc())
            if isinstance(e, BuildError):
                raise
            raise BuildError(f"构建失败: {e}") from e
    
    def get_build_stats(self) -> dict:
        """获取构建统计信息"""
        return self.build_stats.copy()
    
    def _collect_files(self, config: InspaConfig) -> list[FileInfo]:
        """收集文件"""
        logger = get_stage_logger(LogStage.COLLECT)
        logger.info("开始收集文件", input_count=len(config.inputs))
        
        try:
            files = self.collector.collect_files(config.inputs, config.exclude)
            
            stats = self.collector.get_statistics()
            logger.info(
                "文件收集完成",
                **stats
            )
            
            return files
            
        except Exception as e:
            logger.error("文件收集失败", error=str(e), traceback=traceback.format_exc())
            raise BuildError(f"文件收集失败: {e}") from e
    
    def _compress_files(
        self, 
        config: InspaConfig, 
        files: list[FileInfo], 
        progress_callback: Optional[ProgressCallback]
    ) -> tuple[bytes, str]:
        """压缩文件"""
        logger = get_stage_logger(LogStage.COMPRESS)
        logger.info("开始压缩文件", algorithm=config.compression.algo.value, level=config.compression.level)
        
        try:
            # 创建压缩器
            compressor = CompressorFactory.create_compressor(
                config.compression.algo,
                config.compression.level,
                config.compression.fallback_to_zip
            )
            
            actual_algorithm = compressor.get_algorithm().value
            
            if actual_algorithm != config.compression.algo.value:
                logger.warning(
                    "压缩算法回退",
                    requested=config.compression.algo.value,
                    actual=actual_algorithm
                )
            
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
            
            logger.info(
                "压缩完成",
                algorithm=actual_algorithm,
                original_size=format_size(sum(f.size for f in files if not f.is_directory)),
                compressed_size=format_size(len(compressed_data)),
                compression_ratio=f"{(1 - len(compressed_data) / max(1, sum(f.size for f in files if not f.is_directory))) * 100:.1f}%"
            )
            
            return compressed_data, actual_algorithm
            
        except CompressionError as e:
            logger.error("压缩失败", error=str(e), traceback=traceback.format_exc())
            raise BuildError(f"压缩失败: {e}") from e
        except Exception as e:
            logger.error("压缩过程异常", error=str(e), traceback=traceback.format_exc())
            raise BuildError(f"压缩过程异常: {e}") from e
    
    def _build_header(
        self, 
        config: InspaConfig, 
        files: list[FileInfo], 
        actual_algorithm: str, 
        archive_hash: str
    ) -> bytes:
        """构建头部"""
        logger = get_stage_logger(LogStage.HEADER)
        logger.info("开始构建头部")
        
        try:
            from ..config.schema import CompressionAlgorithm
            
            # 转换算法枚举
            compression_enum = CompressionAlgorithm(actual_algorithm)
            
            header_data = self.header_builder.build_header(
                config, files, compression_enum, archive_hash
            )
            
            header_bytes = self.header_builder.serialize_header(header_data)
            
            logger.info("头部构建完成", header_size=format_size(len(header_bytes)))
            
            return header_bytes
            
        except Exception as e:
            logger.error("头部构建失败", error=str(e), traceback=traceback.format_exc())
            raise BuildError(f"头部构建失败: {e}") from e
    
    def _write_installer(self, header: bytes, compressed_data: bytes, output_path: Path, config: InspaConfig) -> None:
        """写入最终安装器文件"""
        logger = get_stage_logger(LogStage.WRITE)
        logger.info("开始写入安装器", output_path=str(output_path))
        
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
            logger.info("安装器写入完成", file_size=format_size(file_size))
            
        except Exception as e:
            logger.error("写入安装器失败", error=str(e), traceback=traceback.format_exc())
            raise BuildError(f"写入安装器失败: {e}") from e
    
    def _get_runtime_stub(self, config: InspaConfig) -> bytes:
        """获取 Runtime Stub 数据
        
        动态编译 runtime stub 或使用预编译版本
        """
        logger = get_stage_logger(LogStage.STUB)
        logger.info("获取 Runtime Stub")
        need_custom = bool(getattr(config, 'resources', None) and config.resources and config.resources.icon)
        # 版本信息始终需要注入
        need_custom = True  # 直接强制动态编译以便写入版本信息和图标
        
        try:
            # 首先尝试使用预编译的 stub
            if not need_custom:
                stub_path = Path(__file__).parent.parent / "runtime_stub" / "dist" / "stub.exe"
                if stub_path.exists():
                    logger.info("使用预编译的 Runtime Stub", stub_path=str(stub_path))
                    stub_data = stub_path.read_bytes()
                    logger.info("Runtime Stub 准备完成", stub_size=format_size(len(stub_data)))
                    return stub_data
            
            # 如果没有预编译版本，动态编译
            logger.info("预编译 stub 不存在，开始动态编译")
            stub_data = self._compile_runtime_stub(config)
            logger.info("Runtime Stub 准备完成", stub_size=format_size(len(stub_data)))
            return stub_data
            
        except Exception as e:
            logger.error("获取 Runtime Stub 失败", error=str(e))
            logger.error("详细错误信息", traceback=traceback.format_exc())
            raise BuildError(f"无法获取 Runtime Stub: {e}")
    
    def _compile_runtime_stub(self, config: InspaConfig) -> bytes:
        """动态编译 Runtime Stub"""
        import subprocess
        import tempfile
        
        logger = get_stage_logger(LogStage.STUB)
        logger.info("开始编译 Runtime Stub")
        
        # 获取 runtime_stub 目录
        runtime_stub_dir = Path(__file__).parent.parent / "runtime_stub"
        main_py = runtime_stub_dir / "standalone_main.py"
        
        if not main_py.exists():
            raise BuildError(f"Runtime stub 源文件不存在: {main_py}")
        
        # 创建临时目录用于编译
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_dir = temp_path / "dist"
            
            try:
                # 使用 PyInstaller 编译 stub
                cmd = [
                    "pyinstaller",
                    "--onefile",
                    "--noconsole",
                    "--distpath", str(output_dir),
                    "--workpath", str(temp_path / "build"),
                    "--specpath", str(temp_path),
                    "--name", "stub",
                ]

                # 图标
                if config.resources and config.resources.icon:
                    icon_path = str(config.resources.icon)
                    logger.info(f"添加图标: {icon_path}")
                    cmd.extend(["--icon", icon_path])

                # 版本文件生成
                version_file = temp_path / "version_info.txt"
                version_info = config.get_version_info()
                version_lines = [f"# UTF-8\n# Auto-generated version file\n"]
                # 固定示例结构 (FILEVERSION, PRODUCTVERSION 使用逗号分隔的数字，简单拆分语义化版本前三段，不足补 0)
                def split_ver(v: str):
                    parts = [p for p in v.split('-')[0].split('.')][:4]
                    while len(parts) < 4:
                        parts.append('0')
                    return ','.join(parts)
                numeric_ver = split_ver(version_info['FileVersion'])
                version_lines.append(f"VSVersionInfo(\n  ffi=FixedFileInfo(\n    filevers=({numeric_ver}),\n    prodvers=({numeric_ver}),\n    mask=0x3f,\n    flags=0x0,\n    OS=0x4,\n    fileType=0x1,\n    subtype=0x0,\n    date=(0, 0)\n  ),\n  kids=[\n    StringFileInfo([\n      StringTable(\n        '040904B0',\n        [\n          StringStruct('CompanyName', '{version_info['CompanyName']}'),\n          StringStruct('FileDescription', '{version_info['FileDescription']}'),\n          StringStruct('FileVersion', '{version_info['FileVersion']}'),\n          StringStruct('InternalName', '{version_info['InternalName']}'),\n          StringStruct('LegalCopyright', '{version_info['LegalCopyright']}'),\n          StringStruct('OriginalFilename', '{version_info['OriginalFilename']}'),\n          StringStruct('ProductName', '{version_info['ProductName']}'),\n          StringStruct('ProductVersion', '{version_info['ProductVersion']}'),\n        ]\n      )\n    ]),\n    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n  ]\n)\n")
                version_file.write_text(''.join(version_lines), encoding='utf-8')
                cmd.extend(["--version-file", str(version_file)])

                cmd.append(str(main_py))
                
                logger.info("执行编译命令", cmd=" ".join(cmd))
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(temp_path),  # 改为在临时目录运行
                    timeout=120  # 添加超时
                )
                
                if result.returncode != 0:
                    logger.error("编译失败", stderr=result.stderr, stdout=result.stdout)
                    raise BuildError(f"PyInstaller 编译失败: {result.stderr}")
                
                # 读取编译结果
                stub_exe = output_dir / "stub.exe"
                if not stub_exe.exists():
                    raise BuildError("编译完成但未找到输出文件")
                
                stub_data = stub_exe.read_bytes()
                logger.info("Runtime Stub 编译完成", size=format_size(len(stub_data)))
                
                return stub_data
                
            except subprocess.TimeoutExpired:
                raise BuildError("编译超时")
            except subprocess.CalledProcessError as e:
                raise BuildError(f"编译过程出错: {e}")
            except Exception as e:
                logger.error("编译过程异常", error=str(e))
                logger.error("详细错误信息", traceback=traceback.format_exc())
                raise BuildError(f"编译 Runtime Stub 失败: {e}")