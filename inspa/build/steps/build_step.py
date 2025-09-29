"""
构建步骤基类模块

定义构建步骤的抽象接口和基础功能。
映射需求：FR-BLD-004, FR-BLD-014, FR-BLD-015
"""

from abc import ABC, abstractmethod

from inspa.build.build_context import BuildContext


class BuildStep(ABC):
    """构建步骤抽象基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, context: BuildContext) -> None:
        """执行构建步骤"""
        pass

    @abstractmethod
    def get_progress_range(self) -> tuple[int, int]:
        """获取此步骤的进度范围 (start_percent, end_percent)"""
        pass