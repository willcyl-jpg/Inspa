"""
构建管道模块

使用管道模式协调构建步骤的执行。
映射需求：FR-BLD-004, FR-BLD-014, FR-BLD-015
"""

import time
from typing import List, Optional

from ..config.schema import InspaConfig
from ..utils.logging import info, success, error, LogStage
from .build_context import BuildContext, BuildError, ProgressCallback
from .steps.build_step import BuildStep
from .steps.file_collection_step import FileCollectionStep
from .steps.compression_step import CompressionStep
from .steps.header_building_step import HeaderBuildingStep
from .steps.stub_compilation_step import StubCompilationStep
from .steps.installer_assembly_step import InstallerAssemblyStep


class BuildPipeline:
    """构建管道，负责协调构建步骤的执行"""

    def __init__(self, builder_version: str = "0.1.0"):
        """初始化构建管道"""
        self.builder_version = builder_version
        self._steps: List[BuildStep] = []

        # 初始化默认构建步骤
        self._init_default_steps()

    def _init_default_steps(self):
        """初始化默认的构建步骤"""
        self._steps = [
            FileCollectionStep(),
            CompressionStep(),
            HeaderBuildingStep(self.builder_version),
            StubCompilationStep(),
            InstallerAssemblyStep(),
        ]

    def add_step(self, step: BuildStep, position: Optional[int] = None):
        """添加构建步骤"""
        if position is None:
            self._steps.append(step)
        else:
            self._steps.insert(position, step)

    def remove_step(self, step_name: str):
        """移除构建步骤"""
        self._steps = [step for step in self._steps if step.name != step_name]

    def get_steps(self) -> List[BuildStep]:
        """获取所有构建步骤"""
        return self._steps.copy()

    def execute(
        self,
        config: InspaConfig,
        output_path,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> BuildContext:
        """执行构建管道

        Args:
            config: 配置对象
            output_path: 输出文件路径
            progress_callback: 进度回调函数

        Returns:
            BuildContext: 构建上下文，包含所有构建结果

        Raises:
            BuildError: 构建失败
        """
        # 创建构建上下文
        context = BuildContext(
            config=config,
            output_path=output_path,
            progress_callback=progress_callback,
        )

        context.build_stats['start_time'] = time.time()

        try:
            info(f"开始构建安装器: {output_path}", stage=LogStage.BUILD)
            debug_info = f"构建配置: algorithm={config.compression.algo.value} level={config.compression.level} inputs={len(config.inputs)}"
            from ..utils.logging import debug
            debug(debug_info, stage=LogStage.BUILD)

            # 依次执行每个构建步骤
            for step in self._steps:
                info(f"执行步骤: {step.description}", stage=LogStage.BUILD)
                step.execute(context)

            # 计算最终统计信息
            context.build_stats['end_time'] = time.time()
            build_time = context.build_stats['end_time'] - context.build_stats['start_time']

            original_size = context.build_stats.get('total_size', 0)
            compressed_size = context.build_stats.get('compressed_size', 0)
            compression_ratio = (1 - compressed_size / max(1, original_size)) * 100 if original_size > 0 else 0.0

            # 构建成功
            success(f"安装器构建成功: {output_path}", stage=LogStage.BUILD)
            info(f"构建时间: {build_time:.1f}秒")
            from ..utils import format_size
            if 'total_size' in context.build_stats:
                info(f"原始大小: {format_size(original_size)}")
            if 'compressed_size' in context.build_stats:
                info(f"压缩大小: {format_size(compressed_size)}")
            info(f"最终大小: {format_size(output_path.stat().st_size)}")
            info(f"压缩率: {compression_ratio:.1f}%")

            return context

        except Exception as e:
            context.build_stats['end_time'] = time.time()
            build_time = context.build_stats['end_time'] - context.build_stats['start_time']

            error_msg = str(e)
            error(f"构建失败: {error_msg}", stage=LogStage.BUILD)

            # 重新抛出异常，让调用者处理
            raise BuildError(f"构建失败: {error_msg}") from e

    def validate_pipeline(self) -> List[str]:
        """验证构建管道的完整性

        Returns:
            List[str]: 验证错误列表，空列表表示验证通过
        """
        errors = []

        if not self._steps:
            errors.append("构建管道中没有步骤")
            return errors

        # 检查步骤的进度范围是否连续
        prev_end = 0
        for step in self._steps:
            start, end = step.get_progress_range()
            if start != prev_end:
                errors.append(f"步骤 '{step.name}' 的进度范围不连续: 期望起始 {prev_end}%, 实际 {start}%")
            if start >= end:
                errors.append(f"步骤 '{step.name}' 的进度范围无效: {start}% - {end}%")
            prev_end = end

        if prev_end != 100:
            errors.append(f"构建管道的总进度范围不是100%: {prev_end}%")

        return errors