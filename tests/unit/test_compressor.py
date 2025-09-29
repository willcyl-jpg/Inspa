"""
压缩器单元测试

测试 Zstd 和 Zip 压缩算法、压缩/解压功能、错误处理等。
"""

import io
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from inspa.build.collector import FileInfo
from inspa.build.compressor import (
    Compressor,
    CompressionError,
    CompressorFactory,
    DecompressionError,
    ZstdCompressor,
    ZipCompressor,
)
from inspa.config.schema import CompressionAlgorithm


class TestZstdCompressor:
    """ZstdCompressor 测试"""

    def test_init(self):
        """测试初始化"""
        compressor = ZstdCompressor(level=10)
        assert compressor.level == 10
        assert compressor._cctx is not None
        assert compressor._dctx is not None

    def test_get_algorithm(self):
        """测试获取算法"""
        compressor = ZstdCompressor()
        assert compressor.get_algorithm() == CompressionAlgorithm.ZSTD

    def test_compress_files_basic(self, tmp_path):
        """测试基本文件压缩"""
        # 创建测试文件
        file1 = tmp_path / "file1.txt"
        file1.write_text("Hello World 1")
        file2 = tmp_path / "file2.txt"
        file2.write_text("Hello World 2")

        files = [
            FileInfo(path=file1, relative_path=Path("file1.txt"), size=13, mtime=1234567890.0, is_directory=False),
            FileInfo(path=file2, relative_path=Path("file2.txt"), size=13, mtime=1234567890.0, is_directory=False)
        ]

        compressor = ZstdCompressor()
        output = io.BytesIO()

        compressed_size = compressor.compress_files(files, output)

        assert compressed_size > 0
        assert len(output.getvalue()) > 0

    def test_compress_files_with_directory(self, tmp_path):
        """测试包含目录的文件压缩"""
        # 创建测试文件和目录
        file1 = tmp_path / "file1.txt"
        file1.write_text("Hello World")
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        files = [
            FileInfo(path=file1, relative_path=Path("file1.txt"), size=11, mtime=1234567890.0, is_directory=False),
            FileInfo(path=subdir, relative_path=Path("subdir"), size=0, mtime=1234567890.0, is_directory=True)
        ]

        compressor = ZstdCompressor()
        output = io.BytesIO()

        compressed_size = compressor.compress_files(files, output)

        assert compressed_size > 0

    def test_decompress_to_directory(self, tmp_path):
        """测试解压到目录"""
        # 创建测试文件
        file1 = tmp_path / "file1.txt"
        file1.write_text("Hello World 1")
        file2 = tmp_path / "file2.txt"
        file2.write_text("Hello World 2")

        files = [
            FileInfo(path=file1, relative_path=Path("file1.txt"), size=13, mtime=1234567890.0, is_directory=False),
            FileInfo(path=file2, relative_path=Path("file2.txt"), size=13, mtime=1234567890.0, is_directory=False)
        ]

        # 压缩
        compressor = ZstdCompressor()
        compressed_data = io.BytesIO()
        compressor.compress_files(files, compressed_data)

        # 解压到新目录
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        compressed_data.seek(0)
        decompressed_size = compressor.decompress_to_directory(compressed_data, extract_dir)

        assert decompressed_size > 0

        # 验证解压结果
        extracted_file1 = extract_dir / "file1.txt"
        extracted_file2 = extract_dir / "file2.txt"

        assert extracted_file1.exists()
        assert extracted_file2.exists()
        assert extracted_file1.read_text() == "Hello World 1"
        assert extracted_file2.read_text() == "Hello World 2"

    def test_compress_files_read_error(self, tmp_path):
        """测试压缩时的读取错误"""
        # 创建不存在的文件
        nonexistent = tmp_path / "nonexistent.txt"
        files = [
            FileInfo(path=nonexistent, relative_path=Path("nonexistent.txt"), size=0, mtime=1234567890.0, is_directory=False)
        ]

        compressor = ZstdCompressor()
        output = io.BytesIO()

        with pytest.raises(CompressionError) as exc_info:
            compressor.compress_files(files, output)

        assert "读取文件失败" in str(exc_info.value)

    def test_decompress_invalid_data(self, tmp_path):
        """测试解压无效数据"""
        compressor = ZstdCompressor()
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        invalid_data = io.BytesIO(b"invalid zstd data")

        with pytest.raises(DecompressionError):
            compressor.decompress_to_directory(invalid_data, extract_dir)

    @patch('inspa.build.compressor.ZSTD_AVAILABLE', False)
    def test_init_without_zstd(self):
        """测试在没有 zstd 的情况下初始化"""
        with pytest.raises(CompressionError) as exc_info:
            ZstdCompressor()

        assert "zstandard 库未安装" in str(exc_info.value)


class TestZipCompressor:
    """ZipCompressor 测试"""

    def test_init(self):
        """测试初始化"""
        compressor = ZipCompressor(level=6)
        assert compressor.level == 6

    def test_init_level_bounds(self):
        """测试压缩级别边界"""
        # 有效级别
        compressor = ZipCompressor(level=1)
        assert compressor.level == 1

        compressor = ZipCompressor(level=9)
        assert compressor.level == 9

        # 超出边界的级别会被限制
        compressor = ZipCompressor(level=0)
        assert compressor.level == 1

        compressor = ZipCompressor(level=10)
        assert compressor.level == 9

    def test_get_algorithm(self):
        """测试获取算法"""
        compressor = ZipCompressor()
        assert compressor.get_algorithm() == CompressionAlgorithm.ZIP

    def test_compress_files_basic(self, tmp_path):
        """测试基本文件压缩"""
        # 创建测试文件
        file1 = tmp_path / "file1.txt"
        file1.write_text("Hello World 1")
        file2 = tmp_path / "file2.txt"
        file2.write_text("Hello World 2")

        files = [
            FileInfo(path=file1, relative_path=Path("file1.txt"), size=13, mtime=1234567890.0, is_directory=False),
            FileInfo(path=file2, relative_path=Path("file2.txt"), size=13, mtime=1234567890.0, is_directory=False)
        ]

        compressor = ZipCompressor()
        output = io.BytesIO()

        compressed_size = compressor.compress_files(files, output)

        assert compressed_size > 0
        assert len(output.getvalue()) > 0

    def test_compress_files_with_directory(self, tmp_path):
        """测试包含目录的文件压缩"""
        # 创建测试文件和目录
        file1 = tmp_path / "file1.txt"
        file1.write_text("Hello World")
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        files = [
            FileInfo(path=file1, relative_path=Path("file1.txt"), size=11, mtime=1234567890.0, is_directory=False),
            FileInfo(path=subdir, relative_path=Path("subdir"), size=0, mtime=1234567890.0, is_directory=True)
        ]

        compressor = ZipCompressor()
        output = io.BytesIO()

        compressed_size = compressor.compress_files(files, output)

        assert compressed_size > 0

    def test_decompress_to_directory(self, tmp_path):
        """测试解压到目录"""
        # 创建测试文件
        file1 = tmp_path / "file1.txt"
        file1.write_text("Hello World 1")
        file2 = tmp_path / "file2.txt"
        file2.write_text("Hello World 2")

        files = [
            FileInfo(path=file1, relative_path=Path("file1.txt"), size=13, mtime=1234567890.0, is_directory=False),
            FileInfo(path=file2, relative_path=Path("file2.txt"), size=13, mtime=1234567890.0, is_directory=False)
        ]

        # 压缩
        compressor = ZipCompressor()
        compressed_data = io.BytesIO()
        compressor.compress_files(files, compressed_data)

        # 解压到新目录
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        compressed_data.seek(0)
        decompressed_size = compressor.decompress_to_directory(compressed_data, extract_dir)

        assert decompressed_size > 0

        # 验证解压结果
        extracted_file1 = extract_dir / "file1.txt"
        extracted_file2 = extract_dir / "file2.txt"

        assert extracted_file1.exists()
        assert extracted_file2.exists()
        assert extracted_file1.read_text() == "Hello World 1"
        assert extracted_file2.read_text() == "Hello World 2"

    def test_compress_files_read_error(self, tmp_path):
        """测试压缩时的读取错误"""
        # 创建不存在的文件
        nonexistent = tmp_path / "nonexistent.txt"
        files = [
            FileInfo(path=nonexistent, relative_path=Path("nonexistent.txt"), size=0, mtime=1234567890.0, is_directory=False)
        ]

        compressor = ZipCompressor()
        output = io.BytesIO()

        with pytest.raises(CompressionError) as exc_info:
            compressor.compress_files(files, output)

        assert "添加文件到 Zip 失败" in str(exc_info.value)

    def test_decompress_invalid_data(self, tmp_path):
        """测试解压无效数据"""
        compressor = ZipCompressor()
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        invalid_data = io.BytesIO(b"invalid zip data")

        with pytest.raises(DecompressionError):
            compressor.decompress_to_directory(invalid_data, extract_dir)


class TestCompressorFactory:
    """CompressorFactory 测试"""

    def test_create_zstd_compressor(self):
        """测试创建 Zstd 压缩器"""
        compressor = CompressorFactory.create_compressor(CompressionAlgorithm.ZSTD, level=10)
        assert isinstance(compressor, ZstdCompressor)
        assert compressor.level == 10

    def test_create_zip_compressor(self):
        """测试创建 Zip 压缩器"""
        compressor = CompressorFactory.create_compressor(CompressionAlgorithm.ZIP, level=6)
        assert isinstance(compressor, ZipCompressor)
        assert compressor.level == 6

    @patch('inspa.build.compressor.ZSTD_AVAILABLE', False)
    def test_create_zstd_compressor_fallback_to_zip(self):
        """测试 Zstd 不可用时回退到 Zip"""
        compressor = CompressorFactory.create_compressor(
            CompressionAlgorithm.ZSTD, level=10, fallback_to_zip=True
        )
        assert isinstance(compressor, ZipCompressor)

    @patch('inspa.build.compressor.ZSTD_AVAILABLE', False)
    def test_create_zstd_compressor_no_fallback(self):
        """测试 Zstd 不可用且不回退时报错"""
        with pytest.raises(CompressionError) as exc_info:
            CompressorFactory.create_compressor(
                CompressionAlgorithm.ZSTD, level=10, fallback_to_zip=False
            )

        assert "Zstd 不可用且未启用自动回退" in str(exc_info.value)

    def test_get_available_algorithms(self):
        """测试获取可用算法"""
        algorithms = CompressorFactory.get_available_algorithms()

        # Zip 总是可用
        assert CompressionAlgorithm.ZIP in algorithms

        # Zstd 只有在可用时才包含
        try:
            import zstandard
            assert CompressionAlgorithm.ZSTD in algorithms
        except ImportError:
            assert CompressionAlgorithm.ZSTD not in algorithms

    def test_get_available_algorithms_zstd_first(self):
        """测试 Zstd 可用时排在前面"""
        try:
            import zstandard
            algorithms = CompressorFactory.get_available_algorithms()
            assert algorithms[0] == CompressionAlgorithm.ZSTD
            assert algorithms[1] == CompressionAlgorithm.ZIP
        except ImportError:
            # 如果 Zstd 不可用，跳过这个测试
            pass


class TestProgressCallback:
    """进度回调测试"""

    def test_compress_with_progress_callback(self, tmp_path):
        """测试带进度回调的压缩"""
        # 创建测试文件
        file1 = tmp_path / "file1.txt"
        file1.write_text("Hello World")

        files = [
            FileInfo(path=file1, relative_path=Path("file1.txt"), size=11, mtime=1234567890.0, is_directory=False)
        ]

        progress_calls = []
        def progress_callback(current, total, current_file=None):
            progress_calls.append((current, total, current_file))

        compressor = ZstdCompressor()
        output = io.BytesIO()

        compressor.compress_files(files, output, progress_callback)

        assert len(progress_calls) > 0
        # 验证进度回调参数
        for call in progress_calls:
            assert call[0] <= call[1]  # current <= total

    def test_decompress_with_progress_callback(self, tmp_path):
        """测试带进度回调的解压"""
        # 创建测试文件
        file1 = tmp_path / "file1.txt"
        file1.write_text("Hello World")

        files = [
            FileInfo(path=file1, relative_path=Path("file1.txt"), size=11, mtime=1234567890.0, is_directory=False)
        ]

        # 压缩
        compressor = ZstdCompressor()
        compressed_data = io.BytesIO()
        compressor.compress_files(files, compressed_data)

        # 解压并测试进度回调
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        progress_calls = []
        def progress_callback(current, total, current_file=None):
            progress_calls.append((current, total, current_file))

        compressed_data.seek(0)
        compressor.decompress_to_directory(compressed_data, extract_dir, progress_callback)

        assert len(progress_calls) > 0


class TestErrorHandling:
    """错误处理测试"""

    def test_compression_error_inheritance(self):
        """测试压缩错误继承"""
        error = CompressionError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_decompression_error_inheritance(self):
        """测试解压错误继承"""
        error = DecompressionError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"