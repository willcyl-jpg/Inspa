"""构建服务模块

提供安装器构建的核心功能。
"""

from .builder import Builder, BuildError
from .collector import FileCollector, FileInfo, collect_files
from .compressor import (
    Compressor, 
    CompressorFactory, 
    CompressionError,
    ZstdCompressor,
    ZipCompressor,
)
from .header import (
    HeaderBuilder, 
    HeaderData, 
    HashCalculator,
    HashInfo,
    BuildInfo,
    calculate_archive_hash,
)

__all__ = [
    # 主构建器
    "Builder", 
    "BuildError",
    
    # 文件收集
    "FileCollector",
    "FileInfo",
    "collect_files",
    
    # 压缩相关
    "Compressor",
    "CompressorFactory", 
    "CompressionError",
    "ZstdCompressor",
    "ZipCompressor",
    
    # 头部构建
    "HeaderBuilder",
    "HeaderData",
    "HashCalculator",
    "HashInfo", 
    "BuildInfo",
    "calculate_archive_hash",
]