# Roadmap: AI Swarm v1.85

**Defined:** 2026-02-03
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## Milestone v1.85: Claude Tasks 集成 + 自动锁闭环

**Goal:** 通过 `swarm_tasks_bridge.sh` 实现 claim→lock→work→done/fail 自动闭环，配合 CLAUDE_CODE_TASK_LIST_ID 实现多窗口任务共享。

---

## Phase 24: swarm_tasks_bridge.sh 实现

**Goal:** 创建 `swarm_tasks_bridge.sh` 脚本，实现 claim/done/fail 子命令的自动锁闭环，更新文档。

**Requirements:**
- TASK-01: 脚本基础框架
- TASK-02: claim 子命令
- TASK-03: 默认 lock_key
- TASK-04: acquire 调用
- TASK-05: START 状态记录
- TASK-06: done 子命令
- TASK-07: release 调用
- TASK-08: DONE 状态记录
- TASK-09: fail 子命令
- TASK-10: fail release 调用
- TASK-11: ERROR 状态记录
- TASK-12: acquire 错误处理
- TASK-13: release 错误处理
- TASK-14: 错误不吞掉
- TASK-15: README.md 协作流程章节
- TASK-16: SCRIPTS.md 脚本文档

**Success Criteria:**

1. **脚本功能完整**
   - `claim` 子命令成功执行：自动加锁 + START 日志
   - `done` 子命令成功执行：自动解锁 + DONE 日志
   - `fail` 子命令成功执行：自动解锁 + ERROR 日志

2. **错误处理正确**
   - lock 被占用时 claim 失败，提示锁持有者
   - release 失败时脚本退出码为 1
   - 所有错误消息打印到 stderr

3. **文档完整**
   - README.md 包含"Claude Tasks 协作流程"章节
   - docs/SCRIPTS.md 包含完整脚本文档

4. **验收测试通过**
   - claim + done 流程无人工调用 swarm_lock.sh
   - claim + fail 流程无人工调用 swarm_lock.sh
   - 状态日志包含 START/DONE/ERROR 记录

**Plans:**
- [x] 24-01-PLAN.md — Create swarm_tasks_bridge.sh script with claim/done/fail commands
- [x] 24-02-PLAN.md — Update README.md and SCRIPTS.md documentation

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TASK-01 | Phase 24 | Pending |
| TASK-02 | Phase 24 | Pending |
| TASK-03 | Phase 24 | Pending |
| TASK-04 | Phase 24 | Pending |
| TASK-05 | Phase 24 | Pending |
| TASK-06 | Phase 24 | Pending |
| TASK-07 | Phase 24 | Pending |
| TASK-08 | Phase 24 | Pending |
| TASK-09 | Phase 24 | Pending |
| TASK-10 | Phase 24 | Pending |
| TASK-11 | Phase 24 | Pending |
| TASK-12 | Phase 24 | Pending |
| TASK-13 | Phase 24 | Pending |
| TASK-14 | Phase 24 | Pending |
| TASK-15 | Phase 24 | Pending |
| TASK-16 | Phase 24 | Pending |

**Coverage:**
- v1.85 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---

*Roadmap defined: 2026-02-03*
*Last updated: 2026-02-03 after v1.85 milestone start*
