# InstaPro 需求说明书（最终版）

版本：1.0  
状态：正式版 (Final)  
更新日期：2025-09-24  
语言：中文（本版本仅提供中文界面与文档，不支持多语言）  
作者：项目组  

---

## 1. 概述

InstaPro 是一个面向 Windows 平台的 **单文件自解压安装器（Self-Extracting Installer）构建与运行系统**。  
由两大部分组成：  
1. **构建端（Builder：CLI + GUI）**：读取 YAML 配置、管理文件与脚本、设定版本与显示信息、压缩并生成最终安装器 EXE。  
2. **运行端（Runtime Stub / 安装器）**：为最终用户提供安装界面（GitHub Light 风格 + 高 DPI 支持）、协议展示、路径选择、文件解压与脚本执行。

本最终需求在前期 v0.1 / v0.2 版本的基础上统一整理，并纳入新增约束与确认：
- 配置文件格式统一为 YAML（不再支持 JSON）。
- 构建端 GUI 与 安装端 UI 全部使用 GitHub Light 主题，并支持高清 / 高 DPI 自适应显示。
- 构建端支持设置安装器窗口标题、欢迎页主标题与副标题文案。
- 不支持多语言（仅中文文案）。
- 脚本执行输出内嵌至安装 UI，不弹控制台窗口。
- 支持自定义安装器 ICO 图标。
- 其他原有功能保持。

---

## 2. 范围

### 2.1 范围内 (MVP Final)
- 文件/目录打包 → 单 EXE
- 压缩：Zstd（优先）+ Zip 回退
- 统一 YAML 配置
- 构建端：CLI + GUI 向导/高级模式
- 构建端可视化文件/脚本管理
- 自定义安装器标题、欢迎语（主标题、副标题）
- 自定义图标 (.ico)
- Version Info & UAC manifest
- License / 隐私声明（文本显示 & 强制同意控制）
- 安装路径策略（默认 / 可选 / 隐藏）
- 安装 UI：GitHub Light 风格 + 高 DPI
- 脚本执行（PowerShell / Batch）+ 内嵌实时输出（隐藏外窗）
- 环境变量 / PATH 追加
- 归档哈希校验（完整性保障）
- 静默安装模式 `/S`
- 安装日志与构建日志
- 配置保存 / 另存 / 最近打开 / schema 版本校验
- inspect / extract 工具
- 安装完成交互（可选：打开目录 / 运行主程序）

### 2.2 范围外 (本版本不实现)
- 多语言 / 国际化
- 在线下载 / 增量更新
- 自动生成卸载器
- 数字签名自动化
- 差分补丁 / 增量构建
- Web 管理平台
- 深色主题 / 主题插件
- 复杂脚本条件表达式语言
- 安全沙箱 / 权限隔离
- 自动依赖安装

---

## 3. 利益相关者

| 角色 | 诉求 |
|------|------|
| 构建工程师 | 图形化降低门槛 / 可重复构建 / 配置直观 |
| 发行与产品 | 可品牌化（标题 / 欢迎语 / 图标 / 版本信息） |
| 最终用户 | 简洁、熟悉风格、无冗余弹窗、清晰进度 |
| 运维 / 批量部署 | 静默安装、退出码明确、日志可审计 |
| 安全 / 合规 | 内容完整性校验、权限行为可控 |
| QA | 可检视头信息 / 可重复性验证 |

---

## 4. 用户场景 (部分)

| 场景ID | 描述 | 参与者 | 成功判定 |
|--------|------|--------|----------|
| UC-001 | GUI 向导首次创建安装包 | 构建工程师 | 输出可用 EXE |
| UC-002 | 自定义安装器标题与欢迎文案 | 构建工程师 | 安装窗口显示一致 |
| UC-003 | 批量部署静默安装 | 运维 | 返回码=0 无 UI |
| UC-004 | 安装脚本注册服务并输出日志 | 用户/运维 | 脚本输出内嵌显示 |
| UC-005 | 配置文件再次加载重构建 | 构建工程师 | 内容一致无差异 |
| UC-006 | QA 校验归档未被篡改 | QA | 哈希匹配 |
| UC-007 | 高 DPI 屏显示 UI 清晰 | 最终用户 | 无模糊拉伸 |
| UC-008 | 替换图标后重建 | 构建工程师 | 资源查看器可见新图标 |

---

## 5. 术语

| 术语 | 定义 |
|------|------|
| Builder GUI | 图形化打包工具 |
| Runtime Stub | 安装器运行时主体 |
| Header | 内嵌在 EXE 中的 JSON 元数据（结构化定义） |
| Archive | 压缩数据段（Zstd / Zip） |
| Post Script | 解压完成后执行脚本 |
| Silent Mode | 静默安装模式（无界面） |
| In-UI Script Output | 脚本输出内嵌显示区域 |
| High DPI 支持 | 125% ~ 300% 缩放下清晰展示 |

---

## 6. 功能需求 (Functional Requirements)

命名分类：
- 构建端核心：`FR-BLD-*`
- 构建端 GUI：`FR-BGUI-*`
- 运行端：`FR-RT-*`
- 安装 UI：`FR-UI-*`
- 脚本：`FR-SCR-*`
- 资源/图标：`FR-RES-*`
- 配置：`FR-CFG-*`
- 日志：`FR-LOG-*`
- 环境变量：`FR-ENV-*`
- 安全/完整性：`FR-SEC-*`
- 兼容性/回退：`FR-COMP-*`

### 6.1 构建端 (Builder Core)

| ID | 描述 | 优先级 | 验收标准 |
|----|------|--------|----------|
| FR-BLD-001 | 读取 YAML 配置 | Must | validate 通过 |
| FR-BLD-002 | 递归收集文件 | Must | 文件计数正确 |
| FR-BLD-003 | 排除模式（glob） | Should | 指定文件排除 |
| FR-BLD-004 | 生成单 EXE 安装器 | Must | 可执行 |
| FR-BLD-005 | Zstd 压缩 | Must | algo=zstd |
| FR-BLD-006 | Zip 回退 | Should | zstd 不可用自动回退 |
| FR-BLD-007 | 版本信息注入 | Must | 文件属性显示 |
| FR-BLD-008 | UAC manifest 注入 | Must | requireAdministrator 触发 UAC |
| FR-BLD-009 | SHA-256 哈希生成 | Must | inspect 可见 |
| FR-BLD-010 | CLI build/validate/inspect/extract | Must | 命令执行正常 |
| FR-BLD-011 | License/Privacy 文本注入 | Must | 安装端显示 |
| FR-BLD-012 | Post 脚本元数据注入 | Must | header 保留 |
| FR-BLD-013 | 默认安装路径配置 | Must | header.install.default_path |
| FR-BLD-014 | 构建日志输出 | Must | 日志含阶段标签 |
| FR-BLD-015 | 同配置一致性（hash 稳定） | Should | 重复构建 hash 一致 |
| FR-BLD-016 | 配置保存 / 另存 / 加载 | Must | 内容往返无差异 |
| FR-BLD-017 | 配置 schema 版本校验 | Should | 不兼容报警 |
| FR-BLD-018 | 最近使用配置列表 (MRU) | Could | GUI 显示 |
| FR-BLD-019 | GUI 生成对应 CLI 命令 | Could | 可复制 |
| FR-BLD-020 | 自定义安装器图标设置 | Must | 资源注入成功 |
| FR-BLD-021 | 设置安装器窗口标题 | Must | 运行端窗口匹配 |
| FR-BLD-022 | 设置欢迎页主标题与副标题 | Must | 安装 UI 显示正确 |

（JSON 支持原 FR-CFG-002 已废弃，不再保留）

### 6.2 构建端 GUI

| ID | 描述 | 优先级 | 验收标准 |
|----|------|--------|----------|
| FR-BGUI-001 | 向导模式（产品→文件→协议→脚本→压缩→构建） | Must | 顺序可导航 |
| FR-BGUI-002 | 高级模式（集中编辑） | Should | 模式切换保留数据 |
| FR-BGUI-003 | 文件/目录拖拽 | Should | 显示条目 |
| FR-BGUI-004 | 文件列表展示大小/相对路径 | Should | 表格更新 |
| FR-BGUI-005 | 脚本管理（增删/类型/隐藏执行标记） | Must | header 同步 |
| FR-BGUI-006 | 协议文件选择 + 预览 | Should | 文本区显示 |
| FR-BGUI-007 | 实时校验（字段错误高亮） | Must | 输入错误即提示 |
| FR-BGUI-008 | 构建进度状态面板 | Must | 阶段切换显示 |
| FR-BGUI-009 | 实时构建日志窗口 | Should | 自动滚动 |
| FR-BGUI-010 | 图标文件(.ico) 选择 + 预览 | Must | 预览 32x32/64x64 |
| FR-BGUI-011 | 未保存修改关闭提醒 | Should | 弹出确认 |
| FR-BGUI-012 | 导出 YAML | Must | 与内部模型一致 |
| FR-BGUI-013 | 最近配置快速打开 | Could | MRU 更新 |
| FR-BGUI-014 | 配置变更即时同步模型 | Must | 双向绑定 |
| FR-BGUI-015 | GitHub Light 主题 + 高 DPI 支持 | Must | 125%+ 清晰 |
| FR-BGUI-016 | 标题/欢迎语可视化输入预览 | Must | 预览区文本一致 |

### 6.3 运行端 (Runtime Stub)

| ID | 描述 | 优先级 | 验收标准 |
|----|------|--------|----------|
| FR-RT-001 | Header 解析 | Must | 成功或错误退出 |
| FR-RT-002 | Magic & 版本校验 | Must | 非法拒绝 |
| FR-RT-003 | 归档哈希校验 | Must | 篡改失败 |
| FR-RT-004 | UAC 自提升 | Must | 管理员需求触发 |
| FR-RT-005 | 安装路径选择/确认 | Must | 写入成功 |
| FR-RT-006 | 隐藏路径模式 | Should | UI 跳过路径页 |
| FR-RT-007 | 解压目录结构保持 | Must | 文件一致 |
| FR-RT-008 | 解压进度反馈 | Must | 百分比+文件名 |
| FR-RT-009 | 静默模式 `/S` | Must | 无 UI |
| FR-RT-010 | 解压失败记录 | Must | 日志含错误 |
| FR-RT-011 | 退出码规范 (0=成功) | Must | 脚本可识别 |
| FR-RT-012 | 安装日志输出 | Must | install.log |
| FR-RT-013 | 目标已存在策略（提示覆盖/取消） | Should | 交互明确 |
| FR-RT-014 | 完成页操作（打开目录/运行程序） | Could | 选项正常 |
| FR-RT-015 | 脚本在 UI 内嵌执行输出 | Must | 实时刷新 |
| FR-RT-016 | 无控制台弹窗/黑框 | Must | 不出现 | 
| FR-RT-017 | ANSI 彩色输出（可降级） | Could | 彩色或自动去色 |
| FR-RT-018 | 使用配置中自定义窗口标题 | Must | 标题一致 |
| FR-RT-019 | 欢迎页显示构建端配置的主/副标题 | Must | UI 匹配 |

### 6.4 安装 UI

| ID | 描述 | 优先级 | 验收标准 |
|----|------|--------|----------|
| FR-UI-001 | GitHub Light 主题 | Must | 色值规范 |
| FR-UI-002 | 高 DPI 自适应 | Must | ≥200% 不模糊 |
| FR-UI-003 | 页面流：欢迎→协议→隐私(可选)→路径→进度→完成 | Must | 顺序正确 |
| FR-UI-004 | 欢迎页展示主标题、副标题 | Must | 与配置一致 |
| FR-UI-005 | License 同意后才能继续 | Must | 按钮解锁 |
| FR-UI-006 | 隐私声明可选显示 | Should | 配置控制 |
| FR-UI-007 | 进度显示当前文件名 + 百分比 | Must | 真值更新 |
| FR-UI-008 | 脚本输出区域（可折叠） | Must | 实时滚动 |
| FR-UI-009 | 安装失败错误提示 | Must | 简洁消息 |
| FR-UI-010 | 支持窗口最小化 | Could | 状态保持 |
| FR-UI-011 | 安装器窗口标题来自配置 | Must | 一致 |

### 6.5 脚本 (Post Actions)

| ID | 描述 | 优先级 | 验收标准 |
|----|------|--------|----------|
| FR-SCR-001 | PowerShell 脚本 | Must | 执行成功 |
| FR-SCR-002 | Batch 脚本 | Must | 执行成功 |
| FR-SCR-003 | 隐藏执行（无外窗） | Must | 不出现黑框 |
| FR-SCR-004 | 超时终止 | Should | 超时日志记录 |
| FR-SCR-005 | 失败不阻断主流程（默认策略） | Must | 主流程成功仍退出 0 |
| FR-SCR-006 | 输出捕获流式显示 | Must | UI 同步 |
| FR-SCR-007 | 控制台颜色处理（可降级） | Could | 避免乱码 |
| FR-SCR-008 | 限制执行路径（安装目录内） | Should | 安全控制 |

### 6.6 资源 / 图标

| ID | 描述 | 优先级 | 验收标准 |
|----|------|--------|----------|
| FR-RES-001 | 自定义 .ico 图标注入 | Must | 资源查看器显示 |
| FR-RES-002 | 非法 ICO 自动回退默认 | Must | 不崩溃 |
| FR-RES-003 | GUI 预览多尺寸 | Should | 至少 32/64 |
| FR-RES-004 | 默认提供内置图标 | Must | 未设置时正常 |

### 6.7 配置 (YAML 专属)

| ID | 描述 | 优先级 | 验收标准 |
|----|------|--------|----------|
| FR-CFG-001 | 仅支持 YAML | Must | JSON 拒绝并提示 |
| FR-CFG-003 | CLI 参数覆盖关键字段 | Should | 覆盖后生效 |
| FR-CFG-004 | inspect 输出完整 header JSON | Must | 可解析 |
| FR-CFG-005 | extract 解出全部文件 | Should | 文件一致 |
| FR-CFG-006 | PATH 追加 | Should | 生效 |
| FR-CFG-007 | GUI 双向绑定模型 | Must | 修改即反映 |
| FR-CFG-008 | schema version 字段 | Should | 不同版本警告 |
| FR-CFG-009 | 安装器窗口标题字段 | Must | runtime 使用 |
| FR-CFG-010 | 欢迎页主标题字段 | Must | runtime 使用 |
| FR-CFG-011 | 欢迎页副标题字段 | Must | runtime 使用 |

（原“JSON 支持”项废弃）

### 6.8 日志

| ID | 描述 | 优先级 | 验收标准 |
|----|------|--------|----------|
| FR-LOG-001 | Builder 日志级别 | Should | --verbose 生效 |
| FR-LOG-002 | Runtime 阶段标记 | Must | 含阶段标签 |
| FR-LOG-003 | 脚本 stdout/stderr 捕获 | Must | 日志保存 |
| FR-LOG-004 | 写入异常堆栈 | Must | trace 可见 |
| FR-LOG-005 | GUI 构建日志面板 | Should | 实时 |
| FR-LOG-006 | GUI 日志导出 | Could | 保存为 .log |
| FR-LOG-007 | 标记协议同意状态 | Must | Accepted=Yes/No |

### 6.9 环境变量

| ID | 描述 | 优先级 | 验收标准 |
|----|------|--------|----------|
| FR-ENV-001 | PATH 追加（用户或系统） | Should | 新终端可用 |
| FR-ENV-002 | 自定义变量写入 | Should | 注册表存在 |
| FR-ENV-003 | 失败不阻断安装 | Must | 记录警告 |

### 6.10 安全 / 完整性

| ID | 描述 | 优先级 | 验收标准 |
|----|------|--------|----------|
| FR-SEC-001 | 归档 SHA-256 校验 | Must | 损坏退出 |
| FR-SEC-002 | 权限与 manifest 一致 | Must | 行为匹配 |
| FR-SEC-003 | 临时文件清理 | Should | 无冗余 |
| FR-SEC-004 | 脚本路径限制 | Should | 防跳出目录 |

### 6.11 兼容 / 回退

| ID | 描述 | 优先级 | 验收标准 |
|----|------|--------|----------|
| FR-COMP-001 | 支持 Windows 10 及以上 (x64) | Must | 测试通过 |
| FR-COMP-002 | zstd 缺失时 zip 回退 | Should | 日志记录 |
| FR-COMP-003 | 运行端不依赖已安装 Python | Must | 纯单文件 |

---

## 7. 非功能需求 (NFR)

| 分类 | 编号 | 描述 | 验收 |
|------|------|------|------|
| 性能 | NFR-PERF-001 | 100MB 解压 ≤ 8s（SSD, Zstd lvl 10） | 实测 |
| 性能 | NFR-PERF-002 | 构建内存占用 ≤ 2×归档大小 | 监控 |
| 性能 | NFR-PERF-003 | 脚本输出延迟 < 300ms | 压测 |
| 可靠性 | NFR-REL-001 | 安装失败可重试 | 再次成功 |
| 可靠性 | NFR-REL-002 | 解压中断不留半文件 | 使用临时目录 |
| 可靠性 | NFR-REL-003 | GUI 崩溃不损坏配置 | 配置仍可加载 |
| 可用性 | NFR-USE-001 | 向导步骤 ≤ 6 主阶段 | 验证 |
| 可用性 | NFR-USE-002 | 进度刷新 ≥ 每秒 4 次 | 日志/观察 |
| 可用性 | NFR-USE-003 | 高 DPI 无模糊 | 200% 实测 |
| 可维护性 | NFR-MAINT-001 | 单模块不超 800 行 | 代码审查 |
| 可维护性 | NFR-MAINT-002 | GUI 逻辑与视图分层 (MVVM/MVC) | 架构评审 |
| 扩展性 | NFR-EXT-001 | 新增压缩算法仅实现接口 | 演示 |
| 扩展性 | NFR-EXT-002 | 更换图标无需改核心逻辑 | 验证 |
| 安全 | NFR-SEC-001 | 不执行安装目录外脚本 | 测试 |
| 合规 | NFR-LAW-001 | 协议接受写入日志 | 日志行 |
| 兼容 | NFR-COMP-001 | 仅 64-bit PE | 属性检测 |
| 文档 | NFR-DOC-001 | YAML 字段说明集中 | README 附录 |

---

## 8. 配置 YAML 字段摘要（核心）

```yaml
product:
  name: "产品名称"
  version: "1.2.3"
  company: "公司名"
  description: "产品描述"

config:
  version: 1  # schema 版本

resources:
  icon: "./icons/app.ico"  # 可选

ui:
  window_title: "InstaPro 安装程序"
  welcome_heading: "欢迎使用 DemoApp 安装向导"
  welcome_subtitle: "快速、可靠、简洁的安装体验"
  theme: "github-light"  # 固定
  show_progress_script_output: true

install:
  default_path: "%ProgramFiles%/DemoApp"
  allow_user_path: true
  force_hidden_path: false
  show_ui: true
  silent_allowed: true
  license_file: "./LICENSE.txt"
  privacy_file: "./PRIVACY.txt"

compression:
  algo: zstd
  level: 10

inputs:
  - path: ./bin
  - path: ./config
exclude:
  - "*.psd"
  - "__pycache__/"

post_actions:
  - type: powershell
    command: scripts/Init-Service.ps1
    hidden: true
    timeout_sec: 300
    show_in_ui: true
    run_if: always

env:
  add_path:
    - bin
  set:
    APP_ENV: production
```

新增/关键字段说明：

| 字段 | 说明 | 必填 | 示例 |
|------|------|------|------|
| ui.window_title | 安装器窗口标题 | 可选 | "DemoApp 安装" |
| ui.welcome_heading | 欢迎页主标题 | 可选 | "欢迎安装 DemoApp" |
| ui.welcome_subtitle | 欢迎页副标题 | 可选 | "请按步骤完成安装" |
| resources.icon | 自定义图标路径 | 可选 | "./app.ico" |
| post_actions[*].show_in_ui | 是否在 UI 输出区显示执行日志 | 可选 | true |
| config.version | 配置 schema 版本 | 建议 | 1 |

---

## 9. 验收测试（概要）

| 测试项 | 用例 |
|--------|------|
| 构建一致性 | 同配置两次 hash 相同 |
| 图标替换 | 设置新 .ico 构建后资源可见 |
| 高 DPI | Windows 缩放 200% 时界面清晰 |
| 脚本输出 | 长时间脚本输出逐行滚动 |
| 协议流程 | 未同意不可继续 |
| 静默安装 | `/S` 不出现 UI 并成功安装 |
| 破坏归档 | 修改尾部字节 → 安装失败 |
| 安装路径存在 | 覆盖确认流程正常 |
| YAML 校验 | 缺失必填字段报错并定位 |

---

## 10. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 大文件占用内存 | 构建/解压缓慢 | 流式处理、分块压缩 |
| ICO 非法导致崩溃 | 构建失败 | 预解析校验 + 回退默认 |
| 脚本阻塞 UI | 卡死 | 线程 + 队列 + 超时 |
| 高 DPI 布局错位 | 体验差 | 使用矢量/布局容器 |
| YAML 字段拼写错误 | 构建失败 | 严格 schema 校验 |
| 不规范脚本权限风险 | 安全隐患 | 限制脚本路径 / 文档提示 |

---

## 11. 未来可扩展列表（参考）

| 功能 | 价值 |
|------|------|
| 深色主题 | 夜间使用体验 |
| 多语言支持 | 市场扩展 |
| 签名集成 | 信任提升 |
| 增量更新 | 降低分发成本 |
| 自动卸载器 | 生命周期管理 |
| 条件脚本执行 DSL | 灵活部署 |
| 远程日志上报 | 运维可观测性 |

---

## 12. 变更记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 0.1 | 2025-09-24 | 初始需求草稿 |
| 0.2 | 2025-09-24 | 引入 GUI / 图标 / 脚本内嵌输出 |
| 1.0 | 2025-09-24 | 最终版：限定 YAML、仅中文、标题与欢迎语、高清支持、结构清理 |

---

## 13. 附录：需求统计

| 分类 | 数量 |
|------|------|
| 功能需求 (FR) | 约 90 条 |
| 非功能 (NFR) | 16 条 |
| 配置核心字段 | 20+ |
| 范围外建议 | 6+ |

---

本需求说明书（版本 1.0）为当前实现与测试基线，后续修改需提交评审并更新版本号。  