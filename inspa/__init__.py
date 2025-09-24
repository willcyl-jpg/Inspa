"""
Inspa - Windows 单文件自解压安装器构建与运行系统

A self-extracting installer builder and runtime system for Windows.
"""

__version__ = "0.1.0"
__author__ = "Project Team"
__email__ = "team@inspa.dev"
__license__ = "MIT"

# 导出主要 API
try:
    from .config.schema import InspaConfig
    from .build.builder import Builder
    
    __all__ = ["InspaConfig", "Builder", "__version__"]
except ImportError:
    # 在没有安装依赖的情况下仍然可以导入版本信息
    __all__ = ["__version__"]