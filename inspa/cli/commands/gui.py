"""
GUI 命令实现

启动图形界面的命令。
映射需求：FR-BGUI-001
"""

import typer
from rich.console import Console


console = Console()


def gui_command() -> None:
    """启动图形界面
    
    启动 Inspa 的图形用户界面，提供可视化的安装器构建功能。
    """
    try:
        console.print("正在启动图形界面...")
        
        # TODO: 实现实际的 GUI 启动逻辑
        from ...gui.main import launch_gui
        launch_gui()
        
    except ImportError:
        console.print("[red]GUI 依赖未安装或不可用[/red]")
        console.print("请安装 CustomTkinter: pip install customtkinter")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]启动 GUI 失败: {e}[/red]")
        raise typer.Exit(1)