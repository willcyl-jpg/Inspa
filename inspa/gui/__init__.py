"""GUI 图形界面模块

仅包含构建器 (Builder) 相关界面。安装器运行时 GUI 现在位于 `inspa.runtime_stub.gui`
并与核心逻辑 `inspa.runtime_stub.core` 分层；不再存在 `standalone_main.py`。
"""

try:  # pragma: no cover
    import customtkinter as ctk  # type: ignore
    GUI_AVAILABLE = True
except Exception:  # pragma: no cover
    GUI_AVAILABLE = False
    ctk = None  # type: ignore

if GUI_AVAILABLE:
    from .builder_gui import BuilderGUI  # type: ignore
    __all__ = ['BuilderGUI', 'GUI_AVAILABLE']
else:
    BuilderGUI = None  # type: ignore
    __all__ = ['GUI_AVAILABLE']