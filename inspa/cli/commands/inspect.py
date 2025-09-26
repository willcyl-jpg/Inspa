"""
Inspect 命令实现

检查安装器头信息的命令。
映射需求：FR-BLD-010, FR-CFG-004
"""

import json
import struct
import hashlib
from pathlib import Path
from typing import Optional, Tuple

import typer
from rich.console import Console
from rich.table import Table

FOOTER_MAGIC = b'INSPAF01'
FOOTER_SIZE = 8 + 8 + 8 + 8 + 8 + 32  # <8sQQQQ32s>


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
    """读取安装器头部（支持 Footer 快速路径 + 旧格式回退）"""
    with open(installer_path, 'rb') as f:
        f.seek(0, 2)
        file_size = f.tell()

        # 优先 Footer
        if file_size >= FOOTER_SIZE:
            f.seek(file_size - FOOTER_SIZE)
            footer = f.read(FOOTER_SIZE)
            try:
                magic, header_offset, header_len, comp_offset, comp_size, hash_bytes = struct.unpack('<8sQQQQ32s', footer)
                if magic == FOOTER_MAGIC:
                    # 读取头部
                    f.seek(header_offset)
                    len_field = f.read(8)
                    if len(len_field) != 8:
                        raise ValueError('无法读取头长度字段')
                    recorded_len = struct.unpack('<Q', len_field)[0]
                    if recorded_len != header_len:
                        raise ValueError('头长度与 Footer 不匹配')
                    header_bytes = f.read(header_len)
                    data = json.loads(header_bytes.decode('utf-8'))
                    data['_locator'] = {
                        'mode': 'footer',
                        'header_offset': header_offset,
                        'header_len': header_len,
                        'compressed_offset': comp_offset,
                        'compressed_size': comp_size,
                        'archive_hash': hash_bytes.hex()
                    }
                    return data
            except struct.error:
                pass  # 回退

        # 旧格式回退：末尾32字节哈希，需扫描 stub 边界
        f.seek(-32, 2)
        tail_hash = f.read(32).hex()
        found = False
        stub_size = 0
        header_len = 0
        for guess in range(100*1024, file_size - 1024, 1024):
            f.seek(guess)
            len_bytes = f.read(8)
            if len(len_bytes) < 8:
                continue
            hl = struct.unpack('<Q', len_bytes)[0]
            if 100 <= hl <= 100*1024:
                comp_size = file_size - 32 - guess - 8 - hl
                if comp_size > 0:
                    found = True
                    stub_size = guess
                    header_len = hl
                    break
        if not found:
            raise ValueError('无法定位头部（旧格式回退失败）')
        f.seek(stub_size + 8)
        header_bytes = f.read(header_len)
        data = json.loads(header_bytes.decode('utf-8'))
        data['_locator'] = {
            'mode': 'legacy-scan',
            'stub_size': stub_size,
            'header_len': header_len,
            'tail_hash': tail_hash
        }
        return data


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

    stats = header_data.get('stats') or {}
    if stats:
        orig = stats.get('original_size')
        comp = stats.get('compressed_size')
        fc = stats.get('file_count')
        if orig is not None:
            basic_table.add_row("原始大小", _format_file_size(orig))
        if comp is not None:
            basic_table.add_row("压缩大小", _format_file_size(comp))
        if orig and comp:
            ratio = (1 - (comp / max(1, orig))) * 100
            basic_table.add_row("压缩率", f"{ratio:.1f}%")
        if fc is not None:
            basic_table.add_row("文件数", str(fc))

    locator = header_data.get('_locator')
    if locator:
        basic_table.add_row("定位模式", locator.get('mode', ''))
    
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