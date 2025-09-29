# CHANGELOG

所有显著变更按语义化风格记录。

## [Unreleased]

## [2025-09-29]

### Changed

- 运行时 GUI 调整：
  - 移除侧栏顶部重复的应用名称，避免视觉重复（顶部保留应用名）。
  - 侧栏步骤列表左对齐并更紧凑，减少顶部空白，步骤标签不再水平居中。
  - 移除了欢迎与进度页的显式“退出”按钮；请使用窗口右上角的关闭 (X) 退出安装器；安装进行中点击 X 会触发取消逻辑并安全中断。
  - 修复 CTkLabel 在某些环境下接收 None width 导致类型不匹配的错误（仅在显式设置宽度时传递 width 参数）。

### Notes

- 建议在需要 GUI（图标显示）时安装 `customtkinter` 与 `pillow`：

```powershell
pip install customtkinter pillow
```

- 若系统不具备 `customtkinter`/`tkinter`，运行时会回退到 CLI 模式。

---

请在发布前将合适的条目从 `Unreleased` 移动到版本号（例如 `0.2.1`），并在 PR 中更新。
