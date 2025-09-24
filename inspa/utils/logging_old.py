"""
日志工具

提供结构化日志功能，支持不同阶段的标记。
映射需求：FR-LOG-001, FR-LOG-002, FR-LOG-004, FR-LOG-005
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import structlog
try:
    from rich.logging import RichHandler
except ImportError:  # 兜底，避免运行环境未装 rich
    RichHandler = None  # type: ignore


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

    # 清理现有 handlers（避免和 RichHandler 混用导致进度条错乱）
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    # 确保控制台输出使用正确编码
    import sys
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
        # 使用 Rich Handler 并与进度条同步
        handler = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            show_level=True,
            show_path=False,
            markup=True,
            log_time_format=DEFAULT_TIME_FORMAT,
            omit_repeated_times=False,
            console=rich_console,  # 复用外部进度条 console，避免行错乱
        )
        handler.setLevel(target_level)
        root_logger.addHandler(handler)
    else:
        # 兜底简单格式，确保使用 UTF-8 编码
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        handler.setLevel(target_level)
        root_logger.addHandler(handler)
    
    # 配置 structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if json_format:
        processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ])
    else:
        # 当使用RichHandler时，禁用structlog的颜色输出避免冲突
        use_colors = enable_colors and sys.stdout.isatty() and (RichHandler is None or json_format)
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=use_colors)
        ])
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # 如果指定了日志文件，添加文件 handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(target_level)
        if json_format:
            file_handler.setFormatter(logging.Formatter("%(message)s"))
        else:
            file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        root_logger.addHandler(file_handler)

    setattr(root_logger, configured_flag, True)


def get_logger(name: Optional[str] = None, stage: Optional[str] = None) -> structlog.BoundLogger:
    """获取带阶段标记的日志器
    
    Args:
        name: 日志器名称
        stage: 阶段标记
        
    Returns:
        BoundLogger: 绑定的日志器
    """
    logger = structlog.get_logger(name or __name__)
    
    if stage:
        logger = logger.bind(stage=stage)
    
    return logger


class StageLogger:
    """阶段日志器
    
    提供带阶段标记的日志记录功能。
    """
    
    def __init__(self, stage: str, name: Optional[str] = None):
        self.stage = stage
        self.logger = get_logger(name, stage)
    
    def debug(self, message: str, **kwargs) -> None:
        """调试日志"""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """信息日志"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """警告日志"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """错误日志"""
        self.logger.error(message, **kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """异常日志（包含堆栈信息）"""
        self.logger.exception(message, **kwargs)
    
    def bind(self, **kwargs) -> 'StageLogger':
        """绑定额外的上下文"""
        new_logger = StageLogger(self.stage)
        new_logger.logger = self.logger.bind(**kwargs)
        return new_logger


# 预定义的阶段日志器
def get_stage_logger(stage: str) -> StageLogger:
    """获取阶段日志器"""
    return StageLogger(stage)


# 便捷的阶段日志器
init_logger = get_stage_logger(LogStage.INIT)
collect_logger = get_stage_logger(LogStage.COLLECT)
compress_logger = get_stage_logger(LogStage.COMPRESS)
hash_logger = get_stage_logger(LogStage.HASH)
header_logger = get_stage_logger(LogStage.HEADER)
stub_logger = get_stage_logger(LogStage.STUB)
write_logger = get_stage_logger(LogStage.WRITE)
done_logger = get_stage_logger(LogStage.DONE)