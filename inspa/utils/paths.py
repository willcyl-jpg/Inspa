"""
路径工具

提供路径处理相关的工具函数。
"""

import os
import tempfile
from pathlib import Path
from typing import Union


def expand_path(path: Union[str, Path]) -> Path:
    """扩展路径（处理环境变量和用户目录）
    
    Args:
        path: 原始路径
        
    Returns:
        Path: 扩展后的路径
    """
    if isinstance(path, str):
        # 处理 Windows 环境变量
        path = os.path.expandvars(path)
        # 处理用户目录
        path = os.path.expanduser(path)
    
    return Path(path).resolve()


def ensure_directory(path: Union[str, Path]) -> Path:
    """确保目录存在
    
    Args:
        path: 目录路径
        
    Returns:
        Path: 目录路径
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_temp_dir(prefix: str = "inspa_") -> Path:
    """获取临时目录
    
    Args:
        prefix: 目录前缀
        
    Returns:
        Path: 临时目录路径
    """
    temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
    return temp_dir


def safe_path_join(*parts: Union[str, Path]) -> Path:
    """安全的路径拼接（防止目录穿越）
    
    Args:
        *parts: 路径部分
        
    Returns:
        Path: 拼接后的路径
        
    Raises:
        ValueError: 检测到目录穿越尝试
    """
    if not parts:
        return Path(".")
    
    result = Path(parts[0])
    
    for part in parts[1:]:
        part_path = Path(part)
        
        # 检查是否包含上级目录引用
        if any(p == ".." for p in part_path.parts):
            raise ValueError(f"检测到目录穿越尝试: {part}")
        
        # 检查是否为绝对路径
        if part_path.is_absolute():
            raise ValueError(f"不允许使用绝对路径: {part}")
        
        result = result / part_path
    
    return result


def format_size(size_bytes: int) -> str:
    """格式化文件大小
    
    Args:
        size_bytes: 字节数
        
    Returns:
        str: 格式化的大小字符串
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def is_safe_filename(filename: str) -> bool:
    """检查文件名是否安全
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 是否安全
    """
    # Windows 非法字符
    illegal_chars = '<>:"/\\|?*'
    
    # 检查非法字符
    if any(char in filename for char in illegal_chars):
        return False
    
    # 检查保留名称（Windows）
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL', 
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    name_only = filename.split('.')[0].upper()
    if name_only in reserved_names:
        return False
    
    # 检查长度
    if len(filename) > 255:
        return False
    
    return True