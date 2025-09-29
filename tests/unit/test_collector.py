"""
文件收集器单元测试

测试文件收集、排除规则、路径计算等核心功能。
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from inspa.build.collector import FileCollector, FileInfo, collect_files
from inspa.config.schema import InputPathModel


class TestFileInfo:
    """FileInfo 测试"""

    def test_file_info_creation(self):
        """测试 FileInfo 创建"""
        path = Path("C:/test/file.txt")
        relative_path = Path("file.txt")
        size = 1024
        mtime = 1234567890.0

        file_info = FileInfo(
            path=path,
            relative_path=relative_path,
            size=size,
            mtime=mtime,
            is_directory=False
        )

        assert file_info.path == path
        assert file_info.relative_path == relative_path
        assert file_info.size == size
        assert file_info.mtime == mtime
        assert file_info.is_directory is False

    def test_file_info_to_dict(self):
        """测试 FileInfo 转字典"""
        file_info = FileInfo(
            path=Path("C:/test/file.txt"),
            relative_path=Path("file.txt"),
            size=1024,
            mtime=1234567890.0,
            is_directory=False
        )

        data = file_info.to_dict()
        assert data["path"] == "file.txt"
        assert data["size"] == 1024
        assert data["mtime"] == 1234567890.0
        assert data["is_directory"] is False


class TestFileCollector:
    """FileCollector 测试"""

    def test_init(self):
        """测试初始化"""
        collector = FileCollector()
        assert collector.collected_files == []
        assert collector.excluded_patterns == []
        assert collector.total_size == 0

    def test_collect_files_single_file(self, tmp_path):
        """测试收集单个文件"""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        input_config = InputPathModel(path=str(test_file), recursive=True, preserve_structure=True)
        collector = FileCollector()
        files = collector.collect_files([input_config])

        assert len(files) == 1
        assert files[0].relative_path == Path("test.txt")
        assert files[0].size == len("test content")
        assert not files[0].is_directory

    def test_collect_files_directory(self, tmp_path):
        """测试收集目录"""
        # 创建测试目录结构
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("content3")

        input_config = InputPathModel(path=str(tmp_path), recursive=True, preserve_structure=True)
        collector = FileCollector()
        files = collector.collect_files([input_config])

        # 应该收集到 3 个文件和 1 个目录
        file_infos = [f for f in files if not f.is_directory]
        dir_infos = [f for f in files if f.is_directory]

        assert len(file_infos) == 3
        assert len(dir_infos) == 1

        # 检查文件
        file_names = {f.relative_path.name for f in file_infos}
        assert file_names == {"file1.txt", "file2.txt", "file3.txt"}

    def test_collect_files_non_recursive(self, tmp_path):
        """测试非递归收集"""
        # 创建测试目录结构
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.txt").write_text("content2")

        input_config = InputPathModel(path=str(tmp_path), recursive=False, preserve_structure=True)
        collector = FileCollector()
        files = collector.collect_files([input_config])

        # 应该只收集到根目录的文件和目录，不收集子目录内容
        file_infos = [f for f in files if not f.is_directory]
        assert len(file_infos) == 1
        assert file_infos[0].relative_path.name == "file1.txt"

    def test_collect_files_preserve_structure_false(self, tmp_path):
        """测试不保持目录结构"""
        # 创建测试目录结构
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file.txt").write_text("content")

        input_config = InputPathModel(path=str(tmp_path / "subdir"), recursive=True, preserve_structure=False)
        collector = FileCollector()
        files = collector.collect_files([input_config])

        # 文件应该直接放在根目录下
        assert len(files) == 1
        assert files[0].relative_path == Path("file.txt")

    def test_collect_files_exclude_patterns(self, tmp_path):
        """测试排除模式"""
        # 创建测试文件
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.log").write_text("content2")
        (tmp_path / "temp.tmp").write_text("content3")

        exclude_patterns = ["*.log", "*.tmp"]
        input_config = InputPathModel(path=str(tmp_path), recursive=True, preserve_structure=True)
        collector = FileCollector()
        files = collector.collect_files([input_config], exclude_patterns)

        # 应该只收集到 file1.txt
        file_infos = [f for f in files if not f.is_directory]
        assert len(file_infos) == 1
        assert file_infos[0].relative_path.name == "file1.txt"

    def test_collect_files_exclude_directory(self, tmp_path):
        """测试排除目录"""
        # 创建测试目录结构
        (tmp_path / "keep.txt").write_text("keep")
        (tmp_path / "exclude_dir").mkdir()
        (tmp_path / "exclude_dir" / "file.txt").write_text("exclude")

        exclude_patterns = ["exclude_dir/"]
        input_config = InputPathModel(path=str(tmp_path), recursive=True, preserve_structure=True)
        collector = FileCollector()
        files = collector.collect_files([input_config], exclude_patterns)

        # 应该只收集到 keep.txt
        file_infos = [f for f in files if not f.is_directory]
        assert len(file_infos) == 1
        assert file_infos[0].relative_path.name == "keep.txt"

    def test_collect_files_multiple_inputs(self, tmp_path):
        """测试多个输入路径"""
        # 创建两个目录
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        (dir1 / "file1.txt").write_text("content1")

        dir2 = tmp_path / "dir2"
        dir2.mkdir()
        (dir2 / "file2.txt").write_text("content2")

        inputs = [
            InputPathModel(path=str(dir1), recursive=True, preserve_structure=True),
            InputPathModel(path=str(dir2), recursive=True, preserve_structure=True)
        ]
        collector = FileCollector()
        files = collector.collect_files(inputs)

        file_infos = [f for f in files if not f.is_directory]
        assert len(file_infos) == 2
        file_names = {f.relative_path.name for f in file_infos}
        assert file_names == {"file1.txt", "file2.txt"}

    def test_collect_files_nonexistent_path(self):
        """测试不存在的路径"""
        input_config = InputPathModel(path="nonexistent/path", recursive=True, preserve_structure=True)
        collector = FileCollector()

        with pytest.raises(FileNotFoundError):
            collector.collect_files([input_config])

    def test_collect_files_invalid_path_type(self, tmp_path):
        """测试无效路径类型（既不是文件也不是目录）"""
        # 创建一个特殊文件（如果可能的话）
        # 在 Windows 上，我们可以尝试创建一个管道或类似的东西
        # 这里我们使用一个不存在的路径类型来模拟
        pass  # 跳过这个测试，因为在普通文件系统上难以创建既不是文件也不是目录的路径

    def test_get_statistics(self, tmp_path):
        """测试获取统计信息"""
        # 创建测试文件和目录
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("content3")

        input_config = InputPathModel(path=str(tmp_path), recursive=True, preserve_structure=True)
        collector = FileCollector()
        collector.collect_files([input_config])

        stats = collector.get_statistics()
        assert stats["total_files"] == 3
        assert stats["total_directories"] == 1
        assert stats["total_items"] == 4
        assert stats["total_size"] == len("content1") + len("content2") + len("content3")

    def test_filter_files_only(self, tmp_path):
        """测试只过滤文件"""
        # 创建测试文件和目录
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "subdir").mkdir()

        input_config = InputPathModel(path=str(tmp_path), recursive=True, preserve_structure=True)
        collector = FileCollector()
        collector.collect_files([input_config])

        files_only = collector.filter_files_only()
        assert len(files_only) == 1
        assert files_only[0].relative_path.name == "file1.txt"

    def test_filter_directories_only(self, tmp_path):
        """测试只过滤目录"""
        # 创建测试文件和目录
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "subdir").mkdir()

        input_config = InputPathModel(path=str(tmp_path), recursive=True, preserve_structure=True)
        collector = FileCollector()
        collector.collect_files([input_config])

        dirs_only = collector.filter_directories_only()
        assert len(dirs_only) == 1
        assert dirs_only[0].relative_path.name == "subdir"

    def test_calculate_relative_path_preserve_structure(self, tmp_path):
        """测试保持目录结构的相对路径计算"""
        base_path = tmp_path / "base"
        base_path.mkdir()
        subdir = base_path / "subdir"
        subdir.mkdir()
        file_path = subdir / "file.txt"

        collector = FileCollector()
        relative_path = collector._calculate_relative_path(
            file_path, base_path, base_path, preserve_structure=True
        )

        assert relative_path == Path("subdir/file.txt")

    def test_calculate_relative_path_no_preserve_structure(self, tmp_path):
        """测试不保持目录结构的相对路径计算"""
        base_path = tmp_path / "base"
        base_path.mkdir()
        subdir = base_path / "subdir"
        subdir.mkdir()
        file_path = subdir / "file.txt"
        file_path.write_text("test")  # 创建实际文件

        collector = FileCollector()
        relative_path = collector._calculate_relative_path(
            file_path, base_path, base_path, preserve_structure=False
        )

        assert relative_path == Path("file.txt")

    def test_is_excluded_no_patterns(self):
        """测试无排除模式"""
        collector = FileCollector()
        assert not collector._is_excluded(Path("file.txt"))

    def test_is_excluded_simple_pattern(self):
        """测试简单排除模式"""
        collector = FileCollector()
        collector.excluded_patterns = ["*.txt"]

        assert collector._is_excluded(Path("file.txt"))
        assert not collector._is_excluded(Path("file.log"))

    def test_is_excluded_directory_pattern(self):
        """测试目录排除模式"""
        collector = FileCollector()
        collector.excluded_patterns = ["temp/"]

        assert collector._is_excluded(Path("temp/file.txt"))
        assert collector._is_excluded(Path("temp/subdir/file.txt"))
        assert not collector._is_excluded(Path("other/file.txt"))

    def test_is_excluded_path_pattern(self):
        """测试路径模式"""
        collector = FileCollector()
        collector.excluded_patterns = ["src/test/"]

        assert collector._is_excluded(Path("src/test/file.txt"))
        assert not collector._is_excluded(Path("src/main/file.txt"))

    def test_match_pattern_glob(self):
        """测试 glob 模式匹配"""
        collector = FileCollector()

        assert collector._match_pattern("file.txt", "*.txt")
        assert not collector._match_pattern("file.log", "*.txt")

    def test_match_pattern_directory(self):
        """测试目录模式匹配"""
        collector = FileCollector()

        assert collector._match_pattern("temp/file.txt", "temp/")
        assert collector._match_pattern("temp/sub/file.txt", "temp/")
        assert not collector._match_pattern("other/file.txt", "temp/")

    def test_match_pattern_path_segments(self):
        """测试路径段匹配"""
        collector = FileCollector()

        assert collector._match_pattern("src/test/file.txt", "src/test/file.txt")
        assert collector._match_pattern("src/test/file.txt", "src/*/file.txt")
        assert not collector._match_pattern("src/main/file.txt", "src/test/file.txt")

    def test_create_file_info_file(self, tmp_path):
        """测试创建文件信息（文件）"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        collector = FileCollector()
        file_info = collector._create_file_info(test_file, tmp_path, Path("test.txt"))

        assert file_info is not None
        assert file_info.path == test_file
        assert file_info.relative_path == Path("test.txt")
        assert file_info.size == len("test content")
        assert not file_info.is_directory

    def test_create_file_info_directory(self, tmp_path):
        """测试创建文件信息（目录）"""
        test_dir = tmp_path / "testdir"
        test_dir.mkdir()

        collector = FileCollector()
        file_info = collector._create_file_info(test_dir, tmp_path, Path("testdir"))

        assert file_info is not None
        assert file_info.path == test_dir
        assert file_info.relative_path == Path("testdir")
        assert file_info.size == 0
        assert file_info.is_directory

    def test_create_file_info_nonexistent(self, tmp_path):
        """测试创建不存在文件的文件信息"""
        nonexistent = tmp_path / "nonexistent.txt"

        collector = FileCollector()
        file_info = collector._create_file_info(nonexistent, tmp_path, Path("nonexistent.txt"))

        assert file_info is None

    @patch('pathlib.Path.stat')
    def test_create_file_info_permission_error(self, mock_stat, tmp_path):
        """测试创建文件信息时的权限错误"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        mock_stat.side_effect = PermissionError("Access denied")

        collector = FileCollector()
        file_info = collector._create_file_info(test_file, tmp_path, Path("test.txt"))

        assert file_info is None


class TestGlobalFunctions:
    """全局函数测试"""

    def test_collect_files_function(self, tmp_path):
        """测试全局 collect_files 函数"""
        # 创建测试文件
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")

        inputs = [InputPathModel(path=str(tmp_path), recursive=True, preserve_structure=True)]
        files = collect_files(inputs)

        file_infos = [f for f in files if not f.is_directory]
        assert len(file_infos) == 2