# Roadmap: AI Swarm

**Defined:** 2026-01-31
**Core Value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈

## Milestones

- **v1.5** — 状态广播闭环 + 自动救援 + 维护性改进 (Phases 15-17) ← Current
- **Next:** 待规划

## v1.5 Phases

**Goal:** Worker 在关键节点自动写 status.log，Master 自动救援卡点，提升协作效率

**约束：**
- 优先脚本化实现，不改 `swarm/*.py`
- 仅围绕"状态广播 + 自动救援 + 维护性"展开
- 不做冲突锁绑定（留给 v1.6）

### Phase 15: _common.sh

**Goal:** Create unified configuration script with shared variables and output formatting

**Dependencies:** None (foundational phase)

**Requirements:** DOCS-01

**Success Criteria:**

1. `scripts/_common.sh` exists and is executable
2. All other scripts source `scripts/_common.sh` at startup
3. `SWARM_STATE_DIR` is exported and used by all scripts that need it
4. `SESSION_NAME` is exported and used by all scripts that need it
5. Output format is consistent across all scripts (timestamp, level prefixes)

---

### Phase 16: Auto-Rescue

**Goal:** Implement automatic confirmation for [y/n] and Press Enter patterns

**Dependencies:** Phase 15 (_common.sh for shared config)

**Requirements:** RESC-01, RESC-02, RESC-03, RESC-04

**Success Criteria:**

1. Script detects `[y/n]` prompt patterns and auto-sends Enter
2. Script detects "Press Enter", "press return", "hit enter" patterns
3. Script detects confirmation words: confirm, continue, proceed, yes
4. 30-second cooldown prevents duplicate confirmations per window
5. Dangerous commands (rm -rf, DROP, DELETE) trigger alert instead of auto-confirm

---

### Phase 17: Status Broadcast

**Goal:** Worker automatically writes status entries at key lifecycle points

**Dependencies:** Phase 15 (_common.sh for shared config)

**Requirements:** AUTO-01, AUTO-02, AUTO-03, DOCS-02

**Success Criteria:**

1. Worker records START when receiving a new task
2. Worker records DONE when task completes successfully
3. Worker records ERROR when task fails or encounters error
4. Worker records WAIT when waiting for external input
5. All status records use JSON Lines format with task_id, status, worker, timestamp
6. CONTRIBUTING.md documents script conventions and testing requirements

---

## Previous Milestones (Archived)

<details>
<summary>v1.4 共享状态与任务锁 (3 phases, 3 plans) — SHIPPED 2026-02-02</summary>

**Goal:** 实现外部脚本可读写共享状态文件与任务锁

**约束：**
- 优先脚本化实现，尽量不改 swarm/*.py
- 仅围绕"共享状态 + 任务锁"展开
- 不做自动救援、UI/面板、P2P/流水线

**Phase 12:** 状态记录脚本 ✓ COMPLETE

**Phase 13:** 任务锁脚本 ✓ COMPLETE

**Phase 14:** 集成验证 ✓ COMPLETE

**Archive:** `.planning/milestones/v1.4-ROADMAP.md`
**Requirements:** `.planning/milestones/v1.4-REQUIREMENTS.md`

</details>

<details>
<summary>v1.3 Claude Code 通信协议 (1 phase, 1 plan) — SHIPPED 2026-02-02</summary>

- [x] Phase 11: 通信脚本实现 (1/1 plan) — 2026-02-02

**Archive:** `.planning/milestones/v1.3-通信协议.md`

</details>

<details>
<summary>v1.2 Claude Code CLI 多窗口 (1 phase, 1 plan) — SHIPPED 2026-02-01</summary>

- [x] Phase 10: 4 窗口 Claude CLI 启动 (1/1 plan) — 2026-02-01

**Archive:** `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>v1.1 UAT & CLI 增强 (2 phases, 2 plans) — SHIPPED 2026-02-01</summary>

- [x] Phase 9: CLI 状态增强 (1/1 plan) — 2026-02-01
- [x] Phase 10: 验收测试 (1/1 plan) — 2026-02-01

</details>

<details>
<summary>v1.0 MVP (Phases 1-6) — SHIPPED 2026-01-31</summary>

- [x] Phase 1: 项目初始化 (1/1 plan) — 2026-01-31
- [x] Phase 2: tmux 集成层 (1/1 plan) — 2026-01-31
- [x] Phase 3: 共享状态系统 (1/1 plan) — 2026-01-31
- [x] Phase 4: Master 实现 (3/3 plans) — 2026-01-31
- [x] Phase 5: CLI 与启动脚本 (3/3 plans) — 2026-01-31
- [x] Phase 6: 集成测试 (5/5 plans) — 2026-01-31

**Archive:** `.planning/milestones/v1.0-ROADMAP.md`
**Requirements:** `.planning/milestones/v1.0-REQUIREMENTS.md`

</details>

---

*Roadmap updated: 2026-02-02*
*For full milestone details, see `.planning/milestones/`*
