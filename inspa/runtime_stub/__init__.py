"""Unified runtime stub public API.

此包已合并为单文件实现: `installer.py`，包含:
 - InstallerRuntime (核心逻辑)
 - InstallerRuntimeGUI (可选 GUI)

外部使用保持不变::

	from inspa.runtime_stub import InstallerRuntime, GUI_AVAILABLE
	rt = InstallerRuntime(installer_path)
	ok = rt.run_installation(use_gui=GUI_AVAILABLE)
"""

from .installer import (  # noqa: F401
	InstallerRuntime,
	InstallerRuntimeGUI,
	GUI_AVAILABLE,
	FOOTER_MAGIC,
	FOOTER_SIZE,
)

__all__ = [
	"InstallerRuntime",
	"InstallerRuntimeGUI",
	"GUI_AVAILABLE",
	"FOOTER_MAGIC",
	"FOOTER_SIZE",
]