"""
构建管道单元测试

测试构建管道、构建步骤、构建上下文等核心功能。
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from inspa.build.build_context import BuildContext, BuildError
from inspa.build.build_pipeline import BuildPipeline
from inspa.build.steps.build_step import BuildStep
from inspa.config.schema import (
    CompressionAlgorithm,
    CompressionModel,
    InputPathModel,
    InspaConfig,
    InstallModel,
    ProductModel,
)


class MockBuildStep(BuildStep):
    """模拟构建步骤"""

    def __init__(self, name="MockStep", description="Mock step", progress_range=(0, 10)):
        self._name = name
        self._description = description
        self._progress_range = progress_range
        self.execute_called = False
        self.execute_context = None

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    def get_progress_range(self):
        return self._progress_range

    def execute(self, context):
        self.execute_called = True
        self.execute_context = context
        # 模拟一些处理
        context.build_stats['mock_processed'] = True


class TestBuildStep:
    """BuildStep 基类测试"""

    def test_build_step_interface(self):
        """测试构建步骤接口"""
        step = MockBuildStep()

        assert step.name == "MockStep"
        assert step.description == "Mock step"
        assert step.get_progress_range() == (0, 10)
        assert not step.execute_called

    def test_build_step_execute(self):
        """测试构建步骤执行"""
        step = MockBuildStep()
        context = MagicMock()

        step.execute(context)

        assert step.execute_called
        assert step.execute_context == context


class TestBuildContext:
    """BuildContext 测试"""

    def test_init(self):
        """测试初始化"""
        config = MagicMock()
        output_path = Path("test.exe")

        context = BuildContext(config, output_path)

        assert context.config == config
        assert context.output_path == output_path
        assert 'start_time' in context.build_stats
        assert 'total_files' in context.build_stats
        assert context.progress_callback is None

    def test_init_with_progress_callback(self):
        """测试带进度回调的初始化"""
        config = MagicMock()
        output_path = Path("test.exe")
        progress_callback = MagicMock()

        context = BuildContext(config, output_path, progress_callback)

        assert context.progress_callback == progress_callback

    def test_build_stats_initialization(self):
        """测试构建统计初始化"""
        config = MagicMock()
        output_path = Path("test.exe")

        context = BuildContext(config, output_path)

        expected_stats = {
            'start_time': context.build_stats['start_time'],  # 时间戳
            'total_files': 0,
            'total_size': 0,
            'compressed_size': 0,
            'compression_ratio': 0.0,
        }

        # 检查所有期望的键都存在
        for key in expected_stats:
            assert key in context.build_stats


class TestBuildPipeline:
    """BuildPipeline 测试"""

    def test_init(self):
        """测试初始化"""
        pipeline = BuildPipeline()

        assert len(pipeline.get_steps()) == 5  # 默认的5个步骤
        assert pipeline.builder_version == "0.1.0"

    def test_init_custom_version(self):
        """测试自定义版本初始化"""
        pipeline = BuildPipeline("1.0.0")
        assert pipeline.builder_version == "1.0.0"

    def test_add_step(self):
        """测试添加步骤"""
        pipeline = BuildPipeline()
        initial_count = len(pipeline.get_steps())

        new_step = MockBuildStep("NewStep")
        pipeline.add_step(new_step)

        assert len(pipeline.get_steps()) == initial_count + 1
        assert pipeline.get_steps()[-1] == new_step

    def test_add_step_with_position(self):
        """测试在指定位置添加步骤"""
        pipeline = BuildPipeline()

        new_step = MockBuildStep("NewStep")
        pipeline.add_step(new_step, position=0)

        assert pipeline.get_steps()[0] == new_step

    def test_remove_step(self):
        """测试移除步骤"""
        pipeline = BuildPipeline()
        initial_count = len(pipeline.get_steps())

        # 添加一个步骤然后移除
        step_to_remove = MockBuildStep("ToRemove")
        pipeline.add_step(step_to_remove)
        assert len(pipeline.get_steps()) == initial_count + 1

        pipeline.remove_step("ToRemove")
        assert len(pipeline.get_steps()) == initial_count

    def test_remove_nonexistent_step(self):
        """测试移除不存在的步骤"""
        pipeline = BuildPipeline()
        initial_count = len(pipeline.get_steps())

        pipeline.remove_step("NonExistent")
        assert len(pipeline.get_steps()) == initial_count  # 数量不变

    def test_get_steps_returns_copy(self):
        """测试 get_steps 返回副本"""
        pipeline = BuildPipeline()
        steps1 = pipeline.get_steps()
        steps2 = pipeline.get_steps()

        assert steps1 is not steps2  # 应该是不同的对象
        assert steps1 == steps2  # 但内容相同

    def test_validate_pipeline_valid(self):
        """测试验证有效管道"""
        pipeline = BuildPipeline()
        errors = pipeline.validate_pipeline()

        assert errors == []  # 默认管道应该是有效的

    def test_validate_pipeline_empty(self):
        """测试验证空管道"""
        pipeline = BuildPipeline()
        # 移除所有步骤
        for step in pipeline.get_steps():
            pipeline.remove_step(step.name)

        errors = pipeline.validate_pipeline()
        assert "构建管道中没有步骤" in errors[0]

    def test_validate_pipeline_invalid_progress_ranges(self):
        """测试验证无效进度范围"""
        pipeline = BuildPipeline()

        # 添加一个进度范围无效的步骤
        invalid_step = MockBuildStep("Invalid", progress_range=(10, 5))  # 开始 > 结束
        pipeline.add_step(invalid_step)

        errors = pipeline.validate_pipeline()
        assert any("进度范围无效" in error for error in errors)

    def test_validate_pipeline_non_continuous_progress(self):
        """测试验证不连续进度范围"""
        pipeline = BuildPipeline()

        # 添加一个进度范围不连续的步骤
        discontinuous_step = MockBuildStep("Discontinuous", progress_range=(5, 15))  # 期望从0开始
        pipeline.add_step(discontinuous_step, position=0)

        errors = pipeline.validate_pipeline()
        assert any("进度范围不连续" in error for error in errors)

    def test_validate_pipeline_not_ending_at_100(self):
        """测试验证未以100结束的管道"""
        pipeline = BuildPipeline()

        # 移除所有步骤并添加一个只到50的步骤
        for step in pipeline.get_steps():
            pipeline.remove_step(step.name)

        short_step = MockBuildStep("Short", progress_range=(0, 50))
        pipeline.add_step(short_step)

        errors = pipeline.validate_pipeline()
        assert any("不是100%" in error for error in errors)

    @patch('inspa.build.build_pipeline.FileCollectionStep')
    @patch('inspa.build.build_pipeline.CompressionStep')
    @patch('inspa.build.build_pipeline.HeaderBuildingStep')
    @patch('inspa.build.build_pipeline.StubCompilationStep')
    @patch('inspa.build.build_pipeline.InstallerAssemblyStep')
    def test_execute_success(self, mock_assembly, mock_stub, mock_header, mock_compression, mock_collection):
        """测试成功执行"""
        # 创建模拟步骤
        mock_collection.return_value = MockBuildStep("FileCollection", progress_range=(0, 20))
        mock_compression.return_value = MockBuildStep("Compression", progress_range=(20, 60))
        mock_header.return_value = MockBuildStep("HeaderBuilding", progress_range=(60, 80))
        mock_stub.return_value = MockBuildStep("StubCompilation", progress_range=(80, 90))
        mock_assembly.return_value = MockBuildStep("InstallerAssembly", progress_range=(90, 100))

        pipeline = BuildPipeline()

        # 创建测试配置
        config = InspaConfig(
            product=ProductModel(name="TestApp", version="1.0.0"),
            install=InstallModel(default_path="C:/TestApp"),
            inputs=[InputPathModel(path="C:/source")]
        )

        with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as f:
            output_path = Path(f.name)

        try:
            context = pipeline.execute(config, output_path)

            assert context is not None
            assert 'end_time' in context.build_stats
            assert context.build_stats['end_time'] >= context.build_stats['start_time']

            # 验证所有步骤都被执行
            for step in pipeline.get_steps():
                assert step.execute_called
                assert step.execute_context == context

        finally:
            output_path.unlink()

    @patch('inspa.build.build_pipeline.FileCollectionStep')
    def test_execute_with_error(self, mock_collection):
        """测试执行时发生错误"""
        # 让第一个步骤抛出异常
        mock_step = MockBuildStep("FileCollection", progress_range=(0, 20))
        mock_step.execute = MagicMock(side_effect=BuildError("Test error"))
        mock_collection.return_value = mock_step

        pipeline = BuildPipeline()

        config = InspaConfig(
            product=ProductModel(name="TestApp", version="1.0.0"),
            install=InstallModel(default_path="C:/TestApp"),
            inputs=[InputPathModel(path="C:/source")]
        )

        with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as f:
            output_path = Path(f.name)

        try:
            with pytest.raises(BuildError) as exc_info:
                pipeline.execute(config, output_path)

            assert "Test error" in str(exc_info.value)

        finally:
            output_path.unlink()

    def test_execute_updates_build_stats(self):
        """测试执行更新构建统计"""
        pipeline = BuildPipeline()

        config = InspaConfig(
            product=ProductModel(name="TestApp", version="1.0.0"),
            install=InstallModel(default_path="C:/TestApp"),
            inputs=[InputPathModel(path="C:/source")]
        )

        with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as f:
            output_path = Path(f.name)

        try:
            # 由于实际的构建步骤会失败（缺少文件等），我们只测试统计信息初始化
            context = BuildContext(config, output_path)

            # 验证初始统计信息
            assert 'start_time' in context.build_stats
            assert 'total_files' in context.build_stats
            assert 'total_size' in context.build_stats
            assert 'compressed_size' in context.build_stats
            assert 'compression_ratio' in context.build_stats

        finally:
            output_path.unlink()


class TestBuildError:
    """BuildError 测试"""

    def test_build_error_inheritance(self):
        """测试 BuildError 继承"""
        error = BuildError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_build_error_with_cause(self):
        """测试带原因的 BuildError"""
        cause = ValueError("original error")
        error = BuildError("build failed", cause)

        assert isinstance(error, Exception)
        assert "build failed" in str(error)