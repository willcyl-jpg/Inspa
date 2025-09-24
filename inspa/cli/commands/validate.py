"""
Validate 命令实现

验证配置文件的命令。
映射需求：FR-BLD-010, FR-BLD-017
"""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ...config import validate_config, ConfigError, ConfigValidationError


console = Console()


def validate_command(
    config: str = typer.Option(..., "--config", "-c", help="配置文件路径"),
    json_output: bool = typer.Option(False, "--json", help="输出 JSON 格式的错误信息"),
    show_warnings: bool = typer.Option(True, "--warnings/--no-warnings", help="显示警告信息")
) -> None:
    """验证配置文件
    
    检查配置文件的语法和语义正确性。
    
    示例:
        inspa validate -c config.yaml
        inspa validate -c config.yaml --json
    """
    config_path = Path(config)
    
    if not config_path.exists():
        console.print(f"[red]配置文件不存在: {config_path}[/red]")
        raise typer.Exit(1)
    
    try:
        console.print(f"正在验证配置文件: [cyan]{config_path}[/cyan]")
        
        # 验证配置
        errors = validate_config(config_path)
        
        if not errors:
            console.print("[green]✓ 配置文件验证通过[/green]")
            return
        
        # 有错误
        if json_output:
            # JSON 格式输出
            error_data = {
                "file": str(config_path),
                "errors": errors,
                "error_count": len(errors)
            }
            console.print(json.dumps(error_data, ensure_ascii=False, indent=2))
        else:
            # 人类可读格式
            console.print(f"[red]配置文件验证失败 ({len(errors)} 个错误):[/red]")
            console.print()
            
            # 创建错误表格
            table = Table(title="验证错误")
            table.add_column("位置", style="cyan", no_wrap=True)
            table.add_column("错误信息", style="red")
            table.add_column("输入值", style="yellow")
            
            for error in errors:
                location = " -> ".join(str(item) for item in error.get('loc', []))
                message = error.get('msg', '未知错误')
                input_value = str(error.get('input', ''))[:50]  # 限制长度
                
                if len(input_value) > 47:
                    input_value = input_value[:47] + "..."
                
                table.add_row(
                    location or "根级别",
                    message,
                    input_value or "-"
                )
            
            console.print(table)
        
        raise typer.Exit(1)
        
    except ConfigError as e:
        if json_output:
            error_data = {
                "file": str(config_path),
                "error": str(e),
                "error_type": "config_error"
            }
            console.print(json.dumps(error_data, ensure_ascii=False, indent=2))
        else:
            console.print(f"[red]配置错误: {e}[/red]")
        
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]验证失败: {e}[/red]")
        raise typer.Exit(1)