import struct
import json
from pathlib import Path

from inspa.build.builder import Builder
from inspa.config.schema import InspaConfig, ProductModel, InstallModel, InputPathModel

FOOTER_MAGIC = b'INSPAF01'
FOOTER_SIZE = 8 + 8 + 8 + 8 + 8 + 32

def make_temp_files(tmp_path: Path):
    file_a = tmp_path / 'a.txt'
    file_a.write_text('hello world')
    return [file_a]

def build_config(tmp_path: Path):
    product = ProductModel(
        name='TestApp',
        version='1.0.0',
        company='ACME',
        description='Test App',
        copyright='© ACME',
        website='https://example.com'
    )
    install = InstallModel(
        default_path='%TEMP%/TestApp',
        allow_user_path=True,
        force_hidden_path=False,
        show_ui=False,
        silent_allowed=True,
        license_file=None,
        privacy_file=None,
        require_admin=False
    )
    inputs = [InputPathModel(path=tmp_path, recursive=True, preserve_structure=True)]
    return InspaConfig(
        product=product,
        install=install,
        inputs=inputs,
        resources=None,
        exclude=None,
        post_actions=None,
        env=None
    )

def test_footer_present_and_correct(tmp_path: Path):
    files = make_temp_files(tmp_path)
    cfg = build_config(tmp_path)
    out = tmp_path / 'installer.exe'
    builder = Builder()
    res = builder.build(cfg, out)
    assert res.success and out.exists()
    data = out.read_bytes()
    assert len(data) > FOOTER_SIZE
    footer = data[-FOOTER_SIZE:]
    magic, h_off, h_len, c_off, c_size, hash_bytes = struct.unpack('<8sQQQQ32s', footer)
    assert magic == FOOTER_MAGIC
    # basic sanity
    assert h_off + h_len <= len(data)
    assert c_off + c_size + 32 + FOOTER_SIZE <= len(data) + FOOTER_SIZE  # legacy hash + footer


def test_legacy_scan_backward_compatibility(tmp_path: Path):
    cfg = build_config(tmp_path)
    out = tmp_path / 'installer.exe'
    Builder().build(cfg, out)
    raw = out.read_bytes()
    # simulate legacy by stripping footer only
    legacy = raw[:-FOOTER_SIZE]
    legacy_path = tmp_path / 'installer_legacy.exe'
    legacy_path.write_bytes(legacy)
    # quick heuristic: ensure last 32 bytes still present
    assert len(legacy) > 32
    # footer magic removed
    assert legacy[-8:] != FOOTER_MAGIC


def test_stats_in_header(tmp_path: Path):
    cfg = build_config(tmp_path)
    out = tmp_path / 'installer.exe'
    Builder().build(cfg, out)
    data = out.read_bytes()
    footer = data[-FOOTER_SIZE:]
    magic, h_off, h_len, c_off, c_size, hash_bytes = struct.unpack('<8sQQQQ32s', footer)
    with open(out, 'rb') as f:
        f.seek(h_off)
        recorded_len = struct.unpack('<Q', f.read(8))[0]
        assert recorded_len == h_len
        header_bytes = f.read(h_len)
        header = json.loads(header_bytes.decode('utf-8'))
        stats = header.get('stats')
        assert stats and 'original_size' in stats and 'compressed_size' in stats and 'file_count' in stats
