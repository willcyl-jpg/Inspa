"""
Build 命令实现

构建安装器的核心命令。
映射需求：FR-BLD-004, FR-BLD-010, FR-BLD-014
"""

import traceback
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ...config import load_config, ConfigError, ConfigValidationError
from ...utils.logging import set_log_level, set_log_file, OutputLevel


console = Console()


def build_command(
    config: str = typer.Option(..., "--config", "-c", help="配置文件路径"),
    output: str = typer.Option(..., "--output", "-o", help="输出安装器路径"),
    icon: Optional[str] = typer.Option(None, "--icon", help="自定义图标文件 (.ico)"),
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖已存在的输出文件"),
    log_file: Optional[str] = typer.Option(None, "--log-file", help="日志输出文件"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="输出详细调试日志 (DEBUG 级别)"),
) -> None:
    """构建安装器
    
    从配置文件构建单文件自解压安装器。
    
    示例:
        inspa build -c config.yaml -o installer.exe
        inspa build -c config.yaml -o installer.exe --icon app.ico
    """
    from ...build.builder import Builder

    config_path = Path(config)
    output_path = Path(output)
    
    # 初始化日志：在任何输出前设置
    if verbose:
        set_log_level(OutputLevel.DEBUG)
    else:
        # 默认 INFO
        set_log_level(OutputLevel.INFO)

    if log_file:
        try:
            set_log_file(log_file)
        except Exception:
            console.print(f"[yellow]无法写入日志文件: {log_file}[/yellow]")

    # 检查输出文件
    if output_path.exists() and not force:
        console.print(f"[red]输出文件已存在: {output_path}[/red]")
        console.print("使用 --force 参数强制覆盖")
        raise typer.Exit(1)
    
    try:
        # 加载配置
        console.print(f"[cyan]正在加载配置文件[/cyan]: {config_path}")
        config_obj = load_config(config_path)

        # 统一运行时：不再区分 GUI / CLI 构建，始终包含 GUI 能力；运行时可用 --cli 参数强制命令行。
        console.print("[yellow]构建统一运行时 (含 GUI + CLI 双模式)\n[/yellow]")
        
        # 如果指定了图标，更新配置
        if icon:
            icon_path = Path(icon)
            if not icon_path.exists():
                console.print(f"[red]图标文件不存在: {icon_path}[/red]")
                raise typer.Exit(1)
            
            if not config_obj.resources:
                from ...config.schema import ResourcesModel
                # 显式传入 icon=None 以兼容某些静态分析器
                config_obj.resources = ResourcesModel(icon=None)
            config_obj.install.icon_path = icon_path
        
        # 创建构建器
        builder = Builder()
        
        # 开始构建
        console.print("[cyan]开始构建安装器...[/cyan]")
        if verbose:
            console.print("[dim]已启用详细模式 -- 将输出调试级日志[/dim]")
        
        def progress_callback(stage: str, current: int, total: int, message: str = "") -> None:
            """进度回调函数，显示进度"""
            if total > 0:
                percentage = (current / total) * 100
                if message:
                    console.print(f"[blue]{stage}[/blue]: {message} ({percentage:.0f}%)")
                else:
                    console.print(f"[blue]{stage}[/blue]: {percentage:.0f}%")
        
        try:
            result = builder.build(
                config_obj,
                output_path,
                progress_callback=progress_callback,
            )
            
            if result.success:
                # 构建成功消息
                console.print(f"[green]✓ 安装器构建完成[/green]: {output_path}")
                console.print(f"[blue]运行时类型[/blue]: unified (GUI/CLI 二合一)")

                # 原始文件名（用于显示/版本注入）: 优先使用 -o 提供的文件名，否则使用配置默认规则
                try:
                    if output_path:
                        original_filename = output_path.name
                    else:
                        # fallback: 从配置生成默认文件名
                        original_filename = f"{config_obj.product.name}_installer.exe"
                except Exception:
                    original_filename = f"{config_obj.product.name}_installer.exe"

                console.print(f"[blue]原始文件名[/blue]: {original_filename}")

                # 显示统计信息
                if output_path.exists():
                    size_mb = output_path.stat().st_size / (1024 * 1024)
                    console.print(f"[blue]文件大小[/blue]: {size_mb:.1f} MB")
            else:
                console.print(f"[red]✗ 构建失败[/red]: {result.error}")
                if log_file:
                    console.print(f"[yellow]请检查日志文件 {log_file} 获取详细信息。[/yellow]")
                raise typer.Exit(1)
            
        except Exception as e:
            console.print(f"[red]✗ 构建过程中发生意外错误[/red]: {e}")
            if log_file:  # 只有指定了日志文件才显示详细信息
                console.print(f"[yellow]详细错误信息:[/yellow]\n{traceback.format_exc()}")
            raise typer.Exit(1)
                
    except ConfigValidationError as e:
        console.print("[red]配置验证失败:[/red]")
        console.print(e.format_errors())
        raise typer.Exit(1)
    except ConfigError as e:
        console.print(f"[red]配置错误[/red]: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]构建失败[/red]: {e}")
        if log_file:
            console.print(f"[yellow]详细错误信息:[/yellow]\n{traceback.format_exc()}")
        raise typer.Exit(1)