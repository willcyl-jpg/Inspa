"""配置和 Schema 模块

提供 YAML 配置文件的加载、验证和保存功能。
"""

from .schema import InspaConfig
from .loader import (
    ConfigLoader, 
    ConfigValidationError,
    ConfigError,
    load_config, 
    validate_config, 
    save_config,
    config_loader
)

__all__ = [
    # 主要类
    "InspaConfig",
    "ConfigLoader",
    
    # 异常类
    "ConfigError", 
    "ConfigValidationError",
    
    # 便捷函数
    "load_config", 
    "validate_config", 
    "save_config",
    
    # 单例
    "config_loader",
]