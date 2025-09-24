"""
Runtime Stub 主入口

安装器运行时的主要逻辑，负责解析头部、解压文件、执行脚本等。
映射需求：FR-RT-001, FR-RT-002, FR-RT-009, FR-RT-011
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

from .installer import InstallerRuntime
from ..utils import configure_logging, get_logger


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Inspa 安装器",
        add_help=False  # 禁用默认帮助，因为安装器不需要显示帮助
    )
    
    # 静默安装模式
    parser.add_argument(
        "/S", "--silent",
        action="store_true",
        help="静默安装模式（无界面）"
    )
    
    # 自定义安装路径
    parser.add_argument(
        "/D", "--dir",
        type=str,
        help="自定义安装目录"
    )
    
    # 日志级别
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别"
    )
    
    return parser.parse_args()


def main() -> int:
    """主入口函数
    
    Returns:
        int: 退出码，0 表示成功
    """
    args = parse_arguments()
    
    # 配置日志
    configure_logging(
        level=args.log_level,
        log_file=Path.cwd() / "install.log",
        enable_colors=not args.silent
    )
    
    logger = get_logger("runtime")
    logger.info("安装器启动", args=vars(args))
    
    try:
        # 获取当前可执行文件路径
        installer_path = Path(sys.executable)
        if not installer_path.exists():
            installer_path = Path(sys.argv[0])
        
        # 创建运行时实例
        runtime = InstallerRuntime(installer_path)
        
        # 执行安装
        success = runtime.run_installation(
            silent=args.silent,
            custom_install_dir=args.dir
        )
        
        if success:
            logger.info("安装成功完成")
            return 0
        else:
            logger.error("安装失败")
            return 1
            
    except KeyboardInterrupt:
        logger.info("安装被用户中断")
        return 2
    except Exception as e:
        logger.exception("安装过程发生异常", error=str(e))
        return 3


if __name__ == "__main__":
    sys.exit(main())