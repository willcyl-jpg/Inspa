"""
头部构建步骤模块

负责构建安装器头部数据。
映射需求：FR-BLD-004, FR-BLD-014, FR-BLD-015
"""

from ...utils import format_size
from ...utils.logging import info, success, debug, error, LogStage
from inspa.build.build_context import BuildContext, BuildError
from .build_step import BuildStep
from inspa.build.header import HeaderBuilder, HashCalculator


class HeaderBuildingStep(BuildStep):
    """头部构建步骤"""

    def __init__(self, builder_version: str = "0.1.0"):
        super().__init__("header", "构建安装器头部数据")
        self.header_builder = HeaderBuilder(builder_version)

    def get_progress_range(self) -> tuple[int, int]:
        return (60, 70)

    def execute(self, context: BuildContext) -> None:
        """构建头部数据"""
        if not context.files or not context.compressed_data or not context.actual_algorithm:
            raise BuildError("缺少必要的构建数据")

        info("构建头部数据", stage=LogStage.HEADER)

        try:
            if context.progress_callback:
                progress_start, progress_end = self.get_progress_range()
                context.progress_callback("构建头部", progress_start, 100, "生成安装器头部...")

            # 计算压缩数据哈希
            archive_hash = HashCalculator.hash_data(context.compressed_data)

            from ...config.schema import CompressionAlgorithm
            compression_enum = CompressionAlgorithm(context.actual_algorithm)

            # 构建头部
            original_size = sum(f.size for f in context.files if not f.is_directory)
            compressed_size = len(context.compressed_data)
            header_dict = self.header_builder.build_header(
                config=context.config,
                files=context.files,
                compression_algo=compression_enum,
                archive_hash=archive_hash,
                original_size=original_size,
                compressed_size=compressed_size,
            )

            # 序列化为JSON
            header_bytes = self.header_builder.serialize_header(header_dict)
            context.header_data = header_bytes

            if context.progress_callback:
                progress_start, progress_end = self.get_progress_range()
                context.progress_callback("构建头部", progress_end, 100, "头部数据生成完成")

            success(f"头部数据构建完成 - 大小: {format_size(len(header_bytes))}", stage=LogStage.HEADER)
            debug(f"头部预览: {header_bytes[:120]!r}...", stage=LogStage.HEADER)

        except Exception as e:
            error(f"构建头部失败: {e}", stage=LogStage.HEADER)
            raise BuildError(f"构建头部失败: {e}") from e