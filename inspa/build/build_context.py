"""
构建上下文模块

定义构建过程中的共享数据结构和异常类。
映射需求：FR-BLD-004, FR-BLD-014, FR-BLD-015
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Any, Dict, List, TYPE_CHECKING

from ..config.schema import InspaConfig

if TYPE_CHECKING:
    from .collector import FileInfo

# 进度回调类型
ProgressCallback = Callable[[str, int, int, str], None]


@dataclass
class BuildContext:
    """构建上下文，包含构建过程中的共享数据"""
    config: InspaConfig
    output_path: Path
    progress_callback: Optional[ProgressCallback] = None

    # 构建过程中生成的数据
    files: Optional[List['FileInfo']] = None
    compressed_data: Optional[bytes] = None
    actual_algorithm: Optional[str] = None
    header_data: Optional[bytes] = None
    stub_data: Optional[bytes] = None

    # 统计信息
    build_stats: Dict[str, Any] = None  # type: ignore

    def __post_init__(self):
        if self.build_stats is None:
            self.build_stats = {
                'start_time': 0,
                'end_time': 0,
                'total_files': 0,
                'total_size': 0,
                'compressed_size': 0,
                'compression_ratio': 0.0,
            }


class BuildError(Exception):
    """构建错误"""
    pass