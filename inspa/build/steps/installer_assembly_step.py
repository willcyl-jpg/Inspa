"""
安装器组装步骤模块

负责最终组装安装器文件。
映射需求：FR-BLD-004, FR-BLD-014, FR-BLD-015
"""

import struct
from pathlib import Path

from ...utils import ensure_directory, format_size
from ...utils.logging import info, success, debug, error, LogStage
from inspa.build.build_context import BuildContext, BuildError
from .build_step import BuildStep
from inspa.build.header import HashCalculator

# 新的快速定位 Footer 魔术字节 (8 bytes)
FOOTER_MAGIC = b'INSPAF01'


class InstallerAssemblyStep(BuildStep):
    """安装器组装步骤"""

    def __init__(self):
        super().__init__("assemble", "组装最终安装器")

    def get_progress_range(self) -> tuple[int, int]:
        return (85, 100)

    def execute(self, context: BuildContext) -> None:
        """组装最终安装器"""
        if not context.header_data or not context.compressed_data or not context.stub_data:
            raise BuildError("缺少必要的构建数据")

        info(f"组装安装器: {context.output_path}", stage=LogStage.WRITE)

        try:
            if context.progress_callback:
                progress_start, progress_end = self.get_progress_range()
                context.progress_callback("组装文件", progress_start, 100, "写入最终文件...")

            # 确保输出目录存在
            ensure_directory(context.output_path.parent)

            # 预计算各段偏移
            stub_size = len(context.stub_data)
            header_len = len(context.header_data)
            header_offset = stub_size  # 指向 8 字节 header_len 字段开头
            compressed_offset = header_offset + 8 + header_len
            compressed_size = len(context.compressed_data)
            archive_hash = HashCalculator.hash_data(context.compressed_data)

            # Footer 结构: <8sQQQQ32s>
            # magic, header_offset, header_len, compressed_offset, compressed_size, archive_hash(32字节)
            debug(
                f"Offsets 计算: stub_size={stub_size} header_offset={header_offset} header_len={header_len} compressed_offset={compressed_offset} compressed_size={compressed_size}",
                stage=LogStage.WRITE
            )
            footer_struct = struct.pack(
                '<8sQQQQ32s',
                FOOTER_MAGIC,
                header_offset,
                header_len,
                compressed_offset,
                compressed_size,
                bytes.fromhex(archive_hash)
            )

            # 创建最终文件
            with open(context.output_path, 'wb') as f:
                # 1. 写入 runtime stub
                f.write(context.stub_data)
                # 2. 写入头部长度 (8 字节 LE)
                f.write(header_len.to_bytes(8, 'little'))
                # 3. 写入头部数据
                f.write(context.header_data)
                # 4. 写入压缩数据
                f.write(context.compressed_data)
                # 5. 旧格式尾部哈希 (供旧解析器扫描验证) 32 字节
                f.write(bytes.fromhex(archive_hash))
                # 6. 新增 Footer 72 字节
                f.write(footer_struct)

            final_size = context.output_path.stat().st_size

            if context.progress_callback:
                progress_start, progress_end = self.get_progress_range()
                context.progress_callback("组装文件", progress_end, 100, f"完成，大小 {format_size(final_size)}")

            success(f"安装器组装完成 - 大小: {format_size(final_size)}", stage=LogStage.WRITE)

        except Exception as e:
            error(f"组装安装器失败: {e}", stage=LogStage.WRITE)
            raise BuildError(f"组装安装器失败: {e}") from e