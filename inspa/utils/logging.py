"""
日志工具

提供结构化日志功能，支持不同阶段的标记。
映射需求：FR-LOG-001, FR-LOG-002, FR-LOG-004, FR-LOG-005
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Union

try:
    from rich.logging import RichHandler
    from rich.console import Console
except ImportError:  # 兜底，避免运行环境未装 rich
    RichHandler = None  # type: ignore
    Console = None  # type: ignore


# 日志阶段常量
class LogStage:
    """日志阶段标记"""
    INIT = "INIT"
    COLLECT = "COLLECT"
    COMPRESS = "COMPRESS"
    HASH = "HASH"
    HEADER = "HEADER"
    STUB = "STUB"
    WRITE = "WRITE"
    DONE = "DONE"
    
    # Runtime 阶段
    PARSE = "PARSE"
    VALIDATE = "VALIDATE"
    EXTRACT = "EXTRACT"
    SCRIPT = "SCRIPT"
    ENV = "ENV"
    COMPLETE = "COMPLETE"
    
    # 错误阶段
    ERROR = "ERROR"
    WARNING = "WARNING"


DEFAULT_TIME_FORMAT = "%H:%M:%S"


class StageAwareFormatter(logging.Formatter):
    """阶段感知的日志格式器"""
    
    def format(self, record):
        # 从record中提取stage信息和额外参数
        stage = getattr(record, 'stage', '')
        extra_info = getattr(record, 'extra_info', '')
        
        # 基础格式化
        result = super().format(record)
        
        # 如果有额外信息，添加到输出中
        if extra_info:
            result = f"{result} {extra_info}"
        
        # 如果有stage信息，添加到输出中
        if stage:
            result = f"{result} stage={stage}"
        
        return result


def configure_logging(
    level: str = "INFO",
    log_file: Optional[Union[str, Path]] = None,
    json_format: bool = False,
    enable_colors: bool = True,
    rich_console: Optional[object] = None,
) -> None:
    """配置日志系统
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 日志文件路径
        json_format: 是否使用 JSON 格式
        enable_colors: 是否启用颜色输出
        rich_console: Rich console 实例，用于与进度条协同
    """
    # 配置标准库 logging
    root_logger = logging.getLogger()
    target_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(target_level)

    # 防止重复配置
    configured_flag = "__inspa_logging_configured__"
    if getattr(root_logger, configured_flag, False):
        return

    # 清理现有 handlers
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    # 确保控制台输出使用正确编码
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass

    handler: logging.Handler
    if RichHandler is not None and not json_format:
        # 使用独立的Console实例来避免与Progress冲突
        if rich_console is None:
            from rich.console import Console
            log_console = Console()
        else:
            # 创建一个新的Console实例，但使用相同的输出流
            from rich.console import Console
            log_console = Console(file=rich_console.file)
        
        handler = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            show_level=True,
            show_path=False,
            markup=True,
            log_time_format=DEFAULT_TIME_FORMAT,
            omit_repeated_times=False,
            console=log_console,  # 使用独立的console
        )
        handler.setLevel(target_level)
        root_logger.addHandler(handler)
    else:
        # 兜底简单格式
        handler = logging.StreamHandler(sys.stdout)
        formatter = StageAwareFormatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        handler.setLevel(target_level)
        root_logger.addHandler(handler)
    
    # 如果指定了日志文件，添加文件 handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(target_level)
        if json_format:
            file_handler.setFormatter(logging.Formatter("%(message)s"))
        else:
            file_handler.setFormatter(StageAwareFormatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        root_logger.addHandler(file_handler)

    setattr(root_logger, configured_flag, True)


class StageLogger:
    """阶段日志器
    
    提供带阶段标记的日志记录功能，基于标准库logging。
    """
    
    def __init__(self, stage: str, name: Optional[str] = None):
        self.stage = stage
        self.logger = logging.getLogger(name or __name__)
    
    def _format_extra_kwargs(self, **kwargs) -> str:
        """格式化额外的kwargs信息"""
        if not kwargs:
            return ""
        return " ".join(f"{k}={v}" for k, v in kwargs.items())
    
    def _log_with_stage(self, log_level: int, message: str, **kwargs) -> None:
        """带阶段信息的日志记录"""
        # 格式化额外信息
        extra_info = self._format_extra_kwargs(**kwargs)
        
        # 创建一个LogRecord，附加stage和额外信息
        extra = {
            'stage': self.stage,
            'extra_info': extra_info
        }
        
        self.logger.log(log_level, message, extra=extra)
    
    def debug(self, message: str, **kwargs) -> None:
        """调试日志"""
        self._log_with_stage(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """信息日志"""
        self._log_with_stage(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """警告日志"""
        self._log_with_stage(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """错误日志"""
        self._log_with_stage(logging.ERROR, message, **kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """异常日志（包含堆栈信息）"""
        extra_info = self._format_extra_kwargs(**kwargs)
        extra = {
            'stage': self.stage,
            'extra_info': extra_info
        }
        self.logger.exception(message, extra=extra)


# 预定义的阶段日志器
def get_stage_logger(stage: str) -> StageLogger:
    """获取阶段日志器"""
    return StageLogger(stage)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取标准库日志器（兼容性函数）"""
    return logging.getLogger(name or __name__)


# 便捷的阶段日志器
init_logger = get_stage_logger(LogStage.INIT)
collect_logger = get_stage_logger(LogStage.COLLECT)
compress_logger = get_stage_logger(LogStage.COMPRESS)
hash_logger = get_stage_logger(LogStage.HASH)
header_logger = get_stage_logger(LogStage.HEADER)
stub_logger = get_stage_logger(LogStage.STUB)
write_logger = get_stage_logger(LogStage.WRITE)
done_logger = get_stage_logger(LogStage.DONE)