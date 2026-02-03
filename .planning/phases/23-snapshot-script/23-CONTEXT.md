# Phase 23: 快照脚本实现 - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

实现 `scripts/swarm_snapshot.sh` 脚本，一键采集 tmux swarm 运行状态并输出到时间戳目录。脚本为只读操作，不创建/修改任何状态文件。

</domain>

<decisions>
## Implementation Decisions

### 输出目录结构
- **分目录分类结构**，非扁平或单一文件
- 结构：`<snapshot_dir>/{tmux/, state/, locks/, meta/, panes/}`
- 便于定位问题和增量对比

### Pane 输出格式
- **纯文本 + 每行前缀 pane 标识**
- 格式：`[session:window.pane] <content>`
- 示例：`[swarm-claude-default:0.0] [TASK] task-001`

### 默认行数
- **SNAPSHOT_LINES 默认 50 行**
- 平衡上下文丰富度和信息密度

### 目录已存在处理
- **自动追加时间戳**
- 避免手动清理，降低误操作风险

### 缺失文件处理
- **摘要文件提示缺失**
- 在 SUMMARY.txt 中标记 "NOT FOUND" 而非静默跳过

### Git 版本信息
- **记录完整 git status**
- 包含 dirty state、分支信息，用于判断代码状态

### 错误处理
- **部分失败继续执行，生成完整报告 + 错误摘要**
- 非阻塞式错误收集，用户可看到哪些部分失败

### 摘要文件
- **需要 SUMMARY.txt**
- 包含：快照时间、会话名称、pane 数量、文件清单、错误摘要

</decisions>

<specifics>
## Specific Ideas

- "分目录结构更利于定位与增量对比"
- "每行带 pane 标识便于区分来源"
- "50 行既有上下文又不太噪"
- "自动追加时间戳避免覆盖"
- "写入摘要提示缺失更直观"
- "记录 git status 可判断 dirty/分支"
- "继续执行并给错误摘要最实用"
- "需要 summary 便于快速定位"

</specifics>

<deferred>
## Deferred Ideas

- 自动压缩快照 — 手动 gzip 即可
- 远程快照上传 — 超出诊断工具范畴
- 快照对比功能 — 可用 diff 工具手动比较

</deferred>

---

*Phase: 23-snapshot-script*
*Context gathered: 2026-02-03*
