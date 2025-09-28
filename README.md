# Inspa - Windows 单文件自解压安装器构建与运行系统

一个现代化、配置驱动、支持 GUI 与 CLI 的 Windows 单文件安装器（Self-Extracting Installer）构建工具。目标：让「打包 → 分发 → 安装」形成一条可复用、可验证、可扩展的流水线。

## ✨ 核心特性

- 单文件产物：输出一个可直接分发的 `installer.exe`
- 双算法压缩：Zstd (1–22 级，可回退) / Zip（兼容保底）
- Footer 快速定位：通过 `INSPAF01` Footer O(1) 解析，无需线性扫描
- 配置即行为：严格 Pydantic Schema + YAML，支持版本化与验证
- 图形 + 命令行：CustomTkinter 现代 GUI + Typer CLI（CI/CD 友好）
- 后置脚本：支持 PowerShell / Batch，条件运行、超时、隐藏执行
- 环境变量设置：支持 PATH 追加与系统级（自动推断管理员权限）
- 可选静默模式：`/S` 或配置允许时自动无界面安装
- Hash 校验：归档 SHA-256 + Footer 存档结构信息保证完整性
- 动态 Stub：按需 PyInstaller 编译（含版本信息、图标、UAC）或测试占位

## 🧱 架构概览

三层结构（分离式）:

1. CLI 层 (`inspa/cli/`): Typer 命令行（build / validate / inspect / extract / gui / info / example）
2. 业务构建层 (`inspa/build/`, `inspa/config/`): 文件收集、压缩、头部构建、安装器组装
3. 运行时层 (`inspa/runtime_stub/installer.py`): 单文件统一 Stub（解析 + 解压 + 脚本 + 可选 GUI）

数据流：

```
YAML 配置 → Pydantic 验证 → 文件收集(FileCollector) → 压缩(Compressor) → Header(JSON) → Runtime Stub + 数据 + Footer 组装 → installer.exe
```

Footer 结构（72 bytes，末尾追加）：

```
<8s magic=INSPAF01><Q header_offset><Q header_len><Q compressed_offset><Q compressed_size><32s archive_hash>
```

运行时读取流程：定位 Footer → 跳转 header_offset → 读 8 字节长度 → 读 Header(JSON) → 定位压缩块 → 解压 → 执行脚本。

向后兼容：仍写入旧格式末尾 32 字节 Hash，旧解析器可以扫描使用；新解析优先 Footer。

## 🔧 安装

```bash
pip install .
```

或开发模式：

```bash
pip install -e ".[dev]"
```

## 🚀 快速上手

1. 生成示例配置（可选）：

```bash
inspa example -o example.yaml
```

2. 创建或编辑配置 (`installer.yaml`)：

```yaml
config:
  version: 1

product:
  name: "MyApp"
  version: "1.2.0"
  company: "My Company"
  description: "示例应用描述"

install:
  default_path: "%ProgramFiles%/MyApp"
  allow_user_path: true
  show_ui: true
  silent_allowed: true
  license_file: "./LICENSE.txt"
  require_admin: false # 若使用 %ProgramFiles% 会在验证阶段自动提升为 true

ui:
  window_title: "MyApp 安装程序"
  welcome_heading: "欢迎安装 MyApp"
  welcome_subtitle: "请点击开始安装"
  theme: github-light

inputs:
  - path: ./dist
    recursive: true
    preserve_structure: true
  - path: ./config

exclude:
  - "*.log"
  - "__pycache__/"

compression:
  algo: zstd
  level: 10
  fallback_to_zip: true

post_actions:
  - type: powershell
    command: scripts/post_install.ps1
    args: ["--init"]
    timeout_sec: 300
    run_if: success
    show_in_ui: true

env:
  add_path:
    - "%INSTALL_DIR%/bin"
  set:
    MYAPP_ENV: production
  system_scope: false

resources:
  icon: assets/app.ico
```

3. 构建：

```bash
inspa build -c installer.yaml -o dist/MyAppInstaller.exe --verbose
```

4. 运行：

```bash
./MyAppInstaller.exe          # GUI 或 CLI（依据配置）
./MyAppInstaller.exe /S       # 静默（若允许）
```

## 🧪 CLI 命令概览

| 命令     | 说明                             |
| -------- | -------------------------------- |
| build    | 构建安装器                       |
| validate | 验证配置文件（可配合 --json）    |
| inspect  | 查看已构建安装器的 Header 元数据 |
| extract  | 解包安装器内容到目录（调试用）   |
| gui      | 启动图形界面构建器               |
| info     | 显示支持算法、版本信息           |
| example  | 生成示例配置                     |

示例：

```bash
inspa validate -c installer.yaml --json
inspa inspect dist/MyAppInstaller.exe
inspa extract dist/MyAppInstaller.exe -d unpacked/
```

## 📦 运行时（Runtime Stub）

当前已合并为单文件 `inspa/runtime_stub/installer.py`：

- 解析 Footer + 头部 JSON
- 支持旧格式回退（线性扫描头部 + 尾部哈希）
- Zstd/Zip 解包（Zstd 采用流式 reader，避免大文件爆内存）
- 脚本执行（powershell / batch），GUI 模式使用精简进度回调
- 可选 GUI（customtkinter 可用时启用，否则自动降级）

关键 API：

```python
from pathlib import Path
from inspa.runtime_stub import InstallerRuntime, run_gui_installation, GUI_AVAILABLE

rt = InstallerRuntime(Path('MyAppInstaller.exe'))
rt.run_installation(use_gui=GUI_AVAILABLE)

# 或显式 GUI (自定义安装目录)
run_gui_installation(rt, custom_install_dir="D:/Apps/MyApp")
```

## 🗂 项目结构（精简）

```
inspa/
  cli/              # Typer 子命令入口
  build/            # Builder / Compressor / Header / Collector
  config/           # Pydantic Schema + Loader
  runtime_stub/     # 统一运行时 (installer.py)
  gui/              # 构建 GUI (CustomTkinter)
  utils/            # 日志、路径等工具
tests/              # 单元 & 集成测试
docs/               # 文档与设计计划
```

## 🧬 日志与阶段

通过阶段标记：COLLECT / COMPRESS / HEADER / STUB / WRITE / BUILD；使用 `--verbose` 查看 DEBUG 细节（文件列表、偏移计算等）。

## 🔒 安全与完整性

- 压缩块 SHA-256 存储在 Footer & 旧尾部，为双重校验
- 可选 UAC（`install.require_admin`）+ 自动推断（系统级 PATH / %ProgramFiles% 路径）
- 临时目录隔离构建，失败自动清理（测试模式下可保留）

## 🛠 开发工作流

```bash
git clone https://github.com/willcyl-jpg/Inspa.git
cd Inspa
pip install -e ".[dev]"
pre-commit install

# 代码质量
black inspa/ tests/
isort inspa/ tests/
mypy inspa/
pytest -q
```

## 🧩 测试模式

设置 `INSPA_TEST_MODE=1` 时：

- 使用最小占位 Stub (避免 PyInstaller 构建耗时)
- 加速单元测试；仍验证 Footer/解析/解压逻辑

## 🖥 GUI 构建器

```bash
inspa gui
```

支持：实时进度、日志窗口、分步配置（General / Files / Compression / Scripts / Advanced）。

## 🔌 扩展点

- 新压缩算法：实现 `Compressor` 接口并注册到 `CompressorFactory`
- 增加脚本类型：扩展 `ScriptType` + 运行时执行分支
- 配置 Schema：在 `schema.py` 添加字段 + 验证器 + Builder/Runtime 处理逻辑

## 🧾 许可证

MIT License，详见 [LICENSE](LICENSE)。

## 📄 变更记录

请查看 `docs/next_development_plan.md` 与未来的 `CHANGELOG.md`。

---

如果你有功能建议或想法，欢迎提交 Issue / PR，一起完善一个可维护、可靠的 Windows 安装器解决方案。
