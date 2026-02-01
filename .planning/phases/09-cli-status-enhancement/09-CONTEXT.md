# Phase 9: CLI 状态增强 - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

在 `swarm status` 命令中添加 `--panes` 参数，显示 4 个 tmux 窗口的内容快照。

**命令行为**：
- `swarm status` — 保持现有输出（任务状态）
- `swarm status --panes` — 在现有输出后追加 4 窗口 pane 快照

**不包括**：
- Web 监控面板（后续版本）
- JSON 输出格式（本版本不做）
- 实时流式更新（本版本不做）
- 窗口过滤参数（如 `--only`）（本版本不做）

</domain>

<decisions>
## Implementation Decisions

### 输出格式
- **行数限制**：每个窗口固定显示最近 20 行（-S -30）
- **状态图标**：仅三类
  - `[ERROR]` — 包含 "Error" 或 "Failed"
  - `[DONE]` — 包含 "DONE" 或 "Complete"
  - `[ ]` — 其他情况

### 窗口选择与过滤
- **窗口顺序**：固定顺序 master → worker-0 → worker-1 → worker-2
- **过滤参数**：暂不支持（保持简单）
- **缺失处理**：窗口不存在显示 `(missing)` 或 `(no output)`，不报错

### 异常处理
- **tmux 不可用**：打印 warning，跳过 panes 显示，命令返回 0
- **session 不存在**：保持现有 status 提示（如 "No swarm session found"）
- **区分逻辑**：
  - tmux 命令本身不存在 → warning
  - session 名称不存在 → 保持现有行为

### 命令行为
- **无 `--panes`**：保持现有 `swarm status` 输出
- **有 `--panes`**：先输出现有 status，再追加 panes 快照（追加而非替换）

</decisions>

<specifics>
## Specific Ideas

无特定引用。采用标准实现：
- 使用 TmuxCollaboration.capture_all_windows() 批量捕获
- 窗口顺序通过列表硬编码控制
- 20 行限制通过 `-S -30` 实现（取最近 30 行，取最后 20 行）

</specifics>

<deferred>
## Deferred Ideas

- `--only workers` 过滤参数 — Phase 待定
- `--json` JSON 输出格式 — Phase 待定
- Web 实时监控面板 — v1.2 或后续版本
- 实时流式更新（类似 `watch swarm status --panes`）— 后续版本

</deferred>

---

*Phase: 09-cli-status-enhancement*
*Context gathered: 2026-02-01*
