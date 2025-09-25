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
        
        # 导入并检查 GUI 可用性
        from ...gui import GUI_AVAILABLE, BuilderGUI
        
        if not GUI_AVAILABLE:
            console.print("[red]GUI 依赖未安装或不可用[/red]")
            console.print("请安装 CustomTkinter: pip install customtkinter")
            raise typer.Exit(1)
        
        # 启动 Builder GUI
        app = BuilderGUI()
        app.run()
        
    except ImportError as e:
        console.print("[red]GUI 依赖未安装或不可用[/red]")
        console.print("请安装 CustomTkinter: pip install customtkinter")
        console.print(f"详细错误: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]启动 GUI 失败: {e}[/red]")
        raise typer.Exit(1)