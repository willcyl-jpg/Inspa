"""
文件压缩步骤模块

负责压缩收集到的文件数据。
映射需求：FR-BLD-004, FR-BLD-014, FR-BLD-015
"""

import io
from pathlib import Path
from typing import Optional

from ...utils import format_size
from ...utils.logging import info, success, warning, debug, error, LogStage
from inspa.build.build_context import BuildContext, BuildError
from .build_step import BuildStep
from inspa.build.compressor import CompressorFactory, CompressionError


class CompressionStep(BuildStep):
    """文件压缩步骤"""

    def __init__(self):
        super().__init__("compress", "压缩文件数据")

    def get_progress_range(self) -> tuple[int, int]:
        return (20, 60)

    def execute(self, context: BuildContext) -> None:
        """压缩文件"""
        if not context.files:
            raise BuildError("文件列表为空，无法进行压缩")

        info(f"压缩文件 - 算法: {context.config.compression.algo.value}, 级别: {context.config.compression.level}", stage=LogStage.COMPRESS)

        try:
            # 创建压缩器
            compressor = CompressorFactory.create_compressor(
                context.config.compression.algo,
                context.config.compression.level,
                context.config.compression.fallback_to_zip
            )

            actual_algorithm = compressor.get_algorithm().value
            context.actual_algorithm = actual_algorithm

            if actual_algorithm != context.config.compression.algo.value:
                warning(f"压缩算法回退: {context.config.compression.algo.value} -> {actual_algorithm}", stage=LogStage.COMPRESS)

            if context.progress_callback:
                progress_start, progress_end = self.get_progress_range()
                context.progress_callback("压缩文件", progress_start, 100, "开始压缩...")

            # 压缩到内存
            output_buffer = io.BytesIO()

            def compress_progress(current: int, total: int, current_file: Optional[str] = None) -> None:
                if context.progress_callback and total > 0:
                    progress_start, progress_end = self.get_progress_range()
                    # 在压缩阶段内部报告进度 (0-100%)
                    file_progress = int((current / total) * (progress_end - progress_start)) + progress_start

                    message = "压缩中..."
                    if current_file:
                        # 只显示文件名，不显示完整路径
                        filename = Path(current_file).name if current_file else ""
                        message = f"压缩: {filename}"

                    context.progress_callback("压缩文件", file_progress, 100, message)

            compressed_size = compressor.compress_files(context.files, output_buffer, compress_progress)

            compressed_data = output_buffer.getvalue()
            context.compressed_data = compressed_data
            context.build_stats['compressed_size'] = len(compressed_data)

            original_size = sum(f.size for f in context.files if not f.is_directory)
            compression_ratio = (1 - len(compressed_data) / max(1, original_size)) * 100
            context.build_stats['compression_ratio'] = compression_ratio

            if context.progress_callback:
                progress_start, progress_end = self.get_progress_range()
                context.progress_callback("压缩文件", progress_end, 100, f"压缩完成，大小: {format_size(len(compressed_data))}")

            success("压缩完成", stage=LogStage.COMPRESS)
            info(f"  算法: {actual_algorithm}")
            info(f"  原始大小: {format_size(original_size)}")
            info(f"  压缩大小: {format_size(len(compressed_data))}")
            info(f"  压缩率: {compression_ratio:.1f}%")
            debug(f"压缩数据长度={len(compressed_data)} bytes", stage=LogStage.COMPRESS)

        except CompressionError as e:
            error(f"压缩失败: {e}", stage=LogStage.COMPRESS)
            raise BuildError(f"压缩失败: {e}") from e
        except Exception as e:
            error(f"压缩过程异常: {e}", stage=LogStage.COMPRESS)
            raise BuildError(f"压缩过程异常: {e}") from e