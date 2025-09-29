"""
配置 Schema 定义

使用 Pydantic 定义严格的 YAML 配置模型，支持验证和类型检查。
映射需求：FR-BLD-001, FR-CFG-001, FR-CFG-008, FR-CFG-009, FR-CFG-010, FR-CFG-011
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class CompressionAlgorithm(str, Enum):
    """压缩算法枚举"""
    ZSTD = "zstd"
    ZIP = "zip"


class ScriptType(str, Enum):
    """脚本类型枚举"""
    POWERSHELL = "powershell"
    BATCH = "batch"


class RunCondition(str, Enum):
    """脚本运行条件枚举"""
    ALWAYS = "always"
    SUCCESS = "success"
    FAILURE = "failure"


class ProductModel(BaseModel):
    """产品信息模型"""
    name: str = Field(..., description="产品名称", min_length=1, max_length=100)
    version: str = Field(..., description="版本号", min_length=1, max_length=20)
    company: Optional[str] = Field(None, description="公司名称", max_length=100)
    description: Optional[str] = Field(None, description="产品描述", max_length=500)
    copyright: Optional[str] = Field(None, description="版权信息", max_length=200)
    website: Optional[str] = Field(None, description="官网地址")

    @field_validator('version')
    @classmethod
    def validate_version(cls, v: str) -> str:
        """验证版本号格式 - 支持更灵活的格式"""
        import re
        # 支持多种版本号格式：
        # - 语义化版本：1.0.0, 1.2.3-beta.1  
        # - 简单格式：1.0, 1.2.3.4, 25.9.25
        # - 日期格式：2025.01.01, 25.9.25
        patterns = [
            r'^\d+\.\d+\.\d+(?:-[\w\-\.]+)?$',  # 标准 SemVer
            r'^\d+\.\d+$',                      # 简单两段式
            r'^\d+\.\d+\.\d+\.\d+$',           # 四段式
            r'^\d{2,4}\.\d{1,2}\.\d{1,2}$',    # 日期格式
        ]
        
        for pattern in patterns:
            if re.match(pattern, v):
                return v
        
        raise ValueError("版本号格式不正确，支持格式：1.0.0（SemVer）、1.0、25.9.25（日期格式）等")
        return v


class UIModel(BaseModel):
    """UI 配置模型"""
    window_title: Optional[str] = Field(
        None, 
        description="安装器窗口标题", 
        max_length=100
    )
    welcome_heading: Optional[str] = Field(
        None, 
        description="欢迎页主标题", 
        max_length=100
    )
    welcome_subtitle: Optional[str] = Field(
        None, 
        description="欢迎页副标题", 
        max_length=200
    )
    theme: Literal["github-light"] = Field(
        "github-light", 
        description="UI 主题（目前仅支持 github-light）"
    )
    show_progress_script_output: bool = Field(
        True, 
        description="是否在进度页面显示脚本输出"
    )


class InstallModel(BaseModel):
    """安装配置模型"""
    default_path: str = Field(
        ..., 
        description="默认安装路径", 
        min_length=1
    )
    allow_user_path: bool = Field(
        True, 
        description="是否允许用户修改安装路径"
    )
    force_hidden_path: bool = Field(
        False, 
        description="是否强制隐藏路径选择（自动使用默认路径）"
    )
    silent_allowed: bool = Field(
        True, 
        description="是否允许静默安装"
    )
    license_file: Optional[Union[str, Path]] = Field(
        None, 
        description="许可协议文件路径"
    )
    privacy_file: Optional[Union[str, Path]] = Field(
        None, 
        description="隐私声明文件路径"
    )
    require_admin: bool = Field(
        False, 
        description="是否需要管理员权限"
    )
    icon_path: Optional[Union[str, Path]] = Field(
        None,
        description="自定义图标路径 (.ico 文件)"
    )

    @field_validator('default_path')
    @classmethod
    def validate_default_path(cls, v: str) -> str:
        """验证默认安装路径"""
        if not v.strip():
            raise ValueError("默认安装路径不能为空")
        return v.strip()

    @field_validator('license_file', 'privacy_file')
    @classmethod
    def validate_text_file(cls, v: Optional[Union[str, Path]]) -> Optional[Path]:
        """验证文本文件路径"""
        if v is None:
            return None
        
        path = Path(v)
        if path.suffix.lower() not in ['.txt', '.md', '.rst']:
            raise ValueError("文本文件必须是 .txt, .md 或 .rst 格式")
        
        return path

    @model_validator(mode='after')
    def validate_path_settings(self) -> 'InstallModel':
        """验证路径设置的一致性"""
        if self.force_hidden_path and self.allow_user_path:
            raise ValueError("force_hidden_path 和 allow_user_path 不能同时为 true")
        return self


class CompressionModel(BaseModel):
    """压缩配置模型"""
    algo: CompressionAlgorithm = Field(
        CompressionAlgorithm.ZSTD, 
        description="压缩算法"
    )
    level: int = Field(
        10, 
        description="压缩级别", 
        ge=1, 
        le=22
    )
    fallback_to_zip: bool = Field(
        True, 
        description="当 zstd 不可用时是否自动回退到 zip"
    )

    @model_validator(mode='after')
    def validate_compression_level(self) -> 'CompressionModel':
        """验证压缩级别对算法的适用性"""
        if self.algo == CompressionAlgorithm.ZSTD:
            # zstd 支持 1-22 级别
            if not 1 <= self.level <= 22:
                raise ValueError("Zstd 压缩级别必须在 1-22 之间")
        elif self.algo == CompressionAlgorithm.ZIP:
            # zip 只支持 1-9 级别
            if not 1 <= self.level <= 9:
                raise ValueError("Zip 压缩级别必须在 1-9 之间")
        
        return self


class InputPathModel(BaseModel):
    """输入路径模型"""
    path: Union[str, Path] = Field(..., description="输入文件或目录路径")
    recursive: bool = Field(True, description="是否递归包含子目录")
    preserve_structure: bool = Field(True, description="是否保持目录结构")
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v: Union[str, Path]) -> Path:
        """验证输入路径"""
        return Path(v)


class PostActionModel(BaseModel):
    """后置脚本动作模型"""
    type: ScriptType = Field(..., description="脚本类型")
    command: str = Field(..., description="脚本命令或文件路径", min_length=1)
    args: Optional[List[str]] = Field(None, description="脚本参数")
    hidden: bool = Field(True, description="是否隐藏执行（无控制台窗口）")
    timeout_sec: int = Field(300, description="超时时间（秒）", ge=1, le=3600)
    show_in_ui: bool = Field(True, description="是否在 UI 中显示输出")
    run_if: RunCondition = Field(RunCondition.ALWAYS, description="运行条件")
    working_dir: Optional[str] = Field(None, description="工作目录（相对于安装目录）")

    @field_validator('command')
    @classmethod
    def validate_command(cls, v: str) -> str:
        """验证命令"""
        if not v.strip():
            raise ValueError("脚本命令不能为空")
        return v.strip()


class EnvironmentModel(BaseModel):
    """环境变量配置模型"""
    add_path: Optional[List[str]] = Field(None, description="添加到 PATH 的路径列表")
    set: Optional[Dict[str, str]] = Field(None, description="设置的环境变量")
    system_scope: bool = Field(False, description="是否使用系统级作用域（需要管理员权限）")

    @field_validator('add_path')
    @classmethod
    def validate_add_path(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """验证 PATH 添加列表"""
        if v is None:
            return None
        
        # 去除空白和重复项
        cleaned = []
        for path in v:
            path = path.strip()
            if path and path not in cleaned:
                cleaned.append(path)
        
        return cleaned if cleaned else None


class ConfigModel(BaseModel):
    """配置元信息模型"""
    version: int = Field(1, description="配置 schema 版本", ge=1)
    
    @field_validator('version')
    @classmethod
    def validate_config_version(cls, v: int) -> int:
        """验证配置版本"""
        SUPPORTED_VERSIONS = [1]  # 目前支持的版本
        if v not in SUPPORTED_VERSIONS:
            raise ValueError(f"不支持的配置版本 {v}，支持的版本: {SUPPORTED_VERSIONS}")
        return v


class InspaConfig(BaseModel):
    """Inspa 主配置模型
    
    这是整个配置文件的根模型，包含所有配置部分。
    映射需求：FR-BLD-001, FR-CFG-001
    """
    
    # 元信息
    config: ConfigModel = Field(default_factory=ConfigModel, description="配置元信息")
    
    # 必填部分
    product: ProductModel = Field(..., description="产品信息")
    install: InstallModel = Field(..., description="安装配置")
    inputs: List[InputPathModel] = Field(..., description="输入文件/目录列表", min_length=1)
    
    # 可选部分
    ui: UIModel = Field(default_factory=UIModel, description="UI 配置")
    compression: CompressionModel = Field(default_factory=CompressionModel, description="压缩配置")
    exclude: Optional[List[str]] = Field(None, description="排除模式列表（glob 格式）")
    post_actions: Optional[List[PostActionModel]] = Field(None, description="后置脚本动作")
    env: Optional[EnvironmentModel] = Field(None, description="环境变量配置")
    
    model_config = {
        "extra": "forbid",  # 禁止额外字段
        "validate_assignment": True,  # 启用赋值验证
        "str_strip_whitespace": True,  # 自动去除字符串空白
    }

    @model_validator(mode='after')
    def validate_admin_requirements(self) -> 'InspaConfig':
        """验证管理员权限需求的一致性"""
        needs_admin = False
        
        # 检查是否需要系统级环境变量
        if self.env and self.env.system_scope:
            needs_admin = True
        
        # 检查是否有需要管理员权限的安装路径
        if self.install.default_path.startswith('%ProgramFiles%'):
            needs_admin = True
            
        # 如果需要管理员权限但未设置，给出警告
        if needs_admin and not self.install.require_admin:
            # 这里可以选择自动设置或抛出警告
            # 暂时选择自动设置
            self.install.require_admin = True
            
        return self

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = self.model_dump(exclude_none=True, by_alias=True)
        
        # 转换 Path 对象和枚举为字符串
        def convert_values(obj):
            if isinstance(obj, dict):
                return {k: convert_values(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_values(item) for item in obj]
            elif isinstance(obj, (Path, Enum)):
                return str(obj)
            else:
                return obj
        
        return convert_values(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InspaConfig':
        """从字典创建配置实例"""
        return cls.model_validate(data)

    def get_version_info(self) -> Dict[str, str]:
        """获取版本信息字典（用于注入到 EXE 中）"""
        return {
            'FileVersion': self.product.version,
            'ProductVersion': self.product.version,
            'CompanyName': self.product.company or '',
            'FileDescription': self.product.description or self.product.name,
            'InternalName': self.product.name,
            'LegalCopyright': self.product.copyright or '',
            'OriginalFilename': f'{self.product.name}_installer.exe',
            'ProductName': self.product.name,
        }

    def get_window_title(self) -> str:
        """获取窗口标题"""
        return self.ui.window_title or f'{self.product.name} 安装程序'

    def get_welcome_heading(self) -> str:
        """获取欢迎页主标题"""
        return self.ui.welcome_heading or f'欢迎安装 {self.product.name}'

    def get_welcome_subtitle(self) -> str:
        """获取欢迎页副标题"""
        return self.ui.welcome_subtitle or '请按步骤完成安装'