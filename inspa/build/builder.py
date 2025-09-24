"""
构建器主类

负责整个构建流程的协调，将各个组件组合在一起。
映射需求：FR-BLD-004, FR-BLD-014, FR-BLD-015
"""

import io
import shutil
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ..config.schema import InspaConfig
from ..utils import (
    ensure_directory,
    get_temp_dir,
    format_size,
)
from ..utils.logging import info, success, error, warning, LogStage
from .collector import FileCollector, FileInfo
from .compressor import CompressorFactory, CompressionError
from .header import HeaderBuilder, HashCalculator

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
            
        Raises:
            BuildError: 构建失败
        """
        self.build_stats['start_time'] = time.time()
        
        try:
            info(f"开始构建安装器: {output_path}", stage=LogStage.INIT)
            
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
            
            success("构建完成", stage=LogStage.DONE)
            info(f"  构建时间: {self.build_stats['end_time'] - self.build_stats['start_time']:.2f}s")
            info(f"  文件总数: {self.build_stats['total_files']}")
            info(f"  原始大小: {format_size(self.build_stats['total_size'])}")
            info(f"  压缩大小: {format_size(self.build_stats['compressed_size'])}")
            info(f"  压缩率: {self.build_stats['compression_ratio']:.1f}%")
            
            # 返回构建结果
            final_size = output_path.stat().st_size
            build_time = self.build_stats['end_time'] - self.build_stats['start_time']
            
            return BuildResult(
                success=True,
                output_path=output_path,
                output_size=final_size,
                build_time=build_time,
                compression_ratio=self.build_stats['compression_ratio'] / 100.0  # 转换为比例
            )
            
        except Exception as e:
            self.build_stats['end_time'] = time.time()
            error(f"构建失败: {e}", stage=LogStage.ERROR)
            error(f"详细错误信息:\n{traceback.format_exc()}")
            
            error_msg = str(e)
            if isinstance(e, BuildError):
                return BuildResult(success=False, error=error_msg)
            
            return BuildResult(success=False, error=f"构建失败: {error_msg}")
    
    def get_build_stats(self) -> dict:
        """获取构建统计信息"""
        return self.build_stats.copy()
    
    def _collect_files(self, config: InspaConfig) -> list[FileInfo]:
        """收集文件"""
        info(f"收集文件 - 输入源: {len(config.inputs)}", stage=LogStage.COLLECT)
        
        try:
            files = self.collector.collect_files(config.inputs, config.exclude)
            
            stats = self.collector.get_statistics()
            success("文件收集完成", stage=LogStage.COLLECT)
            info(f"  收集文件: {stats.get('files_collected', 0)}")
            info(f"  跳过文件: {stats.get('files_skipped', 0)}")
            info(f"  总大小: {format_size(stats.get('total_size', 0))}")
            
            return files
            
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
            
            return compressed_data, actual_algorithm
            
        except CompressionError as e:
            error(f"压缩失败: {e}", stage=LogStage.COMPRESS)
            raise BuildError(f"压缩失败: {e}") from e
        except Exception as e:
            error(f"压缩过程异常: {e}", stage=LogStage.COMPRESS)
            raise BuildError(f"压缩过程异常: {e}") from e
    
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
            # 首先尝试使用预编译的 stub
            if not need_custom:
                stub_path = Path(__file__).parent.parent / "runtime_stub" / "dist" / "stub.exe"
                if stub_path.exists():
                    info(f"使用预编译的Runtime Stub: {stub_path}", stage=LogStage.STUB)
                    stub_data = stub_path.read_bytes()
                    success(f"Runtime Stub准备完成 - 大小: {format_size(len(stub_data))}", stage=LogStage.STUB)
                    return stub_data
            
            # 如果没有预编译版本，动态编译
            warning("预编译stub不存在，开始动态编译", stage=LogStage.STUB)
            stub_data = self._compile_runtime_stub(config)
            success(f"Runtime Stub准备完成 - 大小: {format_size(len(stub_data))}", stage=LogStage.STUB)
            return stub_data
            
        except Exception as e:
            error(f"获取Runtime Stub失败: {e}", stage=LogStage.STUB)
            error(f"详细错误信息:\n{traceback.format_exc()}")
            raise BuildError(f"无法获取 Runtime Stub: {e}")
    
    def _compile_runtime_stub(self, config: InspaConfig) -> bytes:
        """动态编译 Runtime Stub"""
        import subprocess
        import tempfile
        
        info("开始编译Runtime Stub", stage=LogStage.STUB)
        
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
                    "--console",  # 改为console模式以便看到输出
                    "--distpath", str(output_dir),
                    "--workpath", str(temp_path / "build"),
                    "--specpath", str(temp_path),
                    "--name", "stub",
                ]

                # 图标
                if config.resources and config.resources.icon:
                    icon_path = str(config.resources.icon)
                    info(f"添加图标: {icon_path}", stage=LogStage.STUB)
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
                
                info("执行PyInstaller编译...", stage=LogStage.STUB)
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(temp_path),  # 改为在临时目录运行
                    timeout=120  # 添加超时
                )
                
                if result.returncode != 0:
                    error("编译失败", stage=LogStage.STUB)
                    error(f"stderr: {result.stderr}")
                    info(f"stdout: {result.stdout}")
                    raise BuildError(f"PyInstaller 编译失败: {result.stderr}")
                
                # 读取编译结果
                stub_exe = output_dir / "stub.exe"
                if not stub_exe.exists():
                    raise BuildError("编译完成但未找到输出文件")
                
                stub_data = stub_exe.read_bytes()
                success(f"Runtime Stub编译完成 - 大小: {format_size(len(stub_data))}", stage=LogStage.STUB)
                
                return stub_data
                
            except subprocess.TimeoutExpired:
                raise BuildError("编译超时")
            except subprocess.CalledProcessError as e:
                raise BuildError(f"编译过程出错: {e}")
            except Exception as e:
                error(f"编译过程异常: {e}", stage=LogStage.STUB)
                error(f"详细错误信息:\n{traceback.format_exc()}")
                raise BuildError(f"编译 Runtime Stub 失败: {e}")
    
    def _build_header(self, config: InspaConfig, files: list[FileInfo], compressed_data: bytes, actual_algorithm: str) -> bytes:
        """构建头部数据"""
        info("构建头部数据", stage=LogStage.HEADER)
        
        try:
            # 计算哈希
            archive_hash = HashCalculator.hash_data(compressed_data)
            
            # 构建头部
            header_dict = self.header_builder.build_header(
                config=config,
                files=files,
                compression_algo=actual_algorithm,
                archive_hash=archive_hash
            )
            
            # 序列化为JSON
            header_json = self.header_builder.serialize_header(header_dict)
            
            return header_json.encode('utf-8')
            
        except Exception as e:
            error(f"构建头部失败: {e}", stage=LogStage.HEADER)
            raise BuildError(f"构建头部失败: {e}") from e
    
    def _assemble_installer(self, header_data: bytes, compressed_data: bytes, output_path: Path, progress_callback: Optional[ProgressCallback] = None) -> int:
        """组装最终安装器"""
        info(f"组装安装器: {output_path}", stage=LogStage.WRITE)
        
        try:
            # 确保输出目录存在
            ensure_directory(output_path.parent)
            
            if progress_callback:
                progress_callback("组装文件", 10, 100, "生成 Runtime Stub...")
            
            # 生成 Runtime Stub
            stub_data = self._generate_runtime_stub()
            
            if progress_callback:
                progress_callback("组装文件", 50, 100, "写入最终文件...")
            
            # 创建最终文件
            with open(output_path, 'wb') as f:
                # 写入 stub
                f.write(stub_data)
                
                # 写入头部长度 (8字节 little-endian)
                header_len = len(header_data)
                f.write(header_len.to_bytes(8, byteorder='little'))
                
                # 写入头部数据
                f.write(header_data)
                
                # 写入压缩数据
                f.write(compressed_data)
                
                # 写入尾部哈希校验
                archive_hash = HashCalculator.hash_data(compressed_data)
                f.write(bytes.fromhex(archive_hash))
            
            final_size = output_path.stat().st_size
            
            if progress_callback:
                progress_callback("组装文件", 100, 100, f"完成，大小 {format_size(final_size)}")
            
            success(f"安装器组装完成 - 大小: {format_size(final_size)}", stage=LogStage.WRITE)
            
            return final_size
            
        except Exception as e:
            error(f"组装安装器失败: {e}", stage=LogStage.WRITE)
            raise BuildError(f"组装安装器失败: {e}") from e
    
    def _generate_runtime_stub(self) -> bytes:
        """生成 Runtime Stub"""
        # 这是一个简化的实现，实际需要调用 PyInstaller 或使用预编译的 stub
        # 当前返回一个最小的占位 stub
        
        info("生成 Runtime Stub", stage=LogStage.STUB)
        
        # 创建一个最小的 Python 脚本作为 stub
        stub_script = '''
import sys
import os
from pathlib import Path

def main():
    print("Inspa Runtime Stub - 这是一个测试版本")
    print("正在提取数据...")
    # TODO: 实现实际的提取和安装逻辑
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
        
        # 简单返回脚本内容（实际应该是编译后的可执行文件）
        warning("使用测试 Runtime Stub - 生产环境需要实现完整的编译流程", stage=LogStage.STUB)
        
        return stub_script.encode('utf-8')