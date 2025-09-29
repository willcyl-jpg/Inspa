"""
构建器主类

负责整个构建流程的协调，使用管道模式组织构建步骤。
映射需求：FR-BLD-004, FR-BLD-014, FR-BLD-015
"""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, List

from ..config.schema import InspaConfig
from ..utils.logging import info, success, error, LogStage
from .build_pipeline import BuildPipeline
from .build_context import BuildError

# 进度回调类型
ProgressCallback = Callable[[str, int, int, str], None]


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

    使用管道模式协调构建步骤，提供统一的构建接口。
    """

    def __init__(self, builder_version: str = "0.1.0"):
        """初始化构建器

        Args:
            builder_version: 构建器版本号
        """
        self.builder_version = builder_version
        self.pipeline = BuildPipeline(builder_version)
    
    def build(
        self,
        config: InspaConfig,
        output_path: Path,
        progress_callback: Optional[ProgressCallback] = None,
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
        try:
            # 执行构建管道
            context = self.pipeline.execute(config, output_path, progress_callback)

            # 转换结果格式
            build_time = context.build_stats['end_time'] - context.build_stats['start_time']
            compression_ratio = context.build_stats.get('compression_ratio', 0.0)

            result = BuildResult(
                success=True,
                output_path=output_path,
                output_size=output_path.stat().st_size if output_path.exists() else None,
                build_time=build_time,
                compression_ratio=compression_ratio
            )

            return result

        except BuildError as e:
            # 构建失败，返回失败结果
            return BuildResult(
                success=False,
                error=str(e)
            )
    
    def get_build_stats(self) -> dict:
        """获取构建统计信息

        注意：此方法在新架构中已不推荐使用，
        建议直接从BuildResult中获取统计信息。
        """
        # 返回空的统计信息以保持向后兼容
        return {
            'start_time': 0,
            'end_time': 0,
            'total_files': 0,
            'total_size': 0,
            'compressed_size': 0,
            'compression_ratio': 0.0,
        }

    def get_pipeline(self) -> BuildPipeline:
        """获取构建管道，用于自定义构建流程"""
        return self.pipeline

    def validate_build_pipeline(self) -> List[str]:
        """验证构建管道的完整性

        Returns:
            List[str]: 验证错误列表，空列表表示验证通过
        """
        return self.pipeline.validate_pipeline()

