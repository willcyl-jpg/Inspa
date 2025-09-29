"""PyInstaller spec - Unified runtime (GUI capable, falls back to CLI)

构建示例:
    pyinstaller --noconfirm --clean inspa_runtime.spec
可选加速:
    set PYTHONOPTIMIZE=2  (或 PowerShell: $env:PYTHONOPTIMIZE=2)
"""

from PyInstaller.building.build_main import Analysis, PYZ, EXE

block_cipher = None
target_script = 'inspa/runtime_stub/installer.py'

excludes = [
    # 保留精简：去掉不需要的标准库/调试/测试模块
    'test', 'distutils', 'setuptools', 'asyncio', 'email', 'http', 'xmlrpc',
    'unittest', 'pydoc', 'doctest'
]

a = Analysis(
    [target_script],
    pathex=['.'],
    binaries=[],
    datas=[],
    # tkinter 相关显式列出，防止裁剪
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='inspa_runtime',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,  # GUI 优先，失败自动回退 CLI
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
