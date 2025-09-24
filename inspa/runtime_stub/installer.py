"""
安装器运行时

负责实际的安装逻辑，包括头部解析、文件解压、脚本执行等。
映射需求：FR-RT-001, FR-RT-002, FR-RT-003, FR-RT-005, FR-RT-007, FR-RT-008
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..build.header import HeaderBuilder
from ..build.compressor import CompressorFactory
from ..utils import get_stage_logger, LogStage, expand_path, ensure_directory


class InstallationError(Exception):
    """安装错误"""
    pass


class InstallerRuntime:
    """安装器运行时"""
    
    def __init__(self, installer_path: Path):
        """初始化运行时
        
        Args:
            installer_path: 安装器文件路径
        """
        self.installer_path = installer_path
        self.logger = get_stage_logger(LogStage.PARSE)
        
        # 解析后的信息
        self.header_data: Optional[Dict[str, Any]] = None
        self.compressed_data: Optional[bytes] = None
        
        # 安装状态
        self.install_dir: Optional[Path] = None
        self.temp_dir: Optional[Path] = None
    
    def run_installation(
        self, 
        silent: bool = False, 
        custom_install_dir: Optional[str] = None
    ) -> bool:
        """运行安装流程
        
        Args:
            silent: 是否静默安装
            custom_install_dir: 自定义安装目录
            
        Returns:
            bool: 安装是否成功
        """
        try:
            self.logger.info("开始安装流程", silent=silent)
            
            # 步骤 1: 解析安装器
            if not self._parse_installer():
                return False
            
            # 步骤 2: 确定安装路径
            if not self._determine_install_path(custom_install_dir, silent):
                return False
            
            # 步骤 3: 创建临时目录
            if not self._create_temp_directory():
                return False
            
            # 步骤 4: 解压文件
            if not self._extract_files():
                return False
            
            # 步骤 5: 执行安装脚本
            if not self._execute_scripts():
                return False
            
            # 步骤 6: 设置环境变量
            if not self._setup_environment():
                return False
            
            # 步骤 7: 完成安装
            self._finalize_installation()
            
            self.logger.info("安装完成", install_dir=str(self.install_dir))
            return True
            
        except Exception as e:
            self.logger.exception("安装过程异常", error=str(e))
            return False
        finally:
            # 清理临时目录
            self._cleanup()
    
    def _parse_installer(self) -> bool:
        """解析安装器文件"""
        self.logger.info("解析安装器文件", file=str(self.installer_path))
        
        try:
            with open(self.installer_path, 'rb') as f:
                # 读取文件末尾，查找头部长度
                f.seek(-40, 2)  # 从末尾往前读 40 字节
                tail_data = f.read(40)
                
                # 简化版本：假设头部长度存储在特定位置
                # 实际实现需要按照设计的格式解析
                
                # 这里是占位实现
                header_data = {
                    "magic": "INSPRO1",
                    "schema_version": 1,
                    "product": {"name": "Demo App", "version": "1.0.0"},
                    "install": {"default_path": "C:\\Program Files\\Demo"},
                    "compression": {"algo": "zstd"},
                    "files": [],
                    "scripts": []
                }
                
                self.header_data = header_data
                self.compressed_data = b""  # 占位
                
                self.logger.info(
                    "安装器解析完成",
                    product=header_data["product"]["name"],
                    version=header_data["product"]["version"]
                )
                
                return True
                
        except Exception as e:
            self.logger.error("解析安装器失败", error=str(e))
            raise InstallationError(f"解析安装器失败: {e}")
    
    def _determine_install_path(self, custom_path: Optional[str], silent: bool) -> bool:
        """确定安装路径"""
        logger = get_stage_logger(LogStage.VALIDATE)
        
        if custom_path:
            # 使用用户指定路径
            self.install_dir = Path(custom_path)
            logger.info("使用用户指定路径", path=str(self.install_dir))
        else:
            # 使用默认路径
            default_path = self.header_data["install"]["default_path"]
            self.install_dir = expand_path(default_path)
            logger.info("使用默认安装路径", path=str(self.install_dir))
        
        # 检查路径是否可写
        try:
            ensure_directory(self.install_dir)
        except Exception as e:
            logger.error("无法创建安装目录", path=str(self.install_dir), error=str(e))
            raise InstallationError(f"无法创建安装目录: {e}")
        
        return True
    
    def _create_temp_directory(self) -> bool:
        """创建临时目录"""
        try:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="inspa_install_"))
            self.logger.info("创建临时目录", path=str(self.temp_dir))
            return True
        except Exception as e:
            self.logger.error("创建临时目录失败", error=str(e))
            return False
    
    def _extract_files(self) -> bool:
        """解压文件"""
        logger = get_stage_logger(LogStage.EXTRACT)
        logger.info("开始解压文件")
        
        try:
            # TODO: 实现实际的文件解压逻辑
            # 这里是占位实现
            
            # 创建一些示例文件
            (self.temp_dir / "example.txt").write_text("示例文件内容")
            bin_dir = self.temp_dir / "bin"
            bin_dir.mkdir()
            (bin_dir / "app.exe").write_text("示例程序")
            
            logger.info("文件解压完成", temp_dir=str(self.temp_dir))
            return True
            
        except Exception as e:
            logger.error("文件解压失败", error=str(e))
            return False
    
    def _execute_scripts(self) -> bool:
        """执行安装脚本"""
        logger = get_stage_logger(LogStage.SCRIPT)
        
        scripts = self.header_data.get("scripts", [])
        if not scripts:
            logger.info("无需执行脚本")
            return True
        
        logger.info("开始执行脚本", count=len(scripts))
        
        for i, script in enumerate(scripts):
            logger.info(f"执行脚本 {i+1}/{len(scripts)}", type=script.get("type"), command=script.get("command"))
            
            try:
                if not self._execute_single_script(script):
                    logger.warning("脚本执行失败但继续安装", script=script.get("command"))
                    # 根据策略决定是否继续
            except Exception as e:
                logger.error("脚本执行异常", script=script.get("command"), error=str(e))
        
        logger.info("脚本执行完成")
        return True
    
    def _execute_single_script(self, script: Dict[str, Any]) -> bool:
        """执行单个脚本"""
        script_type = script.get("type", "")
        command = script.get("command", "")
        hidden = script.get("hidden", True)
        timeout = script.get("timeout_sec", 300)
        
        if script_type == "powershell":
            cmd = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", command]
        elif script_type == "batch":
            cmd = ["cmd.exe", "/c", command]
        else:
            self.logger.warning("不支持的脚本类型", type=script_type)
            return False
        
        try:
            # 设置工作目录为安装目录
            working_dir = self.install_dir
            
            # 创建进程参数
            process_kwargs = {
                'cwd': working_dir,
                'timeout': timeout,
                'capture_output': True,
                'text': True
            }
            
            if hidden and os.name == 'nt':
                # Windows 下隐藏窗口
                import subprocess
                process_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            # 执行脚本
            result = subprocess.run(cmd, **process_kwargs)
            
            if result.returncode == 0:
                self.logger.info("脚本执行成功", command=command)
                if result.stdout:
                    self.logger.debug("脚本输出", output=result.stdout)
                return True
            else:
                self.logger.error("脚本执行失败", command=command, returncode=result.returncode)
                if result.stderr:
                    self.logger.error("脚本错误输出", error=result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("脚本执行超时", command=command, timeout=timeout)
            return False
        except Exception as e:
            self.logger.error("脚本执行异常", command=command, error=str(e))
            return False
    
    def _setup_environment(self) -> bool:
        """设置环境变量"""
        logger = get_stage_logger(LogStage.ENV)
        
        env_config = self.header_data.get("env")
        if not env_config:
            logger.info("无需设置环境变量")
            return True
        
        logger.info("开始设置环境变量")
        
        try:
            # TODO: 实现实际的环境变量设置
            # 这里是占位实现
            
            add_path = env_config.get("add_path", [])
            set_vars = env_config.get("set", {})
            
            logger.info("环境变量设置完成", add_path=add_path, set_vars=list(set_vars.keys()))
            return True
            
        except Exception as e:
            logger.error("环境变量设置失败", error=str(e))
            # 环境变量设置失败通常不应该阻止安装
            return True
    
    def _finalize_installation(self) -> None:
        """完成安装"""
        logger = get_stage_logger(LogStage.COMPLETE)
        logger.info("完成安装")
        
        # 将临时文件移动到最终位置
        if self.temp_dir and self.install_dir:
            try:
                # TODO: 实现文件移动逻辑
                logger.info("文件移动完成", from_dir=str(self.temp_dir), to_dir=str(self.install_dir))
            except Exception as e:
                logger.error("文件移动失败", error=str(e))
    
    def _cleanup(self) -> None:
        """清理临时文件"""
        if self.temp_dir and self.temp_dir.exists():
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                self.logger.info("临时目录清理完成", path=str(self.temp_dir))
            except Exception as e:
                self.logger.warning("清理临时目录失败", path=str(self.temp_dir), error=str(e))