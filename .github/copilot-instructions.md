# Inspa 项目开发指导

## 项目概述

Inspa 是一个现代化的 Windows 单文件自解压安装器构建工具，采用**分离式架构**：Builder(构建器)负责打包，Runtime Stub(运行时存根)负责解压安装。

## 核心架构模式

### 三层架构

- **CLI 层** (`inspa/cli/`): 基于 typer 的命令行接口，每个子命令对应`commands/`下的独立模块
- **业务逻辑层** (`inspa/build/`, `inspa/config/`): 核心构建逻辑和配置管理
- **运行时层** (`inspa/runtime_stub/`): 独立的安装器运行时，需要被嵌入到最终 EXE 中

### 关键数据流

```
YAML配置 → Pydantic验证 → 文件收集 → 压缩 → Header+Stub组合 → 单文件EXE
```

## 开发约定与模式

### 配置驱动设计

- 所有行为通过`inspa/config/schema.py`中的 Pydantic 模型定义
- 使用`ruamel.yaml`保持注释，严格类型验证
- 配置加载：`load_config()` → 验证 → `InspaConfig`对象

### 错误处理模式

```python
# 统一异常层次结构
ConfigError → ConfigValidationError
BuildError → CompressionError
InstallationError → 具体运行时错误

# 日志分阶段标记
from ..utils import get_stage_logger, LogStage
logger = get_stage_logger(LogStage.COLLECT)  # PARSE/COLLECT/COMPRESS/BUILD
```

### GUI 响应式架构

- 主线程运行 CustomTkinter 界面
- 构建任务在后台线程执行
- 通过`queue.Queue`进行线程间通信
- 进度回调模式：`ProgressCallback = Callable[[str, int, int, str], None]`

## 关键实现细节

### 文件收集策略

```python
# inspa/build/collector.py 中的模式
# 支持glob排除模式，递归扫描，符号链接处理
collector = FileCollector(base_path, exclude_patterns)
files = collector.collect()  # 返回FileInfo列表
```

### 压缩器抽象层

```python
# inspa/build/compressor.py - 工厂模式
compressor = CompressorFactory.create_compressor(
    algorithm=CompressionAlgorithm.ZSTD,
    level=3
)
# 支持流式压缩，自动降级到ZIP
```

### Runtime Stub 组合机制

- Stub 文件：预编译的最小 Python 可执行文件
- 数据追加：Header(JSON) + 压缩数据块 + 哈希校验
- 自解压：Runtime 在启动时解析自身二进制数据

### CLI 命令映射

```bash
inspa build   # 对应 inspa/cli/commands/build.py
inspa gui     # 启动CustomTkinter界面
inspa validate # 仅验证配置，不构建
inspa inspect # 分析已生成的安装器
inspa extract # 提取安装器内容用于调试
```

## 开发工作流

### 本地开发环境

```bash
# 必须使用虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
pip install -e ".[dev]"  # 包含开发依赖
```

### 代码质量检查

```bash
# 代码格式化（遵循black 88字符限制）
black inspa/ tests/
isort inspa/ tests/

# 类型检查（所有函数必须有类型注解）
mypy inspa/

# 测试运行
pytest tests/unit      # 单元测试
pytest tests/integration  # 集成测试
```

### 调试模式

- 使用`--verbose`启用 DEBUG 级别日志
- 构建失败时检查 temp 目录保留的中间文件
- GUI 开发时可用`console.print`调试，避免影响 GUI 线程

## 常见开发任务

### 添加新的 CLI 子命令

1. 在`inspa/cli/commands/`创建新模块
2. 在`inspa/cli/main.py`中注册命令
3. 遵循 typer + rich console 的输出模式

### 扩展配置 Schema

1. 修改`inspa/config/schema.py`中的模型
2. 添加验证器方法（使用`@field_validator`）
3. 更新相关的构建逻辑处理新字段

### 添加新的压缩算法

1. 实现`inspa/build/compressor.py`中的抽象接口
2. 在`CompressorFactory`中注册
3. 更新`CompressionAlgorithm`枚举

## 重要约束与限制

### 技术栈限制

- Python 3.11+ 最低要求（使用新语法特性）
- CustomTkinter GUI（不是原生 Tkinter）
- 仅支持 Windows 平台（路径处理、UAC、注册表）

### 性能考虑

- 大文件(2GB+)需要流式处理，避免内存溢出
- GUI 更新频率控制，避免卡顿
- PyInstaller 打包后的启动速度优化

### 安全要求

- 所有文件操作使用 SHA-256 哈希验证
- UAC 权限处理（manifest 嵌入）
- 临时文件安全清理

## 当前开发重点

根据`docs/next_development_plan.md`，当前优先级：

1. **GUI 功能完善** - 完善构建器界面的交互逻辑
2. **Runtime Stub 集成** - 实现 stub 与数据的组合输出
3. **脚本执行管线** - 安装后脚本的执行功能

## 调试技巧

### 常见问题排查

- 配置验证失败：检查`InspaConfig`模型定义和 YAML 结构匹配
- 构建卡住：启用详细日志，检查文件权限和磁盘空间
- GUI 无响应：确保耗时操作在后台线程执行
- Runtime 失败：使用`inspa inspect`命令检查生成的安装器结构

记住：所有代码必须有类型注解，遵循 PEP8 规范，测试文件放在`tests/`目录下。
