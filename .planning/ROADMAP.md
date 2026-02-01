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

**Goal:** 实现 Master 通过 tmux send-keys/capture-pane 向 Claude CLI 窗口发送任务，Worker 返回状态词

**Phase 11:** 通信协议实现

**Requirements:** COMM-01 ~ COMM-15

**Success Criteria:**
1. TmuxSwarmManager 新增 `send_command()` 和 `capture_output()` 方法
2. 定义 `[TASK]`, `[DONE]`, `[ERROR]`, `[WAIT]`, `[ACK]` 五个核心标记词
3. Master 可向指定 worker 发送任务（send_keys + 标记行）
4. Worker 返回 `[ACK]` 确认收到任务
5. Master 可从 worker pane 解析状态词（DONE/ERROR/WAIT/HELP）
6. 实现轮询策略定期扫描各 worker 状态
7. 通信协议测试通过

**Plan:**
- [x] 11-01-PLAN.md — 通信协议实现（待创建）

</details>

## v1.2 Phases (Archived)

<details>
<summary>✅ v1.2 Claude Code CLI 多窗口 (1 phase, 1 plan) — SHIPPED 2026-02-01</summary>

- [x] Phase 10: 4 窗口 Claude CLI 启动 (1/1 plan) — 2026-02-01

Plans:
- [x] 10-01-PLAN.md — 创建 4 窗口启动脚本，验证 tmux 中可见 Claude CLI

</details>

## v1.3 Phases (待规划)

<details>
<summary>⏳ v1.3 通信协议 (待规划)</summary>

**范围:** Master ↔ Worker 消息传递协议
- COMM-01: 消息格式定义
- COMM-02: Master → Worker 指令发送
- COMM-03: Worker → Master 状态回报
- COMM-04: 状态标识
- TEST-03: 通信协议测试

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
