"""
Runtime Stub编译步骤模块

负责编译或获取Runtime Stub。
映射需求：FR-BLD-004, FR-BLD-014, FR-BLD-015
"""

import importlib
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Optional

from ...utils import format_size
from ...utils.logging import info, success, error, warning, debug, LogStage
from inspa.build.build_context import BuildContext, BuildError
from .build_step import BuildStep


class StubCompilationStep(BuildStep):
    """Runtime Stub编译步骤"""

    def __init__(self):
        super().__init__("stub", "编译或获取Runtime Stub")

    def get_progress_range(self) -> tuple[int, int]:
        return (70, 85)

    def execute(self, context: BuildContext) -> None:
        """获取 Runtime Stub 数据"""
        info("获取Runtime Stub", stage=LogStage.STUB)

        try:
            if context.progress_callback:
                progress_start, progress_end = self.get_progress_range()
                context.progress_callback("组装文件", progress_start, 100, "生成 Runtime Stub...")

            stub_data = self._get_runtime_stub(context)
            context.stub_data = stub_data

            if context.progress_callback:
                progress_start, progress_end = self.get_progress_range()
                context.progress_callback("组装文件", progress_end, 100, "Runtime Stub准备完成")

        except Exception as e:
            error(f"获取Runtime Stub失败: {e}", stage=LogStage.STUB)
            error(f"详细错误信息:\n{traceback.format_exc()}")
            raise BuildError(f"无法获取 Runtime Stub: {e}")

    def _get_runtime_stub(self, context) -> bytes:
        """获取 Runtime Stub 数据"""
        config = context.config
        need_custom = bool(config.install.icon_path)
        # 版本信息始终需要注入
        need_custom = True  # 直接强制动态编译以便写入版本信息和图标

        try:
            # 首先尝试使用预编译的 stub
            if not need_custom:
                stub_path = Path(__file__).parent.parent / "runtime_stub" / "dist" / "stub.exe"
                if stub_path.exists():
                    info(f"使用预编译的Runtime Stub: {stub_path}", stage=LogStage.STUB)
                    stub_data = stub_path.read_bytes()
                    success(f"Runtime Stub准备完成 - 大小: {format_size(len(stub_data))}", stage=LogStage.STUB)
                    return stub_data

            # 如果没有预编译版本或需要定制，动态编译
            info("使用动态编译 Runtime Stub 以注入版本信息和图标", stage=LogStage.STUB)
            stub_data = self._compile_runtime_stub(context)
            success(f"Runtime Stub准备完成 - 大小: {format_size(len(stub_data))}", stage=LogStage.STUB)
            return stub_data

        except Exception as e:
            error(f"获取Runtime Stub失败: {e}", stage=LogStage.STUB)
            raise

    def _compile_runtime_stub(self, context) -> bytes:
        """动态编译 Runtime Stub"""
        import subprocess
        import tempfile
        import importlib

        config = context.config
        info("开始编译Runtime Stub", stage=LogStage.STUB)
        runtime_stub_dir = Path(__file__).parent.parent.parent / "runtime_stub"
        main_py = runtime_stub_dir / "installer.py"
        project_root = Path(__file__).parent.parent.parent.parent

        # 新的统一 spec 优先，其次兼容旧 gui 命名
        unified_spec = project_root / "inspa_runtime.spec"
        legacy_gui_spec = project_root / "inspa_runtime_gui.spec"
        chosen_spec = unified_spec if unified_spec.exists() else legacy_gui_spec if legacy_gui_spec.exists() else None
        use_spec = chosen_spec is not None

        if not main_py.exists():
            raise BuildError(f"Runtime stub 源文件不存在: {main_py}")

        # 检查 PyInstaller 可用性
        try:
            importlib.import_module("PyInstaller")  # noqa: F401
        except ImportError as e:
            raise BuildError(
                f"PyInstaller 未安装或不可用: {e}\n"
                "请运行以下命令安装: pip install pyinstaller>=6.0.0"
            ) from e

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_dir = temp_path / "dist"

            try:
                # 生成版本信息文件
                version_file = temp_path / "version_info.txt"
                version_info = config.get_version_info()

                # 根据输出文件名更新 OriginalFilename
                if context.output_path:
                    version_info['OriginalFilename'] = context.output_path.name
                def split_ver(v: str) -> str:
                    parts = [p for p in v.split('-')[0].split('.')][:4]
                    while len(parts) < 4:
                        parts.append('0')
                    return ','.join(parts)
                numeric_ver = split_ver(version_info['FileVersion'])
                version_lines = [
                    "# UTF-8\n",
                    "# Auto-generated version file\n",
                    "VSVersionInfo(\n",
                    "  ffi=FixedFileInfo(\n",
                    f"    filevers=({numeric_ver}),\n",
                    f"    prodvers=({numeric_ver}),\n",
                    "    mask=0x3f,\n",
                    "    flags=0x0,\n",
                    "    OS=0x4,\n",
                    "    fileType=0x1,\n",
                    "    subtype=0x0,\n",
                    "    date=(0, 0)\n",
                    "  ),\n",
                    "  kids=[\n",
                    "    StringFileInfo([\n",
                    "      StringTable(\n",
                    "        '040904B0',\n",
                    "        [\n",
                    f"          StringStruct('CompanyName', {version_info['CompanyName']!r}),\n",
                    f"          StringStruct('FileDescription', {version_info['FileDescription']!r}),\n",
                    f"          StringStruct('FileVersion', {version_info['FileVersion']!r}),\n",
                    f"          StringStruct('InternalName', {version_info['InternalName']!r}),\n",
                    f"          StringStruct('LegalCopyright', {version_info['LegalCopyright']!r}),\n",
                    f"          StringStruct('OriginalFilename', {version_info['OriginalFilename']!r}),\n",
                    f"          StringStruct('ProductName', {version_info['ProductName']!r}),\n",
                    f"          StringStruct('ProductVersion', {version_info['ProductVersion']!r}),\n",
                    "        ]\n",
                    "      )\n",
                    "    ]),\n",
                    "    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n",
                    "  ]\n",
                    ")\n"
                ]
                version_file.write_text(''.join(version_lines), encoding='utf-8')

                if use_spec and chosen_spec:
                    spec_name = getattr(chosen_spec, 'name', str(chosen_spec)) if chosen_spec else 'unknown.spec'
                    info(f"检测到 spec 文件: {spec_name}，将合并产品信息后编译", stage=LogStage.STUB)

                    # 读取原始spec文件
                    spec_content = chosen_spec.read_text(encoding='utf-8')

                    # 将脚本文件复制到临时目录
                    temp_script_path = temp_path / "installer.py"
                    import shutil
                    shutil.copy2(main_py, temp_script_path)

                    # 创建临时spec文件路径
                    temp_spec_file = temp_path / "temp_runtime.spec"

                    # 修改spec内容，更新脚本路径
                    modified_spec = self._modify_spec_content(spec_content, version_file, config, temp_script_path)

                    # 写入临时spec文件
                    temp_spec_file.write_text(modified_spec, encoding='utf-8')

                    # 使用临时spec编译
                    cmd = [
                        sys.executable,
                        "-m",
                        "PyInstaller",
                        str(temp_spec_file),
                        "--distpath", str(output_dir),
                        "--workpath", str(temp_path / "build"),
                    ]
                else:
                    info("未找到对应 spec 文件，回退到参数模式", stage=LogStage.STUB)
                    cmd = [
                        sys.executable,
                        "-m",
                        "PyInstaller",
                        "--onefile",
                        "--console",
                        "--distpath", str(output_dir),
                        "--workpath", str(temp_path / "build"),
                        "--specpath", str(temp_path),
                        "--name", "stub",
                        "--version-file", str(version_file),
                    ]

                # 处理UI和UAC设置（仅在非spec模式下）
                if not use_spec:
                    # 默认启用 UI（隐藏控制台窗口）
                    if "--console" in cmd:
                        cmd[cmd.index("--console")] = "--noconsole"
                        info("启用 UI: 隐藏控制台窗口", stage=LogStage.STUB)

                if not use_spec:
                    try:
                        if config.install.require_admin:
                            cmd.append("--uac-admin")
                            info("启用 UAC 提权", stage=LogStage.STUB)
                    except AttributeError:
                        warning("install.require_admin 未定义, 跳过 UAC", stage=LogStage.STUB)

                    if config.install.icon_path:
                        icon_path = str(config.install.icon_path)
                        cmd.extend(["--icon", icon_path])
                        info(f"添加图标: {icon_path}", stage=LogStage.STUB)

                    cmd.append(str(main_py))
                else:
                    debug("spec 模式：版本信息和图标已通过临时spec文件注入", stage=LogStage.STUB)

                info("执行 PyInstaller 编译...", stage=LogStage.STUB)
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(temp_path),
                    timeout=180,
                )

                if result.returncode != 0:
                    error("编译失败", stage=LogStage.STUB)
                    error(f"stderr: {result.stderr}")
                    info(f"stdout: {result.stdout}")
                    raise BuildError(f"PyInstaller 编译失败: {result.stderr}")

                # spec 模式下输出文件名可能在 spec 内定义；尝试推断
                if use_spec:
                    # 遍历 dist 目录取第一个 exe
                    candidates = list(output_dir.glob("*.exe"))
                    if not candidates:
                        raise BuildError("spec 编译完成但未找到任何 exe 输出")
                    stub_exe = candidates[0]
                else:
                    stub_exe = output_dir / "stub.exe"

                if not stub_exe.exists():
                    raise BuildError("编译完成但未找到输出文件")

                data = stub_exe.read_bytes()
                success(f"Runtime Stub编译完成 - 大小: {format_size(len(data))}", stage=LogStage.STUB)
                return data

            except subprocess.TimeoutExpired:
                raise BuildError("编译超时")
            except subprocess.CalledProcessError as e:
                raise BuildError(f"编译过程出错: {e}")
            except Exception as e:  # noqa: BLE001
                error(f"编译过程异常: {e}", stage=LogStage.STUB)
                error(f"详细错误信息:\n{traceback.format_exc()}")
                raise BuildError(f"编译 Runtime Stub 失败: {e}")

    def _modify_spec_content(self, spec_content: str, version_file: Path, config, script_path: Optional[Path] = None) -> str:
        """修改spec文件内容，添加version、icon和UAC信息"""
        import re

        modified_content = spec_content

        # 更新脚本路径（如果提供了）
        if script_path:
            # 替换 target_script 赋值
            import re
            modified_content = re.sub(
                r"target_script\s*=\s*['\"][^'\"]*['\"]",
                f"target_script = '{script_path.name}'",
                modified_content
            )

        # 添加version参数
        if 'version=' in modified_content:
            # 如果已有version，替换它
            modified_content = re.sub(r"version=r?'[^']*'", f"version=r'{re.escape(str(version_file))}'", modified_content)
        else:
            # 添加version参数到EXE调用
            exe_pattern = r'(exe = EXE\(\s*pyz,\s*a\.scripts,\s*a\.binaries,\s*a\.zipfiles,\s*a\.datas,)'
            version_param = f"version=r'{str(version_file)}',"

            def add_version(match):
                return match.group(1) + f'\n    {version_param}'

            modified_content = re.sub(exe_pattern, add_version, modified_content, flags=re.DOTALL)

            # 如果没有找到EXE模式，在文件末尾添加version参数
            if modified_content == spec_content:
                modified_content = modified_content.replace(')', f',\n    {version_param}\n)')

        # 添加icon参数（如果配置中有）
        if config.install.icon_path:
            icon_path = str(config.install.icon_path)
            if 'icon=' in modified_content:
                # 如果已有icon，替换它 - 匹配各种格式：icon=None, icon=r'path', icon='path'
                def replace_icon(match):
                    return f"icon=r'{icon_path}'"
                modified_content = re.sub(
                    r"icon\s*=\s*[^,\)\n]*",
                    replace_icon,
                    modified_content
                )
            else:
                # 添加icon参数到EXE调用
                exe_pattern = r'(exe = EXE\(\s*pyz,\s*a\.scripts,\s*a\.binaries,\s*a\.zipfiles,\s*a\.datas,)'
                def add_icon(match):
                    return match.group(1) + f'\n    icon=r\'{icon_path}\','

                modified_content = re.sub(exe_pattern, add_icon, modified_content, flags=re.DOTALL)

                # 如果没有找到EXE模式，在文件末尾添加icon参数
                if 'icon=' not in modified_content:
                    modified_content = modified_content.replace(')', f',\n    icon=r\'{icon_path}\'\n)')

        # 添加UAC提权参数（如果配置中需要管理员权限）
        # 注意：不设置uac_admin=True以避免exe显示盾牌图标
        # UAC提权将在运行时通过manifest或其他方式处理
        # if config.install.require_admin:
        #     if 'uac_admin=' in modified_content:
        #         # 如果已有uac_admin，替换它
        #         def replace_uac(match):
        #             return "uac_admin=True"
        #         modified_content = re.sub(
        #             r"uac_admin\s*=\s*[^,\)\n]*",
        #             replace_uac,
        #             modified_content
        #         )
        #     else:
        #         # 添加uac_admin参数到EXE调用
        #         exe_pattern = r'(exe = EXE\(\s*pyz,\s*a\.scripts,\s*a\.binaries,\s*a\.zipfiles,\s*a\.datas,)'
        #         def add_uac(match):
        #             return match.group(1) + '\n    uac_admin=True,'
        #
        #         modified_content = re.sub(exe_pattern, add_uac, modified_content, flags=re.DOTALL)
        #
        #         # 如果没有找到EXE模式，在文件末尾添加uac_admin参数
        #         if 'uac_admin=' not in modified_content:
        #             modified_content = modified_content.replace(')', '\n    uac_admin=True\n)')

        return modified_content