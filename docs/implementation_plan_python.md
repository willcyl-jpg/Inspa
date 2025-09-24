# Inspa Python 实现计划（Architecture & Implementation Plan）

版本：0.1  (初稿)  
日期：2025-09-24  
适用需求基线：`docs_requirements.md` v1.0  
目标：用 **Python 为主语言** 实现 Builder (CLI + GUI) 与 Runtime Stub 打包管线，生成 **单文件自解压安装器 EXE**。

---
## 目录
1. 总体技术选型
2. 系统分层与组件划分
3. 运行流程（Build → Installer Runtime → Post Actions）
4. 核心数据结构 & Header 规范
5. 压缩与归档格式设计
6. 安装器 Runtime Stub 生成策略
7. GUI 技术架构（GitHub Light + 高 DPI）
8. CLI 设计与命令语义
9. YAML 配置校验与 Schema 版本控制
10. 日志 & 可观测性方案
11. 脚本执行沙箱与输出管线
12. 环境变量与 PATH 追加策略
13. 安全 / 完整性 / UAC / 哈希
14. 模块结构（包命名与职责）
15. 任务分解 & 与 FR/NFR 映射
16. 开发阶段里程碑 & 迭代顺序
17. 测试策略（功能/非功能/验收）
18. 风险与缓解（实现视角）
19. 后续可扩展挂点（接口点 / Plug-in Points）

---
## 1. 总体技术选型
| 目标 | 方案 | 说明 |
|------|------|------|
| 语言（Builder） | Python 3.11+ | 类型标注 + 较新标准库 (tomllib/exception groups) |
| GUI | CustomTkinter (Tk + themed) | 纯 Python、打包简单；自定义主题模拟 GitHub Light；需手动处理高 DPI 与布局 |
| CLI | `typer` | 结构化命令 + 自动帮助，多子命令映射 FR-BLD-010 |
| 压缩主算法 | `zstandard` 库 | 提供 streaming encoder、可调级别 |
| 压缩回退 | `zipfile` | 标准库，无额外依赖 |
| 归档布局 | 自定义：Header(JSON) + 压缩数据块 + 末尾索引/哈希 | 便于校验 & inspect |
| 哈希 | SHA-256 (`hashlib`) | FR-BLD-009 / FR-SEC-001 |
| 自解压 Stub 方式 | 预编译最小 Stub (C++ or Python frozen) + 附加数据段 | 详见 §6 |
| 单 EXE 打包 | PyInstaller / Nuitka（二选一试验） | 优先 PyInstaller（快），后评估启动性能 |
| 图标注入 | PyInstaller 参数 or rcedit (备用) | FR-BLD-020 |
| UAC Manifest | 嵌入 manifest XML (PyInstaller --uac-admin) | FR-BLD-008 |
| 配置解析 | `ruamel.yaml` | 保留注释（未来编辑），严格 round-trip |
| Schema 校验 | `pydantic` v2 | 精确定义/错误定位 |
| 日志 | `structlog` + 文件 Handler | 分阶段标签、JSON/文本双格式可扩展 |
| 单元测试 | `pytest` | 用例分层 |
| 静默模式 | 解析参数 `/S` | Windows 兼容惯例 |
| 进度 UI | Qt Model + 信号槽 | 多线程安全刷新 |
| 脚本执行 | `subprocess.Popen` + pipes | 捕获 stdout/stderr 实时推送 |
| ANSI 颜色处理 | `colorama` (可选) | FR-RT-017 |
| 安装日志 | `%TEMP%/Inspa/install.log` or 目标目录 | 配置化 |

---
## 2. 系统分层与组件划分
```
┌──────────────────────────────┐
│        CLI / GUI 层          │  (typer / CustomTkinter)
├──────────────┬──────────────┤
│  配置 & 校验  │  交互与状态   │
├──────────────┴──────────────┤
│        构建服务 (Build Service) │  (打包、压缩、哈希)
├──────────────────────────────┤
│        归档 / Header 层       │
├──────────────────────────────┤
│ Runtime Stub (C++/frozen Py) │  <-- 解包/执行脚本/UI
├──────────────────────────────┤
│   平台 & 系统调用适配层       │ (文件、UAC、环境变量) 
└──────────────────────────────┘
```

职责解耦：
- Builder 侧不直接耦合 GUI：GUI 调用 Build Service API。
- Runtime Stub 独立（最小依赖），通过 Header JSON 驱动行为。
- 所有可扩展点（压缩算法、脚本类型）以接口 / Protocol 定义。

---
## 3. 运行流程
### 3.1 构建阶段 (Builder)
1. 解析 YAML → Pydantic 校验 → 标准内部模型 (Model)。
2. 收集输入文件列表（Glob 排除）。
3. Streaming 压缩：写入 Zstd → 若失败 fallback Zip。
4. 生成 Header（含：元信息、文件列表摘要、算法、哈希、UI 文案、脚本元数据、schema_version、配置 hash）。
5. 写入临时归档文件：`[Header(JSON length 8 字节LE) + Header(JSON) + Compressed Data + 尾部校验块]`。
6. 将 Runtime Stub 可执行体复制到输出目录，追加归档数据（`ab` 模式拼接）。
7. 替换图标 & 注入版本信息 / Manifest。
8. 输出最终安装器 EXE & 构建日志。

### 3.2 安装阶段 (Runtime)
1. 读取尾/头部分定位 Header 长度 → 解析 JSON → 校验 magic/version/hash。
2. 若 `/S` 静默模式：跳过 UI，使用默认安装路径。
3. 创建临时解压目录（确保断电原子性）。
4. Streaming 解压 → 更新进度（UI or 日志）。
5. 解压完成后校验总哈希（文件 hash / 归档 hash）。
6. 执行脚本（按配置顺序），实时捕获输出推送 UI。
7. 写入环境变量（注册表 USER / SYSTEM）。
8. （可选）复制成功文件到最终目录，原子替换。
9. 完成页 & 可选自动运行主程序。

### 3.3 inspect / extract
`inspect`：只读取 Header，不需解压全部。  
`extract`：支持命令行将归档内容解出到指定目录（供 QA）。

---
## 4. 核心数据结构 & Header 规范
```jsonc
{
  "magic": "INSPRO1",              // 7~8 字节固定
  "schema_version": 1,
  "product": {"name": "Demo", "version": "1.2.3", ...},
  "ui": {"window_title": "...", "welcome_heading": "...", "welcome_subtitle": "..."},
  "install": {"default_path": "...", "allow_user_path": true, "force_hidden_path": false},
  "compression": {"algo": "zstd", "level": 10},
  "files": [
     {"path": "bin/app.exe", "size":12345, "mtime": 1727000000 }
  ],
  "scripts": [
     {"type":"powershell", "command":"scripts/Init-Service.ps1", "hidden": true, "timeout":300, "show_in_ui": true}
  ],
  "hash": {"algo":"sha256", "archive":"<hex>"},
  "build": {"timestamp": 1727000000, "builder_version": "0.1.0", "config_fingerprint":"<sha256>"}
}
```
Header 长度存放策略：文件开头放 8 字节 little-endian (uint64) 表示 Header JSON 的字节长度，紧跟 JSON，再跟压缩数据。

---
## 5. 压缩与归档格式设计
```
[0..7]              -> header_len (uint64 LE)
[8..8+N-1]          -> header JSON (UTF-8)
[8+N .. M-33]       -> compressed payload (stream zstd or zip)
[M-32 .. M-1]       -> SHA256( compressed payload ) 32 bytes raw
```
回退标记：Header.compression.algo 字段 = `zip` 时，Runtime 选择解压器。  
文件列表：不单独存未压缩内容的 hash（MVP 可选）；后续可扩展增量验证。  
流式压缩：使用 zstd `ZstdCompressor.stream_writer(fp)`，避免大内存。

---
## 6. 安装器 Runtime Stub 生成策略
需求：极简、启动快、不依赖用户 Python。  
方案对比：
| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 纯 Python + PyInstaller | 开发快 | 体积较大 (~8-12MB) | 初始 MVP |
| C++ 自写 Stub | 体积小、启动快 | 实现脚本执行/GUI 难度大 | 后期优化候选 |
| Rust + egui/winit | 跨平台潜力 | 初期复杂度高 | 暂不采用 |

MVP 路线：
1. Runtime Python 源码单独包：`runtime/`。
2. 用 PyInstaller 生成 `stub.exe`（含 UI / 解压逻辑）。
3. Builder 将 stub 与数据段拼接输出最终安装器。

---
## 7. GUI 技术架构（改为 CustomTkinter）
架构模式：保持“视图层 + 状态模型 + 服务”分离（轻量 MVVM 思想），但利用 Tk 事件循环与自定义组件。

组件映射：
- 主窗口：`customtkinter.CTk` + 左侧步骤导航（List / Vertical Buttons）+ 右侧内容容器 (Frame stack)
- 步骤面板：产品信息 / 文件选择 / 协议 / 脚本 / 压缩参数 / 构建与输出
- 文件列表：为性能与 2GB 级工程，采用懒加载树：`ttk.Treeview` 包装 + 虚拟节点（仅展开时列举子文件）
- 日志面板：文本控件（`CTkTextbox`）追加；附加内存 ring buffer（限长度）避免超大内存
- 进度条：`CTkProgressBar`（整体） + 当前文件标签
- 图标预览：加载 ICO 各尺寸 → PIL 转换后放入 `CTkLabel`

主题与样式：
- GitHub Light 颜色表手工定义（背景、边框、选中、滚动条）
- 使用全局 scaling (`tk.call('tk', 'scaling', factor)`) 处理高 DPI；Windows 查询 `ctypes.windll.shcore.GetScaleFactorForDevice(0)` 自适应
- 字体：`('Segoe UI', 10/11)` 随 DPI 调整

线程与 UI 更新：
- 构建/压缩/哈希/文件扫描放入后台线程，UI 使用 `after(16, poll_queue)` 从事件队列增量刷新日志与进度（避免直接跨线程修改控件）

限制与补偿：
- Tk 不具备原生多列虚拟化 → 大量文件时自定义分页 + 搜索过滤
- 无原生现代控件（对比 Qt）→ CustomTkinter + 适度自绘（Canvas 边框、分隔）

高 DPI：测试 125%~300% 缩放；提供内部工具函数 `dpi_scale(px: int) -> int`，在布局常量处调用。

可扩展：未来若 GUI 复杂度升级，可保持业务服务接口不变切换到 Qt / Web 前端。

---
## 8. CLI 设计 (`Inspa` 可执行)
| 命令 | 说明 | 主要参数 |
|------|------|----------|
| build | 构建安装器 | `-c config.yaml -o out/installer.exe --verbose` |
| validate | 校验 YAML / 输出错误 | `-c config.yaml` |
| inspect | 读取 EXE header | `installer.exe --json` |
| extract | 解出归档 | `installer.exe -d extracted/` |
| hash | 输出归档哈希 | `installer.exe` |

---
## 9. YAML Schema 校验
使用 Pydantic 模型：
```python
class UIModel(BaseModel):
    window_title: str | None
    welcome_heading: str | None
    welcome_subtitle: str | None
    theme: Literal['github-light']
```
错误处理：聚合 ValidationError → GUI 高亮字段；CLI 结构化输出 (JSON)。

Schema 版本升级策略：`config.version` 与内部 `SUPPORTED_SCHEMA=1` 对比；未来提供迁移器（非 MVP）。

---
## 10. 日志与可观测性
结构：`[时间][级别][阶段标签] 消息`，阶段如：`COLLECT|COMPRESS|HASH|STUB|WRITE|DONE`。  
GUI 接入：日志流经内存 Pub/Sub (队列) → 追加视图。  
Runtime 日志：默认写入安装目录或 `%TEMP%/Inspa/install.log`。  
可选 JSON 日志（后期开关）。

---
## 11. 脚本执行管线
流程：
1. 构建时仅记录脚本元数据，不内嵌脚本内容（即直接打包原文件）。
2. 运行时按顺序执行，`subprocess.Popen`（`creationflags=CREATE_NO_WINDOW`）。
3. 线程读取 stdout/stderr → 合并队列 → UI 更新。
4. 超时：监视线程 kill 进程并记录。
5. 失败策略：默认不阻断（FR-SCR-005），可未来扩展 `fail_policy`。

安全最小化：限制工作目录 = 安装目录；路径标准化阻止 `..` 上跳。

---
## 12. 环境变量策略
实现：写注册表：
- 用户：`HKEY_CURRENT_USER\Environment`
- 系统（需要管理员）：`HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment`
PATH 追加：读取现值→若不存在则追加以 `;` 分隔。
静默模式下仍执行；失败记录警告不阻断。

---
## 13. 安全 / 完整性
| 项目 | 方案 |
|------|------|
| 归档篡改检测 | 重新计算压缩区 SHA-256 对比 Header.hash.archive |
| 脚本路径限制 | 绝对化后检查前缀 == 安装目录 |
| UAC | Manifest `requireAdministrator` (可配置) |
| 临时文件清理 | finally 块 + 异常捕获 |

---
## 14. 模块结构
```
Inspa/
  __init__.py
  cli/            # CLI 入口 (typer)
  gui/            # GUI 应用入口 + 视图 + models
  config/         # pydantic schema & 解析
  build/          # 打包管线 orchestrator
    collector.py  # 文件收集/排除
    compressor.py # zstd/zip 抽象
    header.py     # Header 生成/序列化
    writer.py     # 拼接 stub + 数据
    icon.py       # 图标处理
    hashutil.py   # 哈希工具
  runtime_stub_src/  # Runtime 源 (若用 PyInstaller)
    main.py
    ui/ ...
  scripts/        # 内部脚本或示例
  utils/          # 通用 (logging, path, env)
tests/
  unit/
  integration/
  runtime/
```

---
## 15. 任务分解 & 需求映射（节选）
| 任务 | 覆盖 FR | 说明 |
|------|---------|------|
| P1: YAML Schema + 解析 | FR-BLD-001, FR-CFG-001, FR-CFG-008 | pydantic 实体 | 
| P1: 文件收集/排除 | FR-BLD-002, FR-BLD-003 | glob + ignore |
| P1: 压缩器接口 + zstd | FR-BLD-005 | streaming |
| P1: Header 构建 + 哈希 | FR-BLD-009, FR-BLD-012, FR-BLD-013 | hash fingerprint |
| P1: CLI build/validate | FR-BLD-010 | 基础命令 |
| P2: Runtime 解压 + 校验 | FR-RT-001..004, FR-SEC-001 | 解析/校验路径 |
| P2: UI Welcome/路径/进度 | FR-UI-003..008 | CustomTkinter 步骤面板 |
| P2: 脚本执行管线 | FR-SCR-001..006 | 输出流式 |
| P3: GUI 全流程 + 日志面板 | FR-BGUI-001..010,015,016 | MVVM (CustomTkinter) |
| P3: 图标注入/UAC/版本信息 | FR-BLD-007,008,020 | PyInstaller 参数 |
| P3: inspect/extract 工具 | FR-BLD-010, FR-CFG-004,005 | 结构读取 |
| P4: 静默模式 /S | FR-RT-009 | 参数解析 |
| P4: PATH / env 追加 | FR-ENV-001..003 | 注册表 |
| P4: 完成页选项 | FR-RT-014 | UI 扩展 |
| P5: MRU / 配置往返 | FR-BLD-016,018 | GUI 持久化 |
| P5: 配置一致性 hash | FR-BLD-015 | 再构建对比 |

---
## 16. 迭代与里程碑 (建议 5 Sprint)
| Sprint | 目标 | 交付 |
|--------|------|------|
| 1 (2w) | 构建核心 P1 | CLI build 出最小 EXE (无 UI Runtime) |
| 2 (2w) | Runtime 基础 + UI 骨架 | 解压 + 进度 + Welcome/路径/协议页面 |
| 3 (2w) | 脚本与日志 & GUI 完整 | 脚本流式输出 + GUI 向导可构建 |
| 4 (2w) | 增强特性 | 静默安装 / inspect / extract / 图标注入 |
| 5 (2w) | 硬化与优化 | 性能调优 / NFR 验证 / 文档 / 风险清理 |

---
## 17. 测试策略
| 类型 | 范围 | 工具 |
|------|------|------|
| 单元 | 压缩/哈希/配置/schema | pytest |
| 集成 | build → runtime 解包一致 | 生成临时 EXE |
| UI 功能 | Tk 组件交互（`pytest + send_events` 自建封装） | 半自动 |
| 性能 | 100MB 压缩/解压时长 | time 测量 |
| 高 DPI | 手工 + 截图像素比对 | 人工 |
| 安全 | 篡改归档/脚本路径穿越 | 用例 |
| 静默 | /S 执行退出码 | 自动脚本 |

---
## 18. 实现风险与缓解
| 风险 | 影响 | 缓解 |
|------|------|------|
| PyInstaller 体积较大 | 最终 EXE > 15MB | 后期换 C++ Stub / UPX 可选 |
| Tk 高 DPI 缩放不一致 | UI 模糊/布局挤压 | 启动时设 scaling；所有像素常量走 dpi_scale()；测试 125/150/200/300% |
| 大体量文件列表 (10万+ 项) | UI 卡顿 | 懒加载 + 分页 + 只在展开目录时列举 |
| 2GB 输入压缩耗时 | 构建 > 允许时间 | Streaming + 多线程读队列 + 调整 zstd level（默认 10 可配置）|
| 500MB+ 安装器写盘 I/O 峰值 | 构建阶段 I/O 瓶颈 | 顺序写 + 8~16MB 缓冲；禁用 OS 缓冲 flush 频率过高 |
| Streaming 压缩内存峰值 | 超出 2×限制 | 分块 4~8MB | 
| 脚本卡死 | 阻塞安装 | 超时 + watchdog 线程 |
| PATH 修改失败 | 权限问题 | 捕获异常→警告 |
| 用户杀进程 | 半文件残留 | 临时目录 + 完成后 move |

---
## 19. 可扩展挂点
| 接口 | 方法 | 未来用途 |
|------|------|----------|
| `Compressor` | `compress(stream)` | 新增算法（brotli, lzma） |
| `ScriptExecutor` | `run(script_meta)` | 新增脚本类型（PowerShell Core, Python 内置） |
| `HeaderMigrator` | `migrate(old, target)` | Schema 升级 |
| `EnvUpdater` | `apply(actions)` | 分层权限策略 |
| `LoggerSink` | `emit(event)` | 远程日志 / 结构化管线 |

---
## 结论
该实现计划以“先交付可运行最小闭环”→“完善 UI 与脚本”→“增强与硬化”为主线，严格映射需求文档。所有关键结构（Header、压缩、脚本输出、GUI MVVM/CustomTkinter 抽象）均已定义清晰边界，可并行开发。后续若需要 Runtime 切换至原生 C++ 或 GUI 升级到 Qt 仅需复刻 GUI 与事件桥接层，业务与归档协议保持不变。

> 后续更新：加入具体类图、时序图（若需要），以及性能基准初稿。
