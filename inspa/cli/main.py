"""
Inspa CLI 主入口

提供命令行接口，支持 build/validate/inspect/extract 等命令。
映射需求：FR-BLD-010
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .. import __version__
from ..config import load_config, validate_config, validate_config_with_result, ConfigValidationError, ConfigError
from ..utils import configure_logging
from .commands import build, validate, inspect, extract, gui


# 创建主应用
app = typer.Typer(
    name="inspa",
    help="Inspa - Windows 单文件自解压安装器构建与运行系统",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,
)

# 控制台输出
console = Console()

# 全局选项
def version_callback(value: bool) -> None:
    """显示版本信息"""
    if value:
        console.print(f"Inspa v{__version__}")
        raise typer.Exit()


def verbose_callback(verbose: bool) -> None:
    """配置详细输出"""
    if verbose:
        configure_logging(level="DEBUG", enable_colors=True)
    else:
        configure_logging(level="INFO", enable_colors=True)


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, 
        "--version", 
        callback=version_callback,
        help="显示版本信息"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        callback=verbose_callback,
        help="启用详细输出"
    )
) -> None:
    """Inspa - Windows 单文件自解压安装器构建与运行系统
    
    使用 --help 查看可用命令的详细信息。
    """
    pass


# 注册子命令
app.command("build", help="构建安装器")(build.build_command)
app.command("validate", help="验证配置文件")(validate.validate_command)
app.command("inspect", help="检查安装器信息")(inspect.inspect_command)
app.command("extract", help="提取安装器内容")(extract.extract_command)
app.command("gui", help="启动图形界面")(gui.gui_command)


@app.command("info")
def info_command() -> None:
    """显示系统信息"""
    from ..build.compressor import CompressorFactory
    
    console.print("[bold]Inspa 系统信息[/bold]")
    console.print()
    
    # 版本信息
    table = Table(title="版本信息")
    table.add_column("组件", style="cyan")
    table.add_column("版本", style="green")
    
    table.add_row("Inspa", __version__)
    table.add_row("Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    console.print(table)
    console.print()
    
    # 支持的压缩算法
    algorithms = CompressorFactory.get_available_algorithms()
    algo_table = Table(title="支持的压缩算法")
    algo_table.add_column("算法", style="cyan")
    algo_table.add_column("状态", style="green")
    
    for algo in algorithms:
        status = "✓ 可用"
        if algo.value == "zstd":
            try:
                import zstandard
                status = f"✓ 可用 (zstandard {zstandard.__version__})"
            except ImportError:
                status = "✗ 不可用"
        algo_table.add_row(algo.value, status)
    
    console.print(algo_table)


@app.command("example")
def example_command(
    output: str = typer.Option(
        "example_config.yaml",
        "--output", "-o",
        help="输出配置文件路径"
    )
) -> None:
    """生成示例配置文件"""
    from ..config.schema import InspaConfig, ProductModel, InstallModel, InputPathModel
    
    # 创建示例配置
    config = InspaConfig(
        product=ProductModel(
            name="示例应用",
            version="1.0.0",
            company="示例公司",
            description="这是一个示例应用程序"
        ),
        install=InstallModel(
            default_path="%ProgramFiles%/ExampleApp",
            allow_user_path=True,
            license_file="./LICENSE.txt"
        ),
        inputs=[
            InputPathModel(path="./bin"),
            InputPathModel(path="./config")
        ],
        exclude=["*.pdb", "*.log", "__pycache__/"]
    )
    
    # 保存到文件
    from ..config import save_config
    
    try:
        save_config(config, output)
        console.print(f"✓ 示例配置文件已生成: [green]{output}[/green]")
        console.print("请根据需要修改配置文件，然后运行:")
        console.print(f"  [cyan]inspa build -c {output} -o installer.exe[/cyan]")
    except Exception as e:
        console.print(f"[red]生成示例配置失败: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()