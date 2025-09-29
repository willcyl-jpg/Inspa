import json
import struct
from pathlib import Path

from inspa.build.builder import Builder
from inspa.config.schema import (
    InspaConfig, ProductModel, InstallModel, InputPathModel, CompressionModel, CompressionAlgorithm
)
from inspa.runtime_stub import InstallerRuntime

FOOTER_MAGIC = b'INSPAF01'
FOOTER_SIZE = struct.calcsize('<8sQQQQ32s')

def build_basic_config(tmp_path: Path) -> InspaConfig:
    product = ProductModel(
        name='ZstdApp',
        version='1.0.0',
        company='ACME',
        description='ZSTD Test',
        copyright='© ACME',
        website='https://example.com'
    )
    install = InstallModel(
        default_path=str(tmp_path / 'install'),
        allow_user_path=True,
        force_hidden_path=False,
        show_ui=False,
        silent_allowed=True,
        license_file=None,
        privacy_file=None,
        require_admin=False
    )
    inputs = [InputPathModel(path=tmp_path, recursive=True, preserve_structure=True)]
    compression = CompressionModel(algo=CompressionAlgorithm.ZSTD, level=3, fallback_to_zip=False)
    return InspaConfig(
        product=product,
        install=install,
        inputs=inputs,
        compression=compression,
        resources=None,
        exclude=None,
        post_actions=None,
        env=None,
    )


def test_zstd_build_and_parse(tmp_path: Path):
    # prepare file
    data_file = tmp_path / 'data.txt'
    data_file.write_text('hello zstd world')

    cfg = build_basic_config(tmp_path)
    out = tmp_path / 'zstd_installer.exe'
    res = Builder().build(cfg, out)
    assert res.success and out.exists()

    # parse footer
    raw = out.read_bytes()
    assert len(raw) > FOOTER_SIZE
    footer = raw[-FOOTER_SIZE:]
    magic, h_off, h_len, c_off, c_size, hash_bytes = struct.unpack('<8sQQQQ32s', footer)
    assert magic == FOOTER_MAGIC
    with open(out, 'rb') as f:
        f.seek(h_off)
        assert struct.unpack('<Q', f.read(8))[0] == h_len
        header_bytes = f.read(h_len)
    header = json.loads(header_bytes.decode('utf-8'))
    assert header.get('compression', {}).get('algo') == 'zstd'

    # runtime extraction using unified runtime_stub (gui.py backend)
    runtime = InstallerRuntime(out, silent=True)
    ok = runtime.run_install()
    assert ok, 'runtime extraction failed'
    # 运行时安装目录逻辑: 默认当前目录 / installed_app 或 header 中 default_path
    default_path = header.get('install', {}).get('default_path')
    if default_path:
        install_dir = Path(default_path).expanduser()
    else:
        install_dir = Path.cwd() / 'installed_app'
    matches = list(install_dir.rglob('data.txt')) if install_dir.exists() else []
    if not matches and install_dir.exists():
        # 兼容结构可能嵌套，递归已做；若仍失败则输出诊断文件列表
        import os
        for root, dirs, files in os.walk(str(install_dir)):
            pass  # 避免冗长输出，调试时可加入打印
    assert matches, 'data.txt not found after extraction'
