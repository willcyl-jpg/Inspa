# Inspa 项目下一步开发计划

版本：v1.0  
日期：2025年9月24日  
状态：执行计划

---

## 当前项目实现状态分析

### ✅ 已完成的核心组件

1. **项目架构与模块结构** - 完全实现
   - CLI 命令行接口 (typer + rich)
   - 配置模块 (pydantic schema + YAML 解析)
   - 工具模块 (日志、路径处理等)

2. **构建系统核心** - 基本实现
   - 文件收集器 (glob 排除、递归扫描)
   - 压缩器抽象 (支持 zstd 和 zip 回退)
   - Header 构建器
   - 构建器主类

3. **Runtime Stub** - 基本实现
   - 安装器主程序框架
   - 基础 GUI 运行时界面

4. **GUI 界面** - 部分实现
   - CustomTkinter 基础框架
   - 构建器主界面结构
   - 安装器运行时界面

### ❌ 待完成的关键功能

1. **GUI 完整实现**
   - 构建器 GUI 的完整交互逻辑
   - 文件选择和预览功能
   - 实时构建进度显示
   - 日志面板集成

2. **核心功能完善**
   - Runtime stub 与压缩数据的完整集成
   - 脚本执行管线
   - 环境变量设置
   - UAC 权限处理

3. **打包与分发**
   - PyInstaller 配置
   - 图标注入
   - 版本信息嵌入

---

## 下一步开发计划

### Phase 1: GUI 功能完善 (优先级: 高)

#### 1.1 完善构建器 GUI 交互逻辑
**目标**: 让用户能通过 GUI 完整地配置和构建安装器

**任务列表**:
- [ ] 完善配置文件加载和编辑功能
- [ ] 实现输入文件/目录选择界面 (带预览)
- [ ] 实现排除规则配置界面
- [ ] 集成构建进度条和日志显示
- [ ] 实现构建完成后的结果显示

**具体实现**:
```python
# 需要完善的核心方法
def _browse_config(self) -> None
def _validate_config(self) -> None  
def _browse_output(self) -> None
def _start_build(self) -> None
def _show_build_progress(self) -> None
def _update_log_display(self) -> None
```

#### 1.2 集成实时构建反馈
**目标**: 构建过程中提供详细的进度和状态反馈

**技术方案**:
- 使用队列 (`queue.Queue`) 实现线程间通信
- 构建器运行在后台线程，GUI 在主线程轮询更新
- 集成 `LogStage` 系统显示不同阶段的进度

### Phase 2: 核心构建功能完善 (优先级: 高)

#### 2.1 完善 Runtime Stub 集成
**目标**: 实现完整的 stub + 数据组合输出

**当前问题**: 
- `builder.py` 中缺少 stub 文件的生成和组合逻辑
- 需要实现将压缩数据追加到 stub 可执行文件的功能

**解决方案**:
```python
# 在 builder.py 中实现
def _attach_data_to_stub(self, stub_path: Path, data_stream: BinaryIO, output_path: Path):
    """将压缩数据追加到 Runtime Stub"""
    
def _generate_runtime_stub(self, header: dict) -> Path:
    """生成 Runtime Stub 可执行文件"""
```

#### 2.2 实现脚本执行管线
**目标**: 完善安装后脚本的执行功能

**需要实现**:
- 脚本类型检测和执行器选择
- 实时输出捕获和 UI 更新
- 超时和错误处理
- 权限管理 (UAC)

### Phase 3: 系统功能增强 (优先级: 中)

#### 3.1 环境变量和PATH设置
**实现位置**: `runtime_stub/installer.py`

```python
def setup_environment_variables(self, config: dict) -> bool:
    """设置环境变量和PATH"""
    # Windows 注册表操作
    # HKEY_CURRENT_USER vs HKEY_LOCAL_MACHINE
```

#### 3.2 图标和版本信息注入
**实现位置**: `build/` 模块新增 `metadata.py`

```python
def inject_icon(exe_path: Path, icon_path: Path) -> None:
def inject_version_info(exe_path: Path, version_info: dict) -> None:
```

### Phase 4: 打包和部署 (优先级: 中)

#### 4.1 PyInstaller 配置优化
**目标**: 生成高质量的单文件可执行程序

**配置文件**: `packaging/pyinstaller.spec`
```python
# PyInstaller 规范文件
# - 优化启动速度
# - 最小化文件体积
# - 包含必要资源文件
```

#### 4.2 创建构建脚本
**文件**: `build_release.py`
- 自动化完整构建流程
- 版本号管理
- 测试验证

---

## 具体开发任务优先级排序

### 本周任务 (Week 1)
1. **[P0]** 完善 `inspa/gui.py` 中的构建器 GUI 核心交互
2. **[P0]** 实现构建进度显示和日志集成
3. **[P1]** 完善 `builder.py` 中的 stub 数据组合逻辑

### 下周任务 (Week 2)  
1. **[P0]** 实现脚本执行管线
2. **[P1]** 环境变量设置功能
3. **[P1]** 图标和版本信息注入

### 第三周任务 (Week 3)
1. **[P1]** PyInstaller 打包配置
2. **[P2]** 完善错误处理和用户体验
3. **[P2]** 文档和示例完善

---

## 技术债务和风险管控

### 当前技术债务
1. **GUI 响应性**: CustomTkinter 在大文件处理时可能卡顿
   - 解决方案: 实现懒加载和虚拟化列表

2. **错误处理**: 缺少统一的错误处理机制
   - 解决方案: 实现全局异常处理器

3. **测试覆盖率**: 核心功能缺少单元测试
   - 解决方案: 优先为关键模块添加测试

### 性能优化点
1. **大文件压缩**: 2GB+ 文件的内存控制
2. **GUI 刷新频率**: 避免过度更新UI导致卡顿
3. **启动速度**: PyInstaller 生成的exe启动优化

---

## 成功标准

### MVP 验收标准
- [ ] GUI 可以完整配置和构建安装器
- [ ] 生成的安装器可以正确解压和安装文件
- [ ] 支持基本的脚本执行
- [ ] 包含完整的错误处理和用户反馈

### 完整版本验收标准  
- [ ] 支持所有配置选项 (YAML schema 全覆盖)
- [ ] 高质量的用户体验 (进度显示、错误提示)
- [ ] 性能达标 (500MB 文件 < 2分钟构建)
- [ ] 完整的文档和示例

---

## 开发环境准备

### 必需依赖
```bash
pip install customtkinter typer rich pydantic ruamel.yaml zstandard
pip install pyinstaller  # 用于最终打包
```

### 开发工具
- IDE: VS Code / PyCharm
- 测试: pytest  
- 代码格式: black + isort
- 类型检查: mypy

---

## 下一步立即行动

1. **立即开始**: 完善 `inspa/gui.py` 中的 `_start_build` 方法
2. **优先修复**: `builder.py` 中缺失的 stub 集成逻辑  
3. **并行进行**: 为核心模块添加单元测试

**预计完成时间**: 3-4 周达到 MVP 标准，6-8 周达到完整版本。