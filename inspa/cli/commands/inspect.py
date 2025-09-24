"""
Inspect 命令实现

检查安装器头信息的命令。
映射需求：FR-BLD-010, FR-CFG-004
"""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table


console = Console()


def inspect_command(
    installer: str = typer.Argument(..., help="安装器文件路径"),
    json_output: bool = typer.Option(False, "--json", help="输出 JSON 格式"),
    show_files: bool = typer.Option(False, "--files", help="显示文件列表"),
    show_scripts: bool = typer.Option(False, "--scripts", help="显示脚本信息")
) -> None:
    """检查安装器头信息
    
    显示安装器的元数据信息，包括产品信息、文件列表、脚本等。
    
    示例:
        inspa inspect installer.exe
        inspa inspect installer.exe --json
        inspa inspect installer.exe --files --scripts
    """
    installer_path = Path(installer)
    
    if not installer_path.exists():
        console.print(f"[red]安装器文件不存在: {installer_path}[/red]")
        raise typer.Exit(1)
    
    try:
        # 读取头信息 (这里需要实现实际的读取逻辑)
        header_data = _read_installer_header(installer_path)
        
        if json_output:
            # JSON 格式输出
            console.print(json.dumps(header_data, ensure_ascii=False, indent=2))
        else:
            # 人类可读格式
            _display_header_info(header_data, show_files, show_scripts)
            
    except Exception as e:
        console.print(f"[red]检查安装器失败: {e}[/red]")
        raise typer.Exit(1)


def _read_installer_header(installer_path: Path) -> dict:
    """读取安装器头信息
    
    这是一个占位函数，实际实现需要根据归档格式读取头部。
    """
    # TODO: 实现实际的头部读取逻辑
    # 这里返回一个示例数据
    return {
        "magic": "INSPRO1",
        "schema_version": 1,
        "product": {
            "name": "示例应用",
            "version": "1.0.0",
            "company": "示例公司"
        },
        "compression": {
            "algo": "zstd",
            "level": 10
        },
        "files": [
            {"path": "bin/app.exe", "size": 1024000, "mtime": 1699000000},
            {"path": "config/app.conf", "size": 2048, "mtime": 1699000000}
        ],
        "scripts": [
            {"type": "powershell", "command": "setup.ps1", "hidden": True}
        ],
        "build": {
            "timestamp": 1699000000,
            "builder_version": "0.1.0"
        }
    }


def _display_header_info(header_data: dict, show_files: bool, show_scripts: bool) -> None:
    """显示头信息（人类可读格式）"""
    console.print("[bold]安装器信息[/bold]")
    console.print()
    
    # 基本信息
    basic_table = Table(title="基本信息")
    basic_table.add_column("属性", style="cyan")
    basic_table.add_column("值", style="green")
    
    product = header_data.get("product", {})
    basic_table.add_row("产品名称", product.get("name", "未知"))
    basic_table.add_row("版本", product.get("version", "未知"))
    basic_table.add_row("公司", product.get("company", "未知"))
    basic_table.add_row("Magic", header_data.get("magic", ""))
    basic_table.add_row("Schema 版本", str(header_data.get("schema_version", "")))
    
    compression = header_data.get("compression", {})
    basic_table.add_row("压缩算法", compression.get("algo", "未知"))
    basic_table.add_row("压缩级别", str(compression.get("level", "")))
    
    console.print(basic_table)
    console.print()
    
    # 构建信息
    build = header_data.get("build", {})
    if build:
        build_table = Table(title="构建信息")
        build_table.add_column("属性", style="cyan")
        build_table.add_column("值", style="green")
        
        build_table.add_row("构建时间", str(build.get("timestamp", "")))
        build_table.add_row("构建器版本", build.get("builder_version", ""))
        
        console.print(build_table)
        console.print()
    
    # 文件列表
    if show_files:
        files = header_data.get("files", [])
        if files:
            files_table = Table(title=f"文件列表 ({len(files)} 个文件)")
            files_table.add_column("路径", style="cyan")
            files_table.add_column("大小", style="green")
            files_table.add_column("修改时间", style="yellow")
            
            for file_info in files:
                size_str = _format_file_size(file_info.get("size", 0))
                mtime_str = str(file_info.get("mtime", ""))
                files_table.add_row(
                    file_info.get("path", ""),
                    size_str,
                    mtime_str
                )
            
            console.print(files_table)
            console.print()
    
    # 脚本信息
    if show_scripts:
        scripts = header_data.get("scripts", [])
        if scripts:
            scripts_table = Table(title=f"脚本列表 ({len(scripts)} 个脚本)")
            scripts_table.add_column("类型", style="cyan")
            scripts_table.add_column("命令", style="green")
            scripts_table.add_column("隐藏", style="yellow")
            
            for script in scripts:
                scripts_table.add_row(
                    script.get("type", ""),
                    script.get("command", ""),
                    "是" if script.get("hidden", False) else "否"
                )
            
            console.print(scripts_table)
            console.print()


def _format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"