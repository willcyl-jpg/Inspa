"""
配置加载器

负责从 YAML 文件加载配置并进行验证。
映射需求：FR-BLD-001, FR-CFG-001, FR-BLD-017
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .schema import InspaConfig


class ConfigError(Exception):
    """配置错误基类"""
    pass


class ConfigValidationError(ConfigError):
    """配置验证错误"""
    
    def __init__(self, message: str, errors: List[Dict[str, Any]]):
        super().__init__(message)
        self.errors = errors

    def format_errors(self) -> str:
        """格式化错误信息为人类可读的格式"""
        formatted = []
        for error in self.errors:
            loc = " -> ".join(str(item) for item in error.get('loc', []))
            msg = error.get('msg', '未知错误')
            input_val = error.get('input', '')
            
            if loc:
                formatted.append(f"字段 '{loc}': {msg}")
                if input_val:
                    formatted.append(f"  输入值: {input_val}")
            else:
                formatted.append(f"根级别: {msg}")
        
        return "\n".join(formatted)

    def format_errors_json(self) -> str:
        """格式化错误信息为 JSON 格式"""
        return json.dumps(self.errors, ensure_ascii=False, indent=2)


@dataclass
class ValidationResult:
    """配置验证结果"""
    is_valid: bool
    errors: List[str] = None
    config: Optional[InspaConfig] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.width = 4096  # 避免长行自动换行

    def load_from_file(self, config_path: Union[str, Path]) -> InspaConfig:
        """从文件加载配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            InspaConfig: 验证后的配置实例
            
        Raises:
            ConfigError: 配置加载或验证错误
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise ConfigError(f"配置文件不存在: {config_path}")
            
        if not config_path.is_file():
            raise ConfigError(f"配置路径不是文件: {config_path}")
        
        # 检查文件扩展名
        if config_path.suffix.lower() not in ['.yaml', '.yml']:
            # 检查是否为 JSON 文件（用于友好提示）
            if config_path.suffix.lower() == '.json':
                raise ConfigError(
                    f"不再支持 JSON 配置文件: {config_path}\n"
                    "请转换为 YAML 格式。参考: https://yaml.org/"
                )
            else:
                raise ConfigError(
                    f"配置文件必须是 .yaml 或 .yml 格式: {config_path}"
                )
        
        try:
            # 读取并解析 YAML
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_data = self.yaml.load(f)
                
        except YAMLError as e:
            raise ConfigError(f"YAML 解析错误: {e}")
        except Exception as e:
            raise ConfigError(f"文件读取错误: {e}")
        
        if raw_data is None:
            raise ConfigError("配置文件为空")
            
        if not isinstance(raw_data, dict):
            raise ConfigError("配置文件根级别必须是对象/字典格式")
        
        # 解析相对路径（相对于配置文件所在目录）
        self._resolve_relative_paths(raw_data, config_path.parent)
        
        # 使用 Pydantic 验证
        try:
            config = InspaConfig.from_dict(raw_data)
        except ValidationError as e:
            errors = [error for error in e.errors()]
            raise ConfigValidationError(
                "配置验证失败",
                errors
            )
        
        return config

    def load_from_dict(self, data: Dict[str, Any], base_path: Optional[Path] = None) -> InspaConfig:
        """从字典加载配置
        
        Args:
            data: 配置数据字典
            base_path: 相对路径的基准路径
            
        Returns:
            InspaConfig: 验证后的配置实例
            
        Raises:
            ConfigValidationError: 配置验证错误
        """
        if base_path:
            # 创建数据副本避免修改原数据
            data = json.loads(json.dumps(data))  # 深拷贝
            self._resolve_relative_paths(data, base_path)
        
        try:
            config = InspaConfig.from_dict(data)
        except ValidationError as e:
            errors = [error for error in e.errors()]
            raise ConfigValidationError(
                "配置验证失败",
                errors
            )
        
        return config

    def save_to_file(self, config: InspaConfig, output_path: Union[str, Path]) -> None:
        """保存配置到文件
        
        Args:
            config: 配置实例
            output_path: 输出文件路径
            
        Raises:
            ConfigError: 保存错误
        """
        output_path = Path(output_path)
        
        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 转换为字典并写入 YAML
            data = config.to_dict()
            with open(output_path, 'w', encoding='utf-8') as f:
                self.yaml.dump(data, f)
                
        except Exception as e:
            raise ConfigError(f"保存配置文件失败: {e}")

    def validate_file(self, config_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """验证配置文件并返回错误列表
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            List[Dict]: 错误列表，空列表表示验证通过
        """
        try:
            self.load_from_file(config_path)
            return []
        except ConfigValidationError as e:
            return e.errors
        except ConfigError as e:
            return [{
                'loc': [],
                'msg': str(e),
                'type': 'config_error'
            }]

    def _resolve_relative_paths(self, data: Dict[str, Any], base_path: Path) -> None:
        """解析配置中的相对路径
        
        Args:
            data: 配置数据字典
            base_path: 基准路径
        """
        # 需要解析相对路径的字段
        path_fields = [
            ('resources', 'icon'),
            ('install', 'license_file'),
            ('install', 'privacy_file'),
        ]
        
        for field_path in path_fields:
            self._resolve_field_path(data, field_path, base_path)
        
        # 解析输入路径
        if 'inputs' in data and isinstance(data['inputs'], list):
            for input_item in data['inputs']:
                if isinstance(input_item, dict) and 'path' in input_item:
                    path_str = input_item['path']
                    if isinstance(path_str, str) and not Path(path_str).is_absolute():
                        resolved_path = (base_path / path_str).resolve()
                        input_item['path'] = str(resolved_path)
        
        # 解析后置脚本中的文件路径
        if 'post_actions' in data and isinstance(data['post_actions'], list):
            for action in data['post_actions']:
                if isinstance(action, dict) and 'command' in action:
                    command = action['command']
                    if isinstance(command, str) and command.endswith(('.ps1', '.bat', '.cmd')):
                        if not Path(command).is_absolute():
                            resolved_path = (base_path / command).resolve()
                            action['command'] = str(resolved_path)

    def _resolve_field_path(self, data: Dict[str, Any], field_path: tuple, base_path: Path) -> None:
        """解析单个字段的相对路径"""
        current = data
        
        # 导航到目标字段
        for i, key in enumerate(field_path[:-1]):
            if key not in current or not isinstance(current[key], dict):
                return
            current = current[key]
        
        # 处理最后一级字段
        final_key = field_path[-1]
        if final_key in current:
            path_value = current[final_key]
            if isinstance(path_value, str) and path_value:
                path_obj = Path(path_value)
                if not path_obj.is_absolute():
                    resolved_path = (base_path / path_value).resolve()
                    current[final_key] = str(resolved_path)


# 全局加载器实例
config_loader = ConfigLoader()


def load_config(config_path: Union[str, Path]) -> InspaConfig:
    """便捷函数：加载配置文件"""
    return config_loader.load_from_file(config_path)


def validate_config(config_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """便捷函数：验证配置文件"""
    return config_loader.validate_file(config_path)


def validate_config_with_result(config_or_path: Union[InspaConfig, str, Path]) -> ValidationResult:
    """验证配置并返回详细结果"""
    try:
        if isinstance(config_or_path, (str, Path)):
            config = load_config(config_or_path)
        else:
            config = config_or_path
        
        # 如果能成功加载，说明验证通过
        return ValidationResult(is_valid=True, config=config)
        
    except ConfigValidationError as e:
        # Pydantic 验证错误
        error_messages = []
        for error in e.errors:
            loc = " -> ".join(str(item) for item in error.get('loc', []))
            msg = error.get('msg', '未知错误')
            if loc:
                error_messages.append(f"字段 '{loc}': {msg}")
            else:
                error_messages.append(f"根级别: {msg}")
        
        return ValidationResult(is_valid=False, errors=error_messages)
        
    except Exception as e:
        # 其他错误 (文件读取、YAML解析等)
        return ValidationResult(is_valid=False, errors=[f"配置加载失败: {str(e)}"])


def save_config(config: InspaConfig, output_path: Union[str, Path]) -> None:
    """便捷函数：保存配置文件"""
    config_loader.save_to_file(config, output_path)