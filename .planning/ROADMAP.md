# Roadmap: AI Swarm

**Defined:** 2026-01-31
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## Milestones

- ✅ **v1.0 MVP** — Phases 1-6 (14 plans), shipped 2026-01-31
- ✅ **v1.1** — UAT & CLI 增强, shipped 2026-02-01
- ✅ **v1.2** — Claude Code CLI 多窗口, shipped 2026-02-01
- ⏳ **v1.3** — Claude Code 通信协议 (1 phase, 1 plan)

## v1.3 Phases

<details>
<summary>⏳ v1.3 Claude Code 通信协议 (1 phase, 1 plan)</summary>

**Goal:** 实现外部脚本通过 tmux send-keys/capture-pane 与 Claude CLI 窗口通信

**约束：**
- 仅用 tmux send-keys / capture-pane
- 不修改 swarm/master.py, swarm/tmux_manager.py
- 新增外部脚本，不改 core 代码

**Phase 11:** 通信脚本实现

**Requirements:** SCRIPT-01~03, COMM-01~03, SEND-01~02, POLL-01~03

**Success Criteria:**
1. `claude_comm.sh send <window> <task_id> "<desc>"` 可发送任务
2. `claude_comm.sh poll <window>` 可解析 `[ACK]/[DONE]/[ERROR]`
3. `claude_poll.sh` 可定期轮询各窗口状态
4. 手动验收：发送任务 → 收到 ACK → 收到 DONE/ERROR
5. 不修改任何 swarm/*.py 文件

**Plan:**
- [x] 11-01-PLAN.md — 通信脚本实现 (4 tasks, Wave 1, 1 checkpoint)

</details>

## v1.2 Phases (Archived)

<details>
<summary>✅ v1.2 Claude Code CLI 多窗口 (1 phase, 1 plan) — SHIPPED 2026-02-01</summary>

- [x] Phase 10: 4 窗口 Claude CLI 启动 (1/1 plan) — 2026-02-01

Plans:
- [x] 10-01-PLAN.md — 创建 4 窗口启动脚本，验证 tmux 中可见 Claude CLI

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

*Roadmap updated: 2026-02-01*
*For full v1.1 details, see `.planning/milestones/v1.1-ROADMAP.md`*
