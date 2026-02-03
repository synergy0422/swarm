# Requirements: AI Swarm v1.85

**Defined:** 2026-02-03
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## v1.85 Requirements

Requirements for the Claude Tasks Integration milestone.

### TASK-01: swarm_tasks_bridge.sh 脚本基础

- [x] **TASK-01**: 创建 `scripts/swarm_tasks_bridge.sh` 主框架和帮助文档

### TASK-02: claim 子命令

- [x] **TASK-02**: 实现 claim <task_id> <worker> [lock_key]
- [x] **TASK-03**: 默认 lock_key = task_id
- [x] **TASK-04**: 自动调用 `swarm_lock.sh acquire <lock_key> <worker>`
- [x] **TASK-05**: 记录状态 `swarm_status_log.sh append START <worker> <task_id>`

### TASK-06: done 子命令

- [x] **TASK-06**: 实现 done <task_id> <worker> [lock_key]
- [x] **TASK-07**: 自动调用 `swarm_lock.sh release <lock_key> <worker>`
- [x] **TASK-08**: 记录状态 `swarm_status_log.sh append DONE <worker> <task_id>`

### TASK-07: fail 子命令

- [x] **TASK-09**: 实现 fail <task_id> <worker> <reason> [lock_key]
- [x] **TASK-10**: 自动调用 release
- [x] **TASK-11**: 记录状态 `swarm_status_log.sh append ERROR <worker> <task_id> <reason>`

### TASK-08: 错误处理

- [x] **TASK-12**: acquire 失败 → 退出 1，打印原因
- [x] **TASK-13**: release 失败 → 退出 1
- [x] **TASK-14**: 任何错误不得吞掉

### TASK-09: 文档更新

- [x] **TASK-15**: README.md 新增"Claude Tasks 协作流程"章节
- [x] **TASK-16**: docs/SCRIPTS.md 新增 swarm_tasks_bridge.sh 完整文档

## v1.85 文档规范

### 任务命名规范

推荐格式：
- `task-YYYYMMDD-序号` — 例如 `task-20260203-01`
- `task-模块-序号` — 例如 `task-auth-01`

任务描述中必须包含目标文件/目录，便于锁粒度控制。

### 依赖策略

- 任务依赖通过 Claude Tasks 内建依赖关系管理
- Worker 只领取"无依赖/依赖已完成"的任务
- 若依赖未完成，任务保持 WAIT 状态

### 冲突处理规则

- 若同一 lock_key 被占用，claim 必须失败并提示锁持有者
- 禁止强制抢锁（无 --force）
- Worker 遇到冲突必须等待或改领其他任务

### 依赖失败回退策略

- 若依赖任务失败，则下游任务标记为 WAIT 或 SKIP
- 由主脑决定是否重开依赖任务或改写任务范围

### 自动重试策略

- 失败任务可手动重新入队或重开（不自动重试）
- **本版本不做自动重试执行**，只提供流程说明

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TASK-01 | Phase 24 | Complete |
| TASK-02 | Phase 24 | Complete |
| TASK-03 | Phase 24 | Complete |
| TASK-04 | Phase 24 | Complete |
| TASK-05 | Phase 24 | Complete |
| TASK-06 | Phase 24 | Complete |
| TASK-07 | Phase 24 | Complete |
| TASK-08 | Phase 24 | Complete |
| TASK-09 | Phase 24 | Complete |
| TASK-10 | Phase 24 | Complete |
| TASK-11 | Phase 24 | Complete |
| TASK-12 | Phase 24 | Complete |
| TASK-13 | Phase 24 | Complete |
| TASK-14 | Phase 24 | Complete |
| TASK-15 | Phase 24 | Complete |
| TASK-16 | Phase 24 | Complete |

**Coverage:**
- v1.85 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-03*
*Last updated: 2026-02-03 after v1.85 milestone start*
