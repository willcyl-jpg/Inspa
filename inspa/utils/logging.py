"""
日志工具 - 统一输出门面

提供高性能、带日期的统一输出接口，封装底层的 Rich Console 和标准输出。
映射需求：FR-LOG-001, FR-LOG-002, FR-LOG-004, FR-LOG-005
"""

import sys
import threading
import time
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Optional, Union, Any, Dict

try:
    from rich.console import Console
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:  # 兜底，避免运行环境未装 rich
    Console = None  # type: ignore
    Text = None  # type: ignore
    RICH_AVAILABLE = False


class OutputLevel:
    """输出级别常量"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogStage:
    """日志阶段标记（保持向下兼容）"""
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


class HighPerformanceOutputFacade:
    """高性能输出门面
    
    统一封装所有输出操作，内部使用最佳的输出流实现。
    所有输出都包含时间戳，支持彩色输出。
    """
    
    def __init__(self):
        self._lock = threading.RLock()  # 线程安全
        self._console = None  # type: Optional[object]
        self._file_handle = None  # type: Optional[Any]
        self._log_level = OutputLevel.INFO
        self._date_format = "%Y-%m-%d %H:%M:%S"
        self._time_format = "%H:%M:%S"
        
        # 初始化 Rich Console（如果可用）
        if RICH_AVAILABLE:
            # 使用性能最好的配置
            self._console = Console(
                file=sys.stdout,
                width=None,  # 自动检测
                legacy_windows=False,  # 现代 Windows 支持
                force_terminal=None,  # 自动检测
                force_jupyter=False,
                force_interactive=None,  # 自动检测
                color_system="auto",  # 自动检测颜色支持
                markup=True,
                emoji=True,
                highlight=False,  # 关闭语法高亮以提高性能
                log_time=False,  # 我们自己管理时间
                log_path=False,  # 不显示路径
                _environ=None,
            )
        
        # 确保控制台使用 UTF-8 编码
        self._setup_console_encoding()
    
    def _setup_console_encoding(self):
        """设置控制台编码为 UTF-8"""
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
        
        if hasattr(sys.stderr, 'reconfigure'):
            try:
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
    
    def _get_timestamp(self, include_date: bool = False) -> str:
        """获取格式化的时间戳"""
        now = datetime.now()
        if include_date:
            return now.strftime(self._date_format)
        return now.strftime(self._time_format)
    
    def _should_output(self, level: str) -> bool:
        """判断是否应该输出该级别的消息"""
        level_order = {
            OutputLevel.DEBUG: 0,
            OutputLevel.INFO: 1,
            OutputLevel.SUCCESS: 1,
            OutputLevel.WARNING: 2,
            OutputLevel.ERROR: 3
        }
        
        current_level = level_order.get(self._log_level, 1)
        msg_level = level_order.get(level, 1)
        return msg_level >= current_level
    
    def _format_message(self, message: str, level: str = OutputLevel.INFO, 
                       stage: Optional[str] = None, include_date: bool = False) -> str:
        """格式化消息"""
        timestamp = self._get_timestamp(include_date)
        
        if stage:
            return f"[{timestamp}] [{level}] [{stage}] {message}"
        else:
            return f"[{timestamp}] [{level}] {message}"
    
    def _output_rich(self, message: str, level: str = OutputLevel.INFO, 
                    stage: Optional[str] = None, **kwargs):
        """使用 Rich 输出（带颜色）"""
        if not self._console:
            return self._output_plain(message, level, stage)
        
        # Rich 输出时使用不同的颜色
        level_styles = {
            OutputLevel.DEBUG: "dim",
            OutputLevel.INFO: "default",
            OutputLevel.SUCCESS: "green",
            OutputLevel.WARNING: "yellow",
            OutputLevel.ERROR: "red bold"
        }
        
        timestamp = self._get_timestamp()
        style = level_styles.get(level, "default")
        
        if stage:
            formatted_msg = f"[dim]{timestamp}[/dim] [bold]{level}[/bold] [cyan]{stage}[/cyan] {message}"
        else:
            formatted_msg = f"[dim]{timestamp}[/dim] [bold]{level}[/bold] {message}"
        
        try:
            self._console.print(formatted_msg, style=style, **kwargs)
        except Exception:
            # 如果 Rich 输出失败，回退到普通输出
            self._output_plain(message, level, stage)
    
    def _output_plain(self, message: str, level: str = OutputLevel.INFO, 
                     stage: Optional[str] = None):
        """使用标准输出（无颜色）"""
        formatted = self._format_message(message, level, stage)
        
        try:
            # 直接写入 stdout，性能最好
            sys.stdout.write(formatted + "\n")
            sys.stdout.flush()
        except Exception:
            # 极端情况下的兜底
            print(formatted)
    
    def set_level(self, level: str):
        """设置输出级别"""
        with self._lock:
            if level in [OutputLevel.DEBUG, OutputLevel.INFO, OutputLevel.WARNING, OutputLevel.ERROR]:
                self._log_level = level
    
    def set_log_file(self, file_path: Union[str, Path]):
        """设置日志文件"""
        with self._lock:
            if self._file_handle:
                try:
                    self._file_handle.close()
                except Exception:
                    pass
            
            try:
                log_path = Path(file_path)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                self._file_handle = open(log_path, 'a', encoding='utf-8-sig')  # 使用 UTF-8 BOM
            except Exception as e:
                self.warning(f"无法打开日志文件 {file_path}: {e}")
    
    def _write_to_file(self, message: str, level: str, stage: Optional[str] = None):
        """写入日志文件"""
        if not self._file_handle:
            return
        
        try:
            formatted = self._format_message(message, level, stage, include_date=True)
            self._file_handle.write(formatted + "\n")
            self._file_handle.flush()
        except Exception:
            pass  # 文件写入失败不应该影响程序运行
    
    def debug(self, message: str, stage: Optional[str] = None, **kwargs):
        """调试信息"""
        if not self._should_output(OutputLevel.DEBUG):
            return
        
        with self._lock:
            if RICH_AVAILABLE and self._console:
                self._output_rich(message, OutputLevel.DEBUG, stage, **kwargs)
            else:
                self._output_plain(message, OutputLevel.DEBUG, stage)
            
            self._write_to_file(message, OutputLevel.DEBUG, stage)
    
    def info(self, message: str, stage: Optional[str] = None, **kwargs):
        """普通信息"""
        if not self._should_output(OutputLevel.INFO):
            return
            
        with self._lock:
            if RICH_AVAILABLE and self._console:
                self._output_rich(message, OutputLevel.INFO, stage, **kwargs)
            else:
                self._output_plain(message, OutputLevel.INFO, stage)
            
            self._write_to_file(message, OutputLevel.INFO, stage)
    
    def success(self, message: str, stage: Optional[str] = None, **kwargs):
        """成功信息"""
        if not self._should_output(OutputLevel.SUCCESS):
            return
            
        with self._lock:
            if RICH_AVAILABLE and self._console:
                self._output_rich(message, OutputLevel.SUCCESS, stage, **kwargs)
            else:
                self._output_plain(message, OutputLevel.SUCCESS, stage)
            
            self._write_to_file(message, OutputLevel.SUCCESS, stage)
    
    def warning(self, message: str, stage: Optional[str] = None, **kwargs):
        """警告信息"""
        if not self._should_output(OutputLevel.WARNING):
            return
            
        with self._lock:
            if RICH_AVAILABLE and self._console:
                self._output_rich(message, OutputLevel.WARNING, stage, **kwargs)
            else:
                self._output_plain(message, OutputLevel.WARNING, stage)
            
            self._write_to_file(message, OutputLevel.WARNING, stage)
    
    def error(self, message: str, stage: Optional[str] = None, **kwargs):
        """错误信息"""
        if not self._should_output(OutputLevel.ERROR):
            return
            
        with self._lock:
            # 错误输出到 stderr
            if RICH_AVAILABLE and self._console:
                error_console = Console(file=sys.stderr, width=self._console.width if self._console else None)
                timestamp = self._get_timestamp()
                
                if stage:
                    formatted_msg = f"[dim]{timestamp}[/dim] [bold red]ERROR[/bold red] [cyan]{stage}[/cyan] {message}"
                else:
                    formatted_msg = f"[dim]{timestamp}[/dim] [bold red]ERROR[/bold red] {message}"
                    
                try:
                    error_console.print(formatted_msg, **kwargs)
                except Exception:
                    sys.stderr.write(self._format_message(message, OutputLevel.ERROR, stage) + "\n")
                    sys.stderr.flush()
            else:
                sys.stderr.write(self._format_message(message, OutputLevel.ERROR, stage) + "\n")
                sys.stderr.flush()
            
            self._write_to_file(message, OutputLevel.ERROR, stage)
    
    def raw_print(self, *args, **kwargs):
        """原生 print 函数的包装，保持 Rich Console 兼容性"""
        with self._lock:
            if RICH_AVAILABLE and self._console:
                self._console.print(*args, **kwargs)
            else:
                print(*args, **kwargs)
    
    def close(self):
        """关闭输出门面"""
        with self._lock:
            if self._file_handle:
                try:
                    self._file_handle.close()
                except Exception:
                    pass
                self._file_handle = None


# 全局输出门面实例
_output_facade: Optional[HighPerformanceOutputFacade] = None


def get_output_facade() -> HighPerformanceOutputFacade:
    """获取全局输出门面实例"""
    global _output_facade
    if _output_facade is None:
        _output_facade = HighPerformanceOutputFacade()
    return _output_facade


# 便捷的全局函数，统一所有输出接口
def debug(message: str, stage: Optional[str] = None, **kwargs):
    """调试信息输出"""
    get_output_facade().debug(message, stage, **kwargs)


def info(message: str, stage: Optional[str] = None, **kwargs):
    """普通信息输出"""
    get_output_facade().info(message, stage, **kwargs)


def success(message: str, stage: Optional[str] = None, **kwargs):
    """成功信息输出"""
    get_output_facade().success(message, stage, **kwargs)


def warning(message: str, stage: Optional[str] = None, **kwargs):
    """警告信息输出"""
    get_output_facade().warning(message, stage, **kwargs)


def error(message: str, stage: Optional[str] = None, **kwargs):
    """错误信息输出"""
    get_output_facade().error(message, stage, **kwargs)


def print(*args, **kwargs):
    """统一的 print 函数替代"""
    get_output_facade().raw_print(*args, **kwargs)


def set_log_level(level: str):
    """设置全局日志级别"""
    get_output_facade().set_level(level)


def set_log_file(file_path: Union[str, Path]):
    """设置全局日志文件"""
    get_output_facade().set_log_file(file_path)


def close_logger():
    """关闭日志系统"""
    global _output_facade
    if _output_facade:
        _output_facade.close()
        _output_facade = None


# 为了向下兼容，保留一些旧的接口
class StageLogger:
    """阶段日志器（向下兼容）"""
    
    def __init__(self, stage: str, name: Optional[str] = None):
        self.stage = stage
    
    def debug(self, message: str, **kwargs):
        debug(message, self.stage, **kwargs)
    
    def info(self, message: str, **kwargs):
        info(message, self.stage, **kwargs)
    
    def success(self, message: str, **kwargs):
        success(message, self.stage, **kwargs)
    
    def warning(self, message: str, **kwargs):
        warning(message, self.stage, **kwargs)
    
    def error(self, message: str, **kwargs):
        error(message, self.stage, **kwargs)
    
    def exception(self, message: str, **kwargs):
        # 异常信息包含在error中
        error(f"{message} (异常详情请查看日志)", self.stage, **kwargs)


def get_stage_logger(stage: str) -> StageLogger:
    """获取阶段日志器（向下兼容）"""
    return StageLogger(stage)


# 向下兼容的函数
def configure_logging(level: str = "INFO", log_file: Optional[Union[str, Path]] = None, **kwargs):
    """配置日志系统（向下兼容）"""
    set_log_level(level)
    if log_file:
        set_log_file(log_file)


# 便捷的阶段日志器实例（向下兼容）
init_logger = get_stage_logger(LogStage.INIT)
collect_logger = get_stage_logger(LogStage.COLLECT)
compress_logger = get_stage_logger(LogStage.COMPRESS)
hash_logger = get_stage_logger(LogStage.HASH)
header_logger = get_stage_logger(LogStage.HEADER)
stub_logger = get_stage_logger(LogStage.STUB)
write_logger = get_stage_logger(LogStage.WRITE)
done_logger = get_stage_logger(LogStage.DONE)


# 向下兼容的 logging 模块接口
def get_logger(name: Optional[str] = None):
    """获取标准库日志器（兼容性函数）"""
    # 返回一个包装器，将标准logging调用转换为我们的输出门面
    class LoggerWrapper:
        def debug(self, msg, *args, **kwargs):
            debug(str(msg) % args if args else str(msg))
        
        def info(self, msg, *args, **kwargs):
            info(str(msg) % args if args else str(msg))
        
        def warning(self, msg, *args, **kwargs):
            warning(str(msg) % args if args else str(msg))
        
        def error(self, msg, *args, **kwargs):
            error(str(msg) % args if args else str(msg))
        
        def exception(self, msg, *args, **kwargs):
            error(f"{str(msg) % args if args else str(msg)} (异常)")
    
    return LoggerWrapper()


# 模块级别的清理
import atexit
atexit.register(close_logger)