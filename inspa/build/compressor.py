"""
压缩器抽象接口和实现

提供统一的压缩/解压接口，支持 Zstd 和 Zip 算法。
映射需求：FR-BLD-005, FR-BLD-006, FR-COMP-002
"""

import io
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Iterator, Optional, Protocol, Tuple

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

from ..config.schema import CompressionAlgorithm
from .collector import FileInfo


class CompressionError(Exception):
    """压缩相关错误"""
    pass


class DecompressionError(Exception):
    """解压相关错误"""
    pass


class ProgressCallback(Protocol):
    """进度回调协议"""
    
    def __call__(self, current: int, total: int, current_file: Optional[str] = None) -> None:
        """进度回调
        
        Args:
            current: 当前处理的字节数
            total: 总字节数
            current_file: 当前处理的文件名（可选）
        """
        ...


class Compressor(ABC):
    """压缩器抽象基类"""
    
    @abstractmethod
    def compress_files(
        self,
        files: list[FileInfo],
        output_stream: BinaryIO,
        progress_callback: Optional[ProgressCallback] = None
    ) -> int:
        """压缩文件到流
        
        Args:
            files: 要压缩的文件列表
            output_stream: 输出流
            progress_callback: 进度回调
            
        Returns:
            int: 压缩后的总字节数
            
        Raises:
            CompressionError: 压缩失败
        """
        pass
    
    @abstractmethod
    def decompress_to_directory(
        self,
        input_stream: BinaryIO,
        output_dir: Path,
        progress_callback: Optional[ProgressCallback] = None
    ) -> int:
        """从流解压到目录
        
        Args:
            input_stream: 输入流
            output_dir: 输出目录
            progress_callback: 进度回调
            
        Returns:
            int: 解压的总字节数
            
        Raises:
            CompressionError: 解压失败
        """
        pass
    
    @abstractmethod
    def get_algorithm(self) -> CompressionAlgorithm:
        """获取压缩算法名称"""
        pass


class ZstdCompressor(Compressor):
    """Zstd 压缩器"""
    
    def __init__(self, level: int = 10):
        if not ZSTD_AVAILABLE:
            raise CompressionError("zstandard 库未安装，无法使用 Zstd 压缩")
        
        self.level = level
        self._cctx = zstd.ZstdCompressor(level=level)
        self._dctx = zstd.ZstdDecompressor()
    
    def get_algorithm(self) -> CompressionAlgorithm:
        return CompressionAlgorithm.ZSTD
    
    def compress_files(
        self,
        files: list[FileInfo],
        output_stream: BinaryIO,
        progress_callback: Optional[ProgressCallback] = None
    ) -> int:
        """使用 Zstd 压缩文件"""
        try:
            total_bytes = 0
            processed_bytes = 0
            
            # 计算总字节数
            total_bytes = sum(f.size for f in files if not f.is_directory)
            
            with self._cctx.stream_writer(output_stream, closefd=False) as writer:
                for file_info in files:
                    if file_info.is_directory:
                        # 目录条目（只记录结构）
                        self._write_directory_entry(writer, file_info)
                        continue
                    
                    # 回调进度
                    if progress_callback:
                        progress_callback(processed_bytes, total_bytes, str(file_info.relative_path))
                    
                    # 写入文件头
                    self._write_file_header(writer, file_info)
                    
                    # 写入文件内容
                    if file_info.path.exists():
                        try:
                            with open(file_info.path, 'rb') as f:
                                while True:
                                    chunk = f.read(64 * 1024)  # 64KB 块
                                    if not chunk:
                                        break
                                    writer.write(chunk)
                        except (OSError, IOError) as e:
                            raise CompressionError(f"读取文件失败 {file_info.path}: {e}")
                    
                    processed_bytes += file_info.size
            
            return output_stream.tell() if hasattr(output_stream, 'tell') else processed_bytes
            
        except Exception as e:
            if isinstance(e, CompressionError):
                raise
            raise CompressionError(f"Zstd 压缩失败: {e}")
    
    def decompress_to_directory(
        self,
        input_stream: BinaryIO,
        output_dir: Path,
        progress_callback: Optional[ProgressCallback] = None
    ) -> int:
        """使用 Zstd 解压到目录"""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            decompressed_bytes = 0
            
            with self._dctx.stream_reader(input_stream) as reader:
                while True:
                    # 读取文件头
                    file_info = self._read_file_header(reader)
                    if not file_info:
                        break  # 结束
                    
                    if progress_callback:
                        progress_callback(decompressed_bytes, decompressed_bytes + file_info.size, 
                                        str(file_info.relative_path))
                    
                    if file_info.is_directory:
                        # 创建目录
                        dir_path = output_dir / file_info.relative_path
                        dir_path.mkdir(parents=True, exist_ok=True)
                    else:
                        # 创建文件
                        file_path = output_dir / file_info.relative_path
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(file_path, 'wb') as f:
                            remaining = file_info.size
                            while remaining > 0:
                                chunk_size = min(64 * 1024, remaining)
                                chunk = reader.read(chunk_size)
                                if not chunk:
                                    break
                                f.write(chunk)
                                remaining -= len(chunk)
                        
                        # 设置修改时间
                        import os
                        os.utime(file_path, (file_info.mtime, file_info.mtime))
                    
                    decompressed_bytes += file_info.size
            
            return decompressed_bytes
            
        except Exception as e:
            if isinstance(e, CompressionError):
                raise
            raise DecompressionError(f"Zstd 解压失败: {e}") from e
    
    def _write_file_header(self, writer: BinaryIO, file_info: FileInfo) -> None:
        """写入文件头信息"""
        # 简化的文件头格式：
        # [path_len:4][path:utf8][size:8][mtime:8][is_dir:1]
        path_bytes = str(file_info.relative_path).replace('\\', '/').encode('utf-8')
        
        writer.write(len(path_bytes).to_bytes(4, 'little'))  # 路径长度
        writer.write(path_bytes)  # 路径
        writer.write(file_info.size.to_bytes(8, 'little'))  # 文件大小
        writer.write(int(file_info.mtime).to_bytes(8, 'little'))  # 修改时间
        writer.write(b'\x00' if not file_info.is_directory else b'\x01')  # 是否目录
    
    def _write_directory_entry(self, writer: BinaryIO, dir_info: FileInfo) -> None:
        """写入目录条目"""
        self._write_file_header(writer, dir_info)
    
    def _read_file_header(self, reader: BinaryIO) -> Optional[FileInfo]:
        """读取文件头信息"""
        try:
            # 读取路径长度
            path_len_bytes = reader.read(4)
            if len(path_len_bytes) != 4:
                return None  # EOF
            
            path_len = int.from_bytes(path_len_bytes, 'little')
            if path_len <= 0 or path_len > 4096:  # 路径长度限制
                return None
            
            # 读取路径
            path_bytes = reader.read(path_len)
            if len(path_bytes) != path_len:
                return None
            
            path = path_bytes.decode('utf-8')
            
            # 读取大小和时间
            size_bytes = reader.read(8)
            mtime_bytes = reader.read(8)
            is_dir_byte = reader.read(1)
            
            if len(size_bytes) != 8 or len(mtime_bytes) != 8 or len(is_dir_byte) != 1:
                return None
            
            size = int.from_bytes(size_bytes, 'little')
            mtime = int.from_bytes(mtime_bytes, 'little')
            is_directory = is_dir_byte[0] != 0
            
            return FileInfo(
                path=Path(path),  # 这里只是占位，不使用绝对路径
                relative_path=Path(path),
                size=size,
                mtime=float(mtime),
                is_directory=is_directory
            )
            
        except (UnicodeDecodeError, ValueError):
            return None


class ZipCompressor(Compressor):
    """Zip 压缩器（回退选项）"""
    
    def __init__(self, level: int = 6):
        self.level = min(9, max(1, level))  # Zip 压缩级别限制在 1-9
    
    def get_algorithm(self) -> CompressionAlgorithm:
        return CompressionAlgorithm.ZIP
    
    def compress_files(
        self,
        files: list[FileInfo],
        output_stream: BinaryIO,
        progress_callback: Optional[ProgressCallback] = None
    ) -> int:
        """使用 Zip 压缩文件"""
        try:
            total_bytes = sum(f.size for f in files if not f.is_directory)
            processed_bytes = 0
            
            with zipfile.ZipFile(output_stream, 'w', zipfile.ZIP_DEFLATED, compresslevel=self.level) as zf:
                for file_info in files:
                    if progress_callback:
                        progress_callback(processed_bytes, total_bytes, str(file_info.relative_path))
                    
                    archive_path = str(file_info.relative_path).replace('\\', '/')
                    
                    if file_info.is_directory:
                        # 添加目录条目
                        if not archive_path.endswith('/'):
                            archive_path += '/'
                        zf.writestr(zipfile.ZipInfo(archive_path), '')
                    else:
                        # 添加文件
                        if file_info.path.exists():
                            try:
                                zf.write(file_info.path, archive_path)
                                processed_bytes += file_info.size
                            except (OSError, IOError) as e:
                                raise CompressionError(f"添加文件到 Zip 失败 {file_info.path}: {e}")
            
            return output_stream.tell() if hasattr(output_stream, 'tell') else processed_bytes
            
        except Exception as e:
            if isinstance(e, CompressionError):
                raise
            raise CompressionError(f"Zip 压缩失败: {e}")
    
    def decompress_to_directory(
        self,
        input_stream: BinaryIO,
        output_dir: Path,
        progress_callback: Optional[ProgressCallback] = None
    ) -> int:
        """使用 Zip 解压到目录"""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            decompressed_bytes = 0
            
            with zipfile.ZipFile(input_stream, 'r') as zf:
                total_size = sum(info.file_size for info in zf.infolist())
                
                for info in zf.infolist():
                    if progress_callback:
                        progress_callback(decompressed_bytes, total_size, info.filename)
                    
                    # 安全检查：防止目录穿越攻击
                    if '..' in info.filename or info.filename.startswith('/'):
                        continue
                    
                    extract_path = output_dir / info.filename
                    
                    if info.is_dir():
                        # 创建目录
                        extract_path.mkdir(parents=True, exist_ok=True)
                    else:
                        # 提取文件
                        extract_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with zf.open(info) as src, open(extract_path, 'wb') as dst:
                            while True:
                                chunk = src.read(64 * 1024)
                                if not chunk:
                                    break
                                dst.write(chunk)
                        
                        decompressed_bytes += info.file_size
            
            return decompressed_bytes
            
        except Exception as e:
            if isinstance(e, CompressionError):
                raise
            raise DecompressionError(f"Zip 解压失败: {e}") from e


class CompressorFactory:
    """压缩器工厂"""
    
    @staticmethod
    def create_compressor(
        algorithm: CompressionAlgorithm, 
        level: int = 10, 
        fallback_to_zip: bool = True
    ) -> Compressor:
        """创建压缩器
        
        Args:
            algorithm: 压缩算法
            level: 压缩级别
            fallback_to_zip: 是否自动回退到 Zip
            
        Returns:
            Compressor: 压缩器实例
            
        Raises:
            CompressionError: 创建失败
        """
        if algorithm == CompressionAlgorithm.ZSTD:
            if ZSTD_AVAILABLE:
                return ZstdCompressor(level)
            elif fallback_to_zip:
                # 自动回退到 Zip
                return ZipCompressor(min(9, level))
            else:
                raise CompressionError("Zstd 不可用且未启用自动回退")
        
        elif algorithm == CompressionAlgorithm.ZIP:
            return ZipCompressor(level)
        
        else:
            raise CompressionError(f"不支持的压缩算法: {algorithm}")
    
    @staticmethod
    def get_available_algorithms() -> list[CompressionAlgorithm]:
        """获取可用的压缩算法列表"""
        algorithms = [CompressionAlgorithm.ZIP]  # Zip 总是可用
        
        if ZSTD_AVAILABLE:
            algorithms.insert(0, CompressionAlgorithm.ZSTD)  # Zstd 优先
        
        return algorithms