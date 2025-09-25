"""GUI 图形界面模块"""

from .installer_gui import InstallerRuntimeGUI, GUI_AVAILABLE

# 只有在GUI可用时才导入BuilderGUI
if GUI_AVAILABLE:
    from .builder_gui import BuilderGUI
    __all__ = ['InstallerRuntimeGUI', 'BuilderGUI', 'GUI_AVAILABLE']
else:
    BuilderGUI = None
    __all__ = ['InstallerRuntimeGUI', 'GUI_AVAILABLE']