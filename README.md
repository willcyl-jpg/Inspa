# Inspa - Windows 安装器构建工具

一个现代化的 Windows 单文件自解压安装器构建工具，支持可视化界面和命令行操作。

## ✨ 特性

- **单文件安装器**: 将应用程序及其依赖打包成一个 .exe 文件
- **高效压缩**: 支持 Zstd 和 ZIP 压缩算法
- **可视化界面**: 基于 CustomTkinter 的现代化 GUI
- **命令行工具**: 完整的 CLI 支持，适合 CI/CD 流水线
- **配置化构建**: YAML 配置文件，易于维护和版本控制
- **脚本支持**: 支持安装前后执行 PowerShell/批处理脚本
- **环境变量**: 自动设置 PATH 和其他环境变量
- **完整性验证**: SHA-256 哈希校验确保文件完整性

## � 快速开始

### 安装

```bash
pip install .
```

### 基本使用

1. **创建配置文件** (`inspa.yaml`):

```yaml
product:
  name: "My Application"
  version: "1.0.0"
  publisher: "My Company"

ui:
  theme: "github-light"
  icon: "app.ico"

install:
  default_path: "C:\\Program Files\\MyApp"

files:
  - source: "dist/"
    target: "."

compression:
  algo: "zstd"
  level: 3
```

version: "1.0.0"
company: "我的公司"
description: "应用描述"

ui:
window_title: "我的应用安装程序"
welcome_heading: "欢迎安装我的应用"
welcome_subtitle: "请按步骤完成安装"

install:
default_path: "%ProgramFiles%/MyApp"
allow_user_path: true
license_file: "./LICENSE.txt"

compression:
algo: zstd
level: 10

inputs:

- path: ./bin
- path: ./config

post_actions:

- type: powershell
  command: scripts/setup.ps1
  hidden: true
  show_in_ui: true

````

2. **构建安装器**:

```bash
inspa build -c config.yaml -o dist/installer.exe
````

3. **运行安装器**:

```bash
# 正常安装（显示 UI）
./installer.exe
```

## 详细输出

```bash
inspa build -c config.yaml -o installer.exe --verbose
```

# 静默安装

./installer.exe /S

```

## 项目结构

```

Inspa/
├── inspa/ # 主包
│ ├── **init**.py
│ ├── cli/ # CLI 命令行工具
│ ├── gui/ # GUI 图形界面
│ ├── config/ # 配置和 Schema
│ ├── build/ # 构建服务
│ ├── runtime_stub/ # 安装器运行时
│ └── utils/ # 通用工具
├── tests/ # 测试文件
├── examples/ # 示例配置
└── docs/ # 文档

````

## 开发

### 环境设置

```bash
# 克隆项目
git clone https://github.com/willcyl-jpg/Inspa.git
cd Inspa

# 安装依赖（包括开发依赖）
pip install -e ".[dev]"

# 安装 pre-commit hooks
pre-commit install
````

### 测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit

# 运行集成测试
pytest tests/integration

# 测试覆盖率
pytest --cov=inspa
```

### 代码格式化

```bash
# 格式化代码
black inspa/ tests/

# 导入排序
# 详细输出 (DEBUG 日志)

# 类型检查
mypy inspa/
```

## 命令行使用

### 构建命令

```bash
# 基础构建
inspa build -c config.yaml -o installer.exe

# 详细输出
inspa build -c config.yaml -o installer.exe --verbose

# 自定义图标
inspa build -c config.yaml -o installer.exe --icon app.ico
```

### 验证配置

```bash
# 验证 YAML 配置
inspa validate -c config.yaml

# 输出 JSON 格式错误
inspa validate -c config.yaml --json
```

### 检查工具

```bash
# 检查安装器头信息
inspa inspect installer.exe

# 提取安装器内容
inspa extract installer.exe -d extracted/

# 计算归档哈希
inspa hash installer.exe
```

## GUI 使用

启动图形界面：

```bash
inspa gui
```

GUI 提供两种模式：

- **向导模式**: 分步引导配置
- **高级模式**: 集中编辑所有选项

## 配置参考

详细的配置字段说明请参考 [配置文档](docs/configuration.md)。

## 贡献

欢迎贡献！请先阅读 [贡献指南](CONTRIBUTING.md)。

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。

## 变更记录

详见 [CHANGELOG.md](CHANGELOG.md)。
