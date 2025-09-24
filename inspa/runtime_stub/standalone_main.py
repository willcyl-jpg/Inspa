"""
Runtime Stub - 独立版本

这是一个可以独立编译的 runtime stub，不依赖 inspa 包的其他部分。
用于创建自解压安装器的可执行部分。
"""

import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Inspa 安装器",
        add_help=False
    )
    
    parser.add_argument(
        "-S", "--silent", 
        action="store_true",
        help="静默安装模式"
    )
    
    parser.add_argument(
        "-D", "--dir",
        type=str,
        help="自定义安装目录"
    )
    
    return parser.parse_args()


class InstallerRuntime:
    """安装器运行时"""
    
    def __init__(self, installer_path: Path):
        self.installer_path = installer_path
        self.header_data: Optional[Dict[str, Any]] = None
        
    def run_installation(
        self, 
        silent: bool = False, 
        custom_install_dir: Optional[str] = None
    ) -> bool:
        """运行安装"""
        try:
            print("正在解析安装器...")
            
            # 解析安装器文件
            self._parse_installer()
            
            if not self.header_data:
                print("错误: 无法解析安装器头部")
                return False
            
            # 确定安装目录
            install_dir = self._determine_install_dir(custom_install_dir)
            print(f"安装目录: {install_dir}")
            
            # 创建安装目录
            install_dir.mkdir(parents=True, exist_ok=True)
            
            # 解压文件
            self._extract_files(install_dir)
            
            # 运行安装脚本（如果有）
            self._run_install_scripts(install_dir)
            
            if not silent:
                print("安装完成！")
            
            return True
            
        except Exception as e:
            print(f"安装失败: {e}")
            return False
    
    def _parse_installer(self) -> None:
        """解析安装器文件"""
        with open(self.installer_path, 'rb') as f:
            # 跳过 stub 部分 - 找到头部长度标记
            # 格式: [stub_exe][header_len:8][header][compressed_data][hash:32]
            
            # 从文件末尾开始读取
            f.seek(-32, 2)  # 文件末尾的 32 字节是哈希
            file_size = f.tell() + 32
            
            # 寻找头部长度信息
            # 在实际实现中，我们需要更复杂的解析逻辑
            # 这里简化处理
            stub_size = 1088  # 当前 stub 的大小（MZ + PE + 1024 字节）
            
            f.seek(stub_size)
            header_len_bytes = f.read(8)
            header_len = struct.unpack('<Q', header_len_bytes)[0]
            
            # 读取头部
            header_bytes = f.read(header_len)
            self.header_data = json.loads(header_bytes.decode('utf-8'))
            
            # 读取压缩数据
            remaining_size = file_size - f.tell() - 32
            self.compressed_data = f.read(remaining_size)
    
    def _determine_install_dir(self, custom_dir: Optional[str]) -> Path:
        """确定安装目录"""
        if custom_dir:
            return Path(custom_dir)
        
        # 使用配置中的默认路径或程序文件目录
        if self.header_data and 'config' in self.header_data:
            config = self.header_data['config']
            if 'install' in config and 'default_path' in config['install']:
                return Path(config['install']['default_path'])
        
        # 默认安装到当前目录的子文件夹
        return Path.cwd() / "installed_app"
    
    def _extract_files(self, install_dir: Path) -> None:
        """解压文件"""
        print("正在解压文件...")
        
        if not self.compressed_data:
            raise Exception("没有压缩数据可解压")
        
        # 创建临时文件来处理压缩数据
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(self.compressed_data)
            temp_file_path = temp_file.name
        
        try:
            # 解压 ZIP 文件
            with zipfile.ZipFile(temp_file_path, 'r') as zip_file:
                zip_file.extractall(install_dir)
            
            print(f"文件解压完成到: {install_dir}")
        finally:
            # 清理临时文件
            os.unlink(temp_file_path)
    
    def _run_install_scripts(self, install_dir: Path) -> None:
        """运行安装脚本"""
        if not self.header_data or 'config' not in self.header_data:
            return
        
        config = self.header_data['config']
        
        # 运行安装后脚本
        if 'install' in config and 'post_install_script' in config['install']:
            script_name = config['install']['post_install_script']
            script_path = install_dir / script_name
            
            if script_path.exists():
                print(f"运行安装脚本: {script_name}")
                try:
                    if script_path.suffix.lower() == '.bat':
                        subprocess.run([str(script_path)], cwd=install_dir, check=True)
                    elif script_path.suffix.lower() == '.ps1':
                        subprocess.run(['powershell', '-File', str(script_path)], cwd=install_dir, check=True)
                    else:
                        subprocess.run([str(script_path)], cwd=install_dir, check=True)
                    print("脚本执行完成")
                except subprocess.CalledProcessError as e:
                    print(f"脚本执行失败: {e}")


def main() -> int:
    """主入口函数"""
    args = parse_arguments()
    
    try:
        # 获取当前可执行文件路径
        if getattr(sys, 'frozen', False):
            # PyInstaller 编译后的环境
            installer_path = Path(sys.executable)
        else:
            installer_path = Path(sys.argv[0])
        
        # 创建运行时实例并运行
        runtime = InstallerRuntime(installer_path)
        success = runtime.run_installation(
            silent=args.silent,
            custom_install_dir=args.dir
        )
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("安装被用户中断")
        return 2
    except Exception as e:
        print(f"安装过程发生异常: {e}")
        return 3


if __name__ == "__main__":
    sys.exit(main())