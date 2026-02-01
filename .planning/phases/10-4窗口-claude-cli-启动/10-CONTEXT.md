# Phase 10: 4 窗口 Claude CLI 启动 - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

创建启动脚本，在 tmux 中看到 4 个 Claude Code CLI 交互窗口（master + worker-0/1/2）。

范围：仅启动脚本和 4 窗口可见性验证。不包含实际的任务分发、通信协议实现（那些是后续 phase 的内容）。

</domain>

<decisions>
## Implementation Decisions

### 会话名称
- 固定名称：`swarm-claude-default`
- 便于 `tmux attach -t swarm-claude-default`

### 工作目录
- 可配置：支持环境变量或 CLI 参数覆盖
- 默认值：`/home/user/projects/AAA/swarm`
- 允许用户通过配置或参数指定其他目录

### 启动后焦点
- 聚焦 master 窗口
- 用户启动后直接看到 master 的 Claude CLI

### 依赖检查
- 只检查 claude CLI 是否可用
- `command -v claude >/dev/null || exit 1`
- 简洁报错，不提供替代方案

### 附加方式
- 支持 `--attach` / `--no-attach` 参数
- 默认行为：attach 到会话
- 允许脚本创建后不自动进入 tmux

</decisions>

<specifics>
## Specific Ideas

- 参考：v1.1 的 `swarm status --panes` 风格（简洁、工具化）
- 脚本风格：类 `run_swarm.sh`，但针对 Claude CLI 场景优化

</specifics>

<deferred>
## Deferred Ideas

- 任务分发协议实现 — Phase 11+
- Master-Worker 消息通信 — Phase 11+
- Worker 状态回报机制 — Phase 11+

</deferred>

---

*Phase: 10-4窗口-claude-cli-启动*
*Context gathered: 2026-02-01*
