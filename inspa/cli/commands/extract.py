"""
Extract 命令实现

提取安装器内容的命令。
映射需求：FR-BLD-010, FR-CFG-005
"""

from pathlib import Path
import json
import struct
import zipfile
import io
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

FOOTER_MAGIC = b'INSPAF01'
FOOTER_SIZE = 8 + 8 + 8 + 8 + 8 + 32  # <8sQQQQ32s>


console = Console()


def extract_command(
    installer: str = typer.Argument(..., help="安装器文件路径"),
    output_dir: str = typer.Option("./extracted", "--dir", "-d", help="输出目录"),
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖已存在的文件")
) -> None:
    """提取安装器内容
    
    将安装器中的文件解压到指定目录。
    
    示例:
        inspa extract installer.exe
        inspa extract installer.exe -d output/
    """
    installer_path = Path(installer)
    output_path = Path(output_dir)
    
    if not installer_path.exists():
        console.print(f"[red]安装器文件不存在: {installer_path}[/red]")
        raise typer.Exit(1)
    
    if output_path.exists() and not force:
        if any(output_path.iterdir()):
            console.print(f"[red]输出目录不为空: {output_path}[/red]")
            console.print("使用 --force 参数强制覆盖")
            raise typer.Exit(1)
    
    try:
        console.print(f"正在提取安装器: [cyan]{installer_path}[/cyan]")
        console.print(f"输出目录: [cyan]{output_path}[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("提取中...", total=None)
            
            _extract_installer(installer_path, output_path, progress, task)
            
            console.print(f"✓ 提取完成: [green]{output_path}[/green]")
            
    except Exception as e:
        console.print(f"[red]提取失败: {e}[/red]")
        raise typer.Exit(1)


def _extract_installer(installer_path: Path, output_path: Path, progress, task) -> None:
    """真实提取实现 (zip 归档路径)"""
    with open(installer_path, 'rb') as f:
        f.seek(0, 2)
        file_size = f.tell()

        # Footer 快速路径
        header_offset = header_len = comp_offset = comp_size = None
        if file_size >= FOOTER_SIZE:
            f.seek(file_size - FOOTER_SIZE)
            footer = f.read(FOOTER_SIZE)
            try:
                magic, h_off, h_len, c_off, c_size, hash_bytes = struct.unpack('<8sQQQQ32s', footer)
                if magic == FOOTER_MAGIC:
                    header_offset, header_len = h_off, h_len
                    comp_offset, comp_size = c_off, c_size
            except struct.error:
                pass

        if header_offset is None:
            # 旧格式回退：末尾32字节 hash + 线性猜测
            f.seek(-32, 2)
            _tail_hash = f.read(32)
            found = False
            for guess in range(100*1024, file_size - 1024, 1024):
                f.seek(guess)
                len_bytes = f.read(8)
                if len(len_bytes) != 8:
                    continue
                hl = struct.unpack('<Q', len_bytes)[0]
                if 100 <= hl <= 100*1024:
                    c_size = file_size - 32 - guess - 8 - hl
                    if c_size > 0:
                        header_offset = guess
                        header_len = hl
                        comp_offset = guess + 8 + hl
                        comp_size = c_size
                        found = True
                        break
            if not found:
                raise ValueError('无法解析安装器结构')

        progress.update(task, description="读取头信息...")
        assert header_offset is not None and header_len is not None
        f.seek(int(header_offset))
        len_field = f.read(8)
        if len(len_field) != 8:
            raise ValueError('头长度字段损坏')
        recorded_len = struct.unpack('<Q', len_field)[0]
        if recorded_len != header_len:
            raise ValueError('头长度不一致')
        header_bytes = f.read(header_len)
        header = json.loads(header_bytes.decode('utf-8'))

        progress.update(task, description="读取压缩数据...")
        assert comp_offset is not None and comp_size is not None
        f.seek(int(comp_offset))
        comp_data = f.read(comp_size)

        algo = (header.get('compression') or {}).get('algo', 'zip')
        output_path.mkdir(parents=True, exist_ok=True)

        progress.update(task, description=f"解压 {algo} 数据...")
        if algo == 'zip':
            with zipfile.ZipFile(io.BytesIO(comp_data), 'r') as zf:
                zf.extractall(output_path)
        else:
            raise ValueError('当前 CLI 仅支持提取 zip 格式安装器 (zstd 解压稍后提供)')

        progress.update(task, description="完成")