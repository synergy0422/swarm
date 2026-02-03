# Phase 24: swarm_tasks_bridge.sh 实现 - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

创建 `scripts/swarm_tasks_bridge.sh` CLI 脚本，实现 claim/done/fail 三个子命令：
- `claim <task_id> <worker> [lock_key]` — 自动调用 `swarm_lock.sh acquire` + `swarm_status_log.sh append START`
- `done <task_id> <worker> [lock_key]` — 自动调用 `swarm_lock.sh release` + `swarm_status_log.sh append DONE`
- `fail <task_id> <worker> <reason> [lock_key]` — 自动调用 `swarm_lock.sh release` + `swarm_status_log.sh append ERROR`

同时更新 README.md 和 docs/SCRIPTS.md 文档。

</domain>

<decisions>
## Implementation Decisions

### 输出格式与日志级别

- **成功输出**: 详细成功消息（例如 `Lock acquired for 'task-001'`）
- **错误输出**: 打印详细错误原因到 stderr，脚本退出
- **调试模式**: LOG_LEVEL 环境变量控制 debug 日志
- **状态日志**: 保留 `swarm_status_log.sh append` 的输出，用户可看到状态记录

### 退出码策略

- **成功**: 退出码 0
- **锁被占用（claim 时）**: 退出码 2（区分于其他错误）
- **其他失败**: 退出码 1

### 参数验证严格程度

- **参数缺失**: 立即报错退出，显示具体缺少哪个参数
- **lock_key 格式**: 透传给 swarm_lock.sh，不额外验证
- **worker 名称**: 透传，不验证（允许任意字符串）
- **reason 参数**: fail 命令的 reason 为必填，不提供则报错

### 与现有脚本集成

- **脚本风格**: 参考 `swarm_task_wrap.sh` 的结构模式
- **help 子命令**: 通过 `--help/-h` 访问帮助，无独立 help 命令
- **环境变量覆盖**: 不允许环境变量覆盖参数，参数优先
- **依赖脚本缺失**: 报错，提示依赖脚本缺失

### 文档规范

- **示例复杂度**: 提供完整工作流示例（claim → work → done）和独立子命令示例
- **错误场景文档**: 列出所有错误码及对应解决方案

</decisions>

<specifics>
## Specific Ideas

参考现有脚本风格：
- `swarm_task_wrap.sh` — 任务包装器结构
- `swarm_lock.sh` — 锁操作底层逻辑
- `swarm_status_log.sh` — 状态日志记录

错误输出格式参考 `swarm_lock.sh` 的错误消息风格。

</specifics>

<deferred>
## Deferred Ideas

- 自动重试执行功能 — v1.86+（本版本只提供手动重试流程说明）
- 任务自动调度系统 — 独立里程碑

</deferred>

---

*Phase: 24-swarm_tasks_bridge_sh*
*Context gathered: 2026-02-03*
