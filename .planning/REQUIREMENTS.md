# Requirements: AI Swarm v1.90

**Defined:** 2026-02-04
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## v1.90 Requirements

Requirements for "统一任务入口 CLI" milestone.

### CLI Commands

- [ ] **CLI-01**: 新增 `swarm task` 子命令入口
  - 在 `swarm/cli.py` 中添加 task 子命令解析器
  - 使用 argparse subparsers 结构

- [ ] **CLI-02**: `swarm task claim <task_id> <worker> [lock_key]`
  - 调用 `scripts/swarm_tasks_bridge.sh claim "$@"`
  - 透传退出码（0=成功, 2=锁占用, 1=其他错误）

- [ ] **CLI-03**: `swarm task done <task_id> <worker> [lock_key]**
  - 调用 `scripts/swarm_tasks_bridge.sh done "$@"`
  - 透传退出码（0=成功, 1=失败）

- [ ] **CLI-04**: `swarm task fail <task_id> <worker> <reason> [lock_key]**
  - 调用 `scripts/swarm_tasks_bridge.sh fail "$@"`
  - 透传退出码（0=成功, 1=失败）

- [ ] **CLI-05**: `swarm task run <task_id> <worker> <command...>**
  - 调用 `scripts/swarm_task_wrap.sh run "$@"`
  - 透传命令退出码

### Exit Code Handling

- [ ] **EXIT-01**: CLI 退出码与底层脚本一致
  - claim: 0=成功, 2=锁占用, 1=其他错误
  - done: 0=成功, 1=失败
  - fail: 0=成功, 1=失败
  - run: 命令的退出码

### Documentation

- [ ] **DOCS-01**: README.md 新增 `swarm task` 用法示例
  - 包含各子命令的用法
  - 包含退出码说明

- [ ] **DOCS-02**: docs/SCRIPTS.md 增加 `swarm task` 说明
  - 参数表格
  - 示例
  - 退出码对照表

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| codex 联动 | 本版本不做 |
| 任务锁逻辑修改 | 复用现有脚本 |
| 新增 swarm 子命令 | 仅添加 task 子命令 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLI-01 | Phase 32 | Pending |
| CLI-02 | Phase 32 | Pending |
| CLI-03 | Phase 32 | Pending |
| CLI-04 | Phase 32 | Pending |
| CLI-05 | Phase 32 | Pending |
| EXIT-01 | Phase 32 | Pending |
| DOCS-01 | Phase 33 | Pending |
| DOCS-02 | Phase 33 | Pending |

**Coverage:**
- v1.90 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0

---
*Requirements defined: 2026-02-04*
*Last updated: 2026-02-04 after milestone initialization*
