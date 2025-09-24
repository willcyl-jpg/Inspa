"""
文件收集器

负责根据配置收集需要打包的文件，支持 glob 模式排除。
映射需求：FR-BLD-002, FR-BLD-003
"""

import fnmatch
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set

from ..config.schema import InputPathModel


@dataclass
class FileInfo:
    """文件信息"""
    path: Path  # 绝对路径
    relative_path: Path  # 相对于输入根目录的路径
    size: int  # 文件大小（字节）
    mtime: float  # 修改时间（时间戳）
    is_directory: bool = False  # 是否为目录
    
    def to_dict(self) -> Dict[str, any]:
        """转换为字典格式"""
        return {
            'path': str(self.relative_path).replace('\\', '/'),  # 统一使用正斜杠
            'size': self.size,
            'mtime': self.mtime,
            'is_directory': self.is_directory,
        }


class FileCollector:
    """文件收集器
    
    负责扫描和收集需要打包的文件，应用排除规则。
    """
    
    def __init__(self):
        self.collected_files: List[FileInfo] = []
        self.excluded_patterns: List[str] = []
        self.total_size: int = 0
        
    def collect_files(
        self, 
        inputs: List[InputPathModel], 
        exclude_patterns: Optional[List[str]] = None
    ) -> List[FileInfo]:
        """收集文件
        
        Args:
            inputs: 输入路径配置列表
            exclude_patterns: 排除模式列表（glob 格式）
            
        Returns:
            List[FileInfo]: 收集到的文件信息列表
            
        Raises:
            FileNotFoundError: 输入路径不存在
            ValueError: 输入路径无效
        """
        self.collected_files.clear()
        self.excluded_patterns = exclude_patterns or []
        self.total_size = 0
        
        # 跟踪已添加的文件，避免重复
        added_files: Set[Path] = set()
        
        for input_config in inputs:
            input_path = Path(input_config.path)
            
            if not input_path.exists():
                raise FileNotFoundError(f"输入路径不存在: {input_path}")
            
            if input_path.is_file():
                # 单个文件
                file_info = self._create_file_info(
                    input_path, 
                    input_path.parent,  # 使用文件所在目录作为基准
                    input_path.name     # 相对路径就是文件名
                )
                
                if file_info and file_info.path not in added_files:
                    if not self._is_excluded(file_info.relative_path):
                        self.collected_files.append(file_info)
                        added_files.add(file_info.path)
                        self.total_size += file_info.size
                        
            elif input_path.is_dir():
                # 目录
                base_path = input_path.parent if input_config.preserve_structure else input_path
                
                if input_config.recursive:
                    # 递归扫描
                    for file_path in self._walk_directory(input_path):
                        relative_path = self._calculate_relative_path(
                            file_path, base_path, input_path, input_config.preserve_structure
                        )
                        
                        file_info = self._create_file_info(file_path, base_path, relative_path)
                        
                        if file_info and file_info.path not in added_files:
                            if not self._is_excluded(relative_path):
                                self.collected_files.append(file_info)
                                added_files.add(file_info.path)
                                if not file_info.is_directory:
                                    self.total_size += file_info.size
                else:
                    # 只扫描直接子项
                    for item in input_path.iterdir():
                        relative_path = self._calculate_relative_path(
                            item, base_path, input_path, input_config.preserve_structure
                        )
                        
                        file_info = self._create_file_info(item, base_path, relative_path)
                        
                        if file_info and file_info.path not in added_files:
                            if not self._is_excluded(relative_path):
                                self.collected_files.append(file_info)
                                added_files.add(file_info.path)
                                if not file_info.is_directory:
                                    self.total_size += file_info.size
            else:
                raise ValueError(f"输入路径既不是文件也不是目录: {input_path}")
        
        # 按相对路径排序，确保输出一致性
        self.collected_files.sort(key=lambda x: str(x.relative_path))
        
        return self.collected_files
    
    def get_statistics(self) -> Dict[str, any]:
        """获取收集统计信息"""
        file_count = sum(1 for f in self.collected_files if not f.is_directory)
        dir_count = sum(1 for f in self.collected_files if f.is_directory)
        
        return {
            'total_files': file_count,
            'total_directories': dir_count,
            'total_items': len(self.collected_files),
            'total_size': self.total_size,
            'total_size_mb': round(self.total_size / (1024 * 1024), 2),
        }
    
    def filter_files_only(self) -> List[FileInfo]:
        """只返回文件，排除目录"""
        return [f for f in self.collected_files if not f.is_directory]
    
    def filter_directories_only(self) -> List[FileInfo]:
        """只返回目录，排除文件"""
        return [f for f in self.collected_files if f.is_directory]
    
    def _walk_directory(self, directory: Path) -> Iterator[Path]:
        """递归遍历目录
        
        Args:
            directory: 要遍历的目录
            
        Yields:
            Path: 文件或目录路径
        """
        try:
            # 先返回目录本身
            yield directory
            
            # 然后遍历内容
            for item in directory.iterdir():
                if item.is_dir():
                    # 递归处理子目录
                    yield from self._walk_directory(item)
                else:
                    # 返回文件
                    yield item
                    
        except PermissionError:
            # 忽略无权限访问的目录
            pass
        except OSError:
            # 忽略其他 OS 错误（如符号链接损坏）
            pass
    
    def _create_file_info(self, file_path: Path, base_path: Path, relative_path: Path) -> Optional[FileInfo]:
        """创建文件信息对象
        
        Args:
            file_path: 文件绝对路径
            base_path: 基准路径
            relative_path: 相对路径
            
        Returns:
            FileInfo: 文件信息，如果出错返回 None
        """
        try:
            stat = file_path.stat()
            return FileInfo(
                path=file_path.resolve(),
                relative_path=relative_path,
                size=stat.st_size if file_path.is_file() else 0,
                mtime=stat.st_mtime,
                is_directory=file_path.is_dir()
            )
        except (OSError, PermissionError):
            # 忽略无法访问的文件
            return None
    
    def _calculate_relative_path(
        self, 
        file_path: Path, 
        base_path: Path, 
        input_path: Path, 
        preserve_structure: bool
    ) -> Path:
        """计算相对路径
        
        Args:
            file_path: 文件路径
            base_path: 基准路径
            input_path: 输入路径
            preserve_structure: 是否保持目录结构
            
        Returns:
            Path: 相对路径
        """
        if preserve_structure:
            # 保持完整目录结构
            try:
                return file_path.relative_to(base_path)
            except ValueError:
                # 如果无法计算相对路径，使用文件名
                return Path(file_path.name)
        else:
            # 平铺结构，只保留文件名
            if file_path.is_file():
                return Path(file_path.name)
            else:
                # 对于目录，使用相对于输入路径的相对路径
                try:
                    return file_path.relative_to(input_path)
                except ValueError:
                    return Path(file_path.name)
    
    def _is_excluded(self, relative_path: Path) -> bool:
        """检查路径是否被排除
        
        Args:
            relative_path: 相对路径
            
        Returns:
            bool: 是否被排除
        """
        if not self.excluded_patterns:
            return False
        
        # 统一使用正斜杠路径进行匹配
        path_str = str(relative_path).replace('\\', '/')
        
        for pattern in self.excluded_patterns:
            # 标准化模式字符串
            pattern = pattern.replace('\\', '/')
            
            # 支持多种匹配方式
            if self._match_pattern(path_str, pattern):
                return True
        
        return False
    
    def _match_pattern(self, path: str, pattern: str) -> bool:
        """匹配单个模式
        
        Args:
            path: 文件路径
            pattern: glob 模式
            
        Returns:
            bool: 是否匹配
        """
        # 直接 glob 匹配
        if fnmatch.fnmatch(path, pattern):
            return True
        
        # 目录模式匹配（以 / 结尾）
        if pattern.endswith('/'):
            dir_pattern = pattern.rstrip('/')
            # 匹配目录本身
            if fnmatch.fnmatch(path, dir_pattern):
                return True
            # 匹配目录内的所有文件
            if path.startswith(dir_pattern + '/'):
                return True
        
        # 扩展名匹配（以 * 开头）
        if pattern.startswith('*.'):
            ext = pattern[1:]  # 去掉 *
            if path.endswith(ext):
                return True
        
        # 路径片段匹配（包含路径分隔符）
        if '/' in pattern:
            # 支持路径中的 glob 模式
            path_parts = path.split('/')
            pattern_parts = pattern.split('/')
            
            # 检查是否有部分匹配
            for i in range(len(path_parts) - len(pattern_parts) + 1):
                if all(
                    fnmatch.fnmatch(path_parts[i + j], pattern_parts[j])
                    for j in range(len(pattern_parts))
                ):
                    return True
        
        return False


def collect_files(
    inputs: List[InputPathModel], 
    exclude_patterns: Optional[List[str]] = None
) -> List[FileInfo]:
    """便捷函数：收集文件
    
    Args:
        inputs: 输入路径配置列表
        exclude_patterns: 排除模式列表
        
    Returns:
        List[FileInfo]: 文件信息列表
    """
    collector = FileCollector()
    return collector.collect_files(inputs, exclude_patterns)