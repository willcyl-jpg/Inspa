"""
Header 构建器和哈希工具

负责生成安装器头部信息和计算完整性哈希。
映射需求：FR-BLD-009, FR-BLD-012, FR-SEC-001
"""

import hashlib
import json
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..config.schema import InspaConfig, CompressionAlgorithm
from ..utils import get_stage_logger, LogStage
from .collector import FileInfo


class PathJSONEncoder(json.JSONEncoder):
    """自定义 JSON 编码器，处理 Path 对象"""
    def default(self, o):  # type: ignore[override]
        if isinstance(o, Path):
            return str(o).replace('\\', '/')
        return super().default(o)


@dataclass
class HashInfo:
    """哈希信息"""
    algorithm: str  # 哈希算法名称
    archive: str    # 归档数据哈希
    header: Optional[str] = None  # 头部哈希（可选）


@dataclass
class BuildInfo:
    """构建信息"""
    timestamp: int          # 构建时间戳
    builder_version: str    # 构建器版本
    config_fingerprint: str # 配置指纹


@dataclass
class HeaderData:
    """头部数据结构
    
    对应实现计划中的 Header 规范。
    """
    magic: str                      # 魔术字符串 "INSPRO1"
    schema_version: int             # Schema 版本
    product: Dict[str, Any]         # 产品信息
    ui: Dict[str, Any]              # UI 配置
    install: Dict[str, Any]         # 安装配置
    compression: Dict[str, Any]     # 压缩配置
    files: List[Dict[str, Any]]     # 文件列表
    scripts: List[Dict[str, Any]]   # 脚本列表
    env: Optional[Dict[str, Any]]   # 环境变量配置
    hash: HashInfo                  # 哈希信息
    build: BuildInfo                # 构建信息
    stats: Optional[Dict[str, Any]] = None  # 统计信息(扩展)
    runtime: Optional[Dict[str, Any]] = None  # 运行时信息 (新增: 记录 runtime_type 等)


class HashCalculator:
    """哈希计算器"""
    
    def __init__(self, algorithm: str = "sha256"):
        """初始化哈希计算器
        
        Args:
            algorithm: 哈希算法名称
        """
        self.algorithm = algorithm.lower()
        if self.algorithm not in hashlib.algorithms_available:
            raise ValueError(f"不支持的哈希算法: {algorithm}")
        
        self._hasher = hashlib.new(self.algorithm)
    
    def update(self, data: Union[bytes, str]) -> None:
        """更新哈希数据
        
        Args:
            data: 要添加的数据
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        self._hasher.update(data)
    
    def update_from_file(self, file_path: Path, chunk_size: int = 64 * 1024) -> None:
        """从文件更新哈希
        
        Args:
            file_path: 文件路径
            chunk_size: 读取块大小
            
        Raises:
            IOError: 文件读取失败
        """
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    self._hasher.update(chunk)
        except (OSError, IOError) as e:
            raise IOError(f"读取文件失败 {file_path}: {e}")
    
    def update_from_stream(self, stream, chunk_size: int = 64 * 1024) -> None:
        """从流更新哈希
        
        Args:
            stream: 输入流
            chunk_size: 读取块大小
        """
        # 记住当前位置
        if hasattr(stream, 'tell') and hasattr(stream, 'seek'):
            current_pos = stream.tell()
        else:
            current_pos = None
        
        try:
            while True:
                chunk = stream.read(chunk_size)
                if not chunk:
                    break
                self._hasher.update(chunk)
        finally:
            # 恢复位置
            if current_pos is not None:
                stream.seek(current_pos)
    
    def hexdigest(self) -> str:
        """获取十六进制哈希值"""
        return self._hasher.hexdigest()
    
    def digest(self) -> bytes:
        """获取二进制哈希值"""
        return self._hasher.digest()
    
    @classmethod
    def hash_data(cls, data: Union[bytes, str], algorithm: str = "sha256") -> str:
        """便捷方法：计算数据哈希
        
        Args:
            data: 要计算哈希的数据
            algorithm: 哈希算法
            
        Returns:
            str: 十六进制哈希值
        """
        calculator = cls(algorithm)
        calculator.update(data)
        return calculator.hexdigest()
    
    @classmethod
    def hash_file(cls, file_path: Path, algorithm: str = "sha256") -> str:
        """便捷方法：计算文件哈希
        
        Args:
            file_path: 文件路径
            algorithm: 哈希算法
            
        Returns:
            str: 十六进制哈希值
        """
        calculator = cls(algorithm)
        calculator.update_from_file(file_path)
        return calculator.hexdigest()


class HeaderBuilder:
    """头部构建器"""
    
    MAGIC = "INSPRO1"
    SCHEMA_VERSION = 1
    
    def __init__(self, builder_version: str = "0.1.0"):
        """初始化头部构建器
        
        Args:
            builder_version: 构建器版本
        """
        self.builder_version = builder_version
    
    def build_header(
        self,
        config: InspaConfig,
        files: List[FileInfo],
        compression_algo: CompressionAlgorithm,
        archive_hash: str,
        original_size: Optional[int] = None,
        compressed_size: Optional[int] = None,
    ) -> HeaderData:
        """构建头部数据
        
        Args:
            config: 配置对象
            files: 文件列表
            compression_algo: 使用的压缩算法
            archive_hash: 归档数据哈希
            
        Returns:
            HeaderData: 头部数据
        """
        # 计算配置指纹
        config_fingerprint = self._calculate_config_fingerprint(config)
        
        # 构建各个部分
        file_count = sum(1 for f in files if not f.is_directory)
        header = HeaderData(
            magic=self.MAGIC,
            schema_version=self.SCHEMA_VERSION,
            product=self._build_product_info(config),
            ui=self._build_ui_info(config),
            install=self._build_install_info(config),
            compression=self._build_compression_info(config, compression_algo),
            files=self._build_file_list(files),
            scripts=self._build_script_list(config),
            env=self._build_env_info(config),
            hash=HashInfo(
                algorithm="sha256",
                archive=archive_hash
            ),
            build=BuildInfo(
                timestamp=int(time.time()),
                builder_version=self.builder_version,
                config_fingerprint=config_fingerprint
            ),
            stats={
                'original_size': original_size,
                'compressed_size': compressed_size,
                'file_count': file_count
            } if original_size is not None and compressed_size is not None else None,
            # 统一运行时：固定写入统一标记，供旧逻辑或调试使用；后续可逐步移除此字段
            runtime={'type': 'unified'},
        )
        
        return header
    
    def serialize_header(self, header: HeaderData) -> bytes:
        """序列化头部数据为 JSON 字节
        
        Args:
            header: 头部数据
            
        Returns:
            bytes: JSON 字节数据
        """
        logger = get_stage_logger(LogStage.HEADER)
        
        try:
            # 手动构建字典，避免 asdict 的问题
            header_dict = {
                'magic': header.magic,
                'schema_version': header.schema_version,
                'product': header.product,
                'ui': header.ui,
                'install': header.install,
                'compression': header.compression,
                'files': header.files,
                'scripts': header.scripts,
                'env': header.env,
                'hash': {
                    'algorithm': header.hash.algorithm,
                    'archive': header.hash.archive,
                    'header': header.hash.header
                },
                'build': {
                    'timestamp': header.build.timestamp,
                    'builder_version': header.build.builder_version,
                    'config_fingerprint': header.build.config_fingerprint
                },
                'stats': header.stats,
                'runtime': header.runtime,
            }
            
            # 使用自定义编码器序列化为 JSON（紧凑格式）
            json_str = json.dumps(
                header_dict, 
                ensure_ascii=False, 
                separators=(',', ':'),
                cls=PathJSONEncoder
            )
            
            return json_str.encode('utf-8')
        except Exception as e:
            logger.error("头部序列化失败", error=str(e), traceback=traceback.format_exc())
            # 额外调试信息
            logger.debug("头部数据类型检查",
                        magic_type=type(header.magic),
                        product_type=type(header.product),
                        files_type=type(header.files),
                        hash_type=type(header.hash))
            raise
    
    def _convert_paths_to_strings(self, obj):
        """递归转换 Path 对象为字符串"""
        if isinstance(obj, Path):
            return str(obj).replace('\\', '/')
        elif isinstance(obj, dict):
            return {key: self._convert_paths_to_strings(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_paths_to_strings(item) for item in obj]
        else:
            return obj
    
    def deserialize_header(self, data: bytes) -> HeaderData:
        """反序列化头部数据
        
        Args:
            data: JSON 字节数据
            
        Returns:
            HeaderData: 头部数据
            
        Raises:
            ValueError: 反序列化失败
        """
        try:
            json_str = data.decode('utf-8')
            header_dict = json.loads(json_str)
            
            # 验证魔术字符串
            if header_dict.get('magic') != self.MAGIC:
                raise ValueError("无效的魔术字符串")
            
            # 验证 schema 版本
            if header_dict.get('schema_version') != self.SCHEMA_VERSION:
                raise ValueError(f"不支持的 schema 版本: {header_dict.get('schema_version')}")
            
            # 重建对象
            hash_info = HashInfo(**header_dict['hash'])
            build_info = BuildInfo(**header_dict['build'])
            
            header = HeaderData(
                magic=header_dict['magic'],
                schema_version=header_dict['schema_version'],
                product=header_dict['product'],
                ui=header_dict['ui'],
                install=header_dict['install'],
                compression=header_dict['compression'],
                files=header_dict['files'],
                scripts=header_dict['scripts'],
                env=header_dict.get('env'),
                hash=hash_info,
                build=build_info
            )
            
            return header
            
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as e:
            raise ValueError(f"头部数据反序列化失败: {e}")
    
    def _calculate_config_fingerprint(self, config: InspaConfig) -> str:
        """计算配置指纹
        
        Args:
            config: 配置对象
            
        Returns:
            str: 配置指纹（SHA-256）
        """
        # 提取影响构建结果的关键配置
        config_data = {
            'product': config.product.model_dump(),
            'inputs': [input_path.model_dump() for input_path in config.inputs],
            'exclude': config.exclude or [],
            'compression': config.compression.model_dump(),
            'post_actions': [action.model_dump() for action in config.post_actions or []],
            'env': config.env.model_dump() if config.env else None,
        }
        
        # 序列化为 JSON 并计算哈希，使用自定义编码器处理 Path 对象
        json_str = json.dumps(
            config_data, 
            sort_keys=True, 
            ensure_ascii=False, 
            separators=(',', ':'),
            cls=PathJSONEncoder
        )
        return HashCalculator.hash_data(json_str)
    
    def _build_product_info(self, config: InspaConfig) -> Dict[str, Any]:
        """构建产品信息"""
        return {
            'name': config.product.name,
            'version': config.product.version,
            'company': config.product.company,
            'description': config.product.description,
            'copyright': config.product.copyright,
            'website': config.product.website,
        }
    
    def _build_ui_info(self, config: InspaConfig) -> Dict[str, Any]:
        """构建 UI 信息"""
        return {
            'window_title': config.get_window_title(),
            'welcome_heading': config.get_welcome_heading(),
            'welcome_subtitle': config.get_welcome_subtitle(),
            'theme': config.ui.theme,
            'show_progress_script_output': config.ui.show_progress_script_output,
        }
    
    def _build_install_info(self, config: InspaConfig) -> Dict[str, Any]:
        """构建安装信息"""
        return {
            'default_path': config.install.default_path,
            'allow_user_path': config.install.allow_user_path,
            'force_hidden_path': config.install.force_hidden_path,
            'show_ui': config.install.show_ui,
            'silent_allowed': config.install.silent_allowed,
            'require_admin': config.install.require_admin,
            'license_file': str(config.install.license_file) if config.install.license_file else None,
            'privacy_file': str(config.install.privacy_file) if config.install.privacy_file else None,
        }
    
    def _build_compression_info(self, config: InspaConfig, actual_algo: CompressionAlgorithm) -> Dict[str, Any]:
        """构建压缩信息"""
        return {
            'algo': actual_algo.value,  # 使用实际使用的算法
            'level': config.compression.level,
            'fallback_to_zip': config.compression.fallback_to_zip,
        }
    
    def _build_file_list(self, files: List[FileInfo]) -> List[Dict[str, Any]]:
        """构建文件列表"""
        return [file_info.to_dict() for file_info in files]
    
    def _build_script_list(self, config: InspaConfig) -> List[Dict[str, Any]]:
        """构建脚本列表"""
        if not config.post_actions:
            return []
        
        return [
            {
                'type': action.type.value,
                'command': action.command,
                'args': action.args or [],
                'hidden': action.hidden,
                'timeout_sec': action.timeout_sec,
                'show_in_ui': action.show_in_ui,
                'run_if': action.run_if.value,
                'working_dir': str(action.working_dir) if action.working_dir else None,
            }
            for action in config.post_actions
        ]
    
    def _build_env_info(self, config: InspaConfig) -> Optional[Dict[str, Any]]:
        """构建环境变量信息"""
        if not config.env:
            return None
        
        return {
            'add_path': config.env.add_path or [],
            'set': config.env.set or {},
            'system_scope': config.env.system_scope,
        }


def calculate_archive_hash(data: bytes, algorithm: str = "sha256") -> str:
    """计算归档数据哈希
    
    Args:
        data: 归档数据
        algorithm: 哈希算法
        
    Returns:
        str: 十六进制哈希值
    """
    return HashCalculator.hash_data(data, algorithm)