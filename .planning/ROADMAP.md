# Roadmap: AI Swarm

**Defined:** 2026-01-31
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## Milestones

- ✅ **v1.0 MVP** — Phases 1-6 (14 plans), shipped 2026-01-31
- ✅ **v1.1** — UAT & CLI 增强, shipped 2026-02-01
- ✅ **v1.2** — Claude Code CLI 多窗口, shipped 2026-02-01
- ✅ **v1.3** — Claude Code 通信协议, shipped 2026-02-02
- ⏳ **v1.4** — 共享状态与任务锁 (3 phases, 3 plans)

## v1.4 Phases

<details>
<summary>⏳ v1.4 共享状态与任务锁 (3 phases, 2/3 complete)</summary>

**Goal:** 实现外部脚本可读写共享状态文件与任务锁

**约束：**
- 优先脚本化实现，尽量不改 swarm/*.py
- 仅围绕"共享状态 + 任务锁"展开
- 不做自动救援、UI/面板、P2P/流水线

**Phase 12:** 状态记录脚本 ✓ COMPLETE

**Requirements:** STATUS-01, STATUS-02

**Plan:**
- [x] 12-01-PLAN.md — 创建 swarm_status_log.sh

**Success Criteria:**
1. `swarm_status_log.sh append START worker-0 task-001` 追加有效 JSON 到 status.log
2. `swarm_status_log.sh tail 10` 返回最近 10 条状态记录
3. `swarm_status_log.sh query task-001` 返回任务状态变更

**Phase 13:** 任务锁脚本 ✓ COMPLETE

**Requirements:** LOCK-01, LOCK-02, LOCK-03

**Plan:**
- [x] 13-01-PLAN.md — 创建 swarm_lock.sh

**Success Criteria:**
1. `swarm_lock.sh acquire task-001 worker-0` 返回锁内容
2. 锁存在时重复 acquire 返回失败
3. `swarm_lock.sh release task-001 worker-0` 成功删除锁
4. release 后可重新 acquire 同一任务

**Phase 14:** 集成验证

**Plan:**
- [ ] 14-01-PLAN.md — 端到端验证脚本

**Success Criteria:**
1. 端到端测试脚本通过
2. `git diff --name-only swarm/` 无新增修改

</details>

## v1.3 Phases (Archived)

<details>
<summary>✅ v1.3 Claude Code 通信协议 (1 phase, 1 plan) — SHIPPED 2026-02-02</summary>

- [x] Phase 11: 通信脚本实现 (1/1 plan) — 2026-02-02

Plans:
- [x] 11-01-PLAN.md — 通信脚本实现

</details>

## v1.2 Phases (Archived)

<details>
<summary>✅ v1.2 Claude Code CLI 多窗口 (1 phase, 1 plan) — SHIPPED 2026-02-01</summary>

- [x] Phase 10: 4 窗口 Claude CLI 启动 (1/1 plan) — 2026-02-01

Plans:
- [x] 10-01-PLAN.md — 创建 4 窗口启动脚本

</details>

## v1.1 Phases (Archived)

<details>
<summary>✅ v1.1 UAT & CLI 增强 (2 phases, 2 plans) — SHIPPED 2026-02-01</summary>

- [x] Phase 9: CLI 状态增强 (1/1 plan) — 2026-02-01
- [x] Phase 10: 验收测试 (1/1 plan) — 2026-02-01

Plans:
- [x] 09-01-PLAN.md — Add --panes parameter to swarm status command
- [x] 10-01-PLAN.md — UAT 验收测试

</details>

## v1.0 Summary

✅ **SHIPPED** — AI Swarm v1.0 MVP (Phases 1-6)

Multi-agent collaboration system with tmux integration, shared state management, Master coordination, and CLI tools. 4,315 LOC, 207 tests passing.

**Archive:** `.planning/milestones/v1.0-ROADMAP.md`
**Requirements:** `.planning/milestones/v1.0-REQUIREMENTS.md`

---

## v1.0 Phases (Archived)

<details>
<summary>✅ v1.0 MVP (Phases 1-6) — SHIPPED 2026-01-31</summary>

- [x] Phase 1: 项目初始化 (1/1 plan) — 2026-01-31
- [x] Phase 2: tmux 集成层 (1/1 plan) — 2026-01-31
- [x] Phase 3: 共享状态系统 (1/1 plan) — 2026-01-31
- [x] Phase 4: Master 实现 (3/3 plans) — 2026-01-31
- [x] Phase 5: CLI 与启动脚本 (3/3 plans) — 2026-01-31
- [x] Phase 6: 集成测试 (5/5 plans) — 2026-01-31

</details>

---

*Roadmap updated: 2026-02-02*
*For full v1.1 details, see `.planning/milestones/v1.1-ROADMAP.md`*
