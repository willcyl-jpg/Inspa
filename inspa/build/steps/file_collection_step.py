"""
文件收集步骤模块

负责收集要打包的文件。
映射需求：FR-BLD-004, FR-BLD-014, FR-BLD-015
"""

from pathlib import Path

from ...utils import format_size
from ...utils.logging import info, success, warning, debug, error, LogStage
from inspa.build.build_context import BuildContext, BuildError
from .build_step import BuildStep
from inspa.build.collector import FileCollector, FileInfo


class FileCollectionStep(BuildStep):
    """文件收集步骤"""

    def __init__(self):
        super().__init__("collect", "收集要打包的文件")
        self.collector = FileCollector()

    def get_progress_range(self) -> tuple[int, int]:
        return (0, 20)

    def execute(self, context: BuildContext) -> None:
        """收集要打包的文件"""
        info("收集文件", stage=LogStage.COLLECT)

        try:
            all_files = []

            # 遍历所有输入路径
            for i, input_path in enumerate(context.config.inputs):
                if context.progress_callback:
                    progress_start, progress_end = self.get_progress_range()
                    current_progress = progress_start + int((i / len(context.config.inputs)) * (progress_end - progress_start))
                    context.progress_callback("收集文件", current_progress, 100, f"扫描: {input_path.path}")

                source_path = Path(input_path.path)

                if not source_path.exists():
                    warning(f"输入路径不存在: {source_path}", stage=LogStage.COLLECT)
                    continue

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
                    dir_files = self.collector.collect_files([input_path], exclude_patterns=context.config.exclude or [])
                    all_files.extend(dir_files)

            # 统计信息
            total_files = len([f for f in all_files if not f.is_directory])
            total_size = sum(f.size for f in all_files if not f.is_directory)

            context.build_stats['total_files'] = total_files
            context.build_stats['total_size'] = total_size
            context.files = all_files

            if context.progress_callback:
                progress_start, progress_end = self.get_progress_range()
                context.progress_callback("收集文件", progress_end, 100, f"找到 {len(all_files)} 个文件")

            success("文件收集完成", stage=LogStage.COLLECT)
            info(f"  文件数量: {total_files}")
            info(f"  总大小: {format_size(total_size)}")

            # 在 DEBUG 级别输出前 20 个文件用于诊断
            for idx, f in enumerate([ff for ff in all_files if not ff.is_directory][:20]):
                debug(f"文件[{idx}]: {f.relative_path} size={format_size(f.size)} mtime={int(f.mtime)}", stage=LogStage.COLLECT)
            if total_files > 20:
                debug(f"... 还有 {total_files - 20} 个文件未列出", stage=LogStage.COLLECT)

        except Exception as e:
            error(f"文件收集失败: {e}", stage=LogStage.COLLECT)
            raise BuildError(f"文件收集失败: {e}") from e