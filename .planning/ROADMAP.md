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

**用户注意点：**
1. **_common.sh 改动范围**：v1.3/v1.4 脚本（claude_comm.sh, claude_poll.sh, claude_status.sh, swarm_status_log.sh, swarm_lock.sh, swarm_e2e_test.sh）全部需要 source _common.sh
2. **Auto-Rescue 危险命令黑名单**：优先检测 + 仅对 Worker 窗口（worker-0/1/2）生效
3. **Status Broadcast 自动写入范围**：只在脚本任务流中触发，避免与手工 append 冲突

### Phase 15: _common.sh

**Goal:** Create unified configuration script with shared variables and output formatting

**Dependencies:** None (foundational phase)

**Requirements:** DOCS-01

**Design Specs:**

1. **Source Guard** (prevent direct execution):
   ```bash
   # In _common.sh
   [[ "${BASH_SOURCE[0]}" != "${0}" ]] || exit 1
   ```
   ```bash
   # In each script
   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   source "$SCRIPT_DIR/_common.sh"
   ```

2. **Unified Logging Functions**:
   ```bash
   log_info() { echo "[$(date +%H:%M:%S)][INFO] $*" >&2; }
   log_warn() { echo "[$(date +%H:%M:%S)][WARN] $*" >&2; }
   log_error() { echo "[$(date +%H:%M:%S)][ERROR] $*" >&2; }
   ```
   - Format: `[HH:MM:SS][LEVEL] message`
   - All scripts use these functions (no raw echo for status)

3. **Environment Variable Compatibility**:
   ```bash
   SWARM_STATE_DIR="${SWARM_STATE_DIR:-/tmp/ai_swarm}"
   SESSION_NAME="${CLAUDE_SESSION:-${SESSION_NAME:-swarm-claude-default}}"
   export SWARM_STATE_DIR SESSION_NAME
   ```

**Success Criteria:**

1. `scripts/_common.sh` exists and is executable (with source guard)
2. All 6 existing scripts source `scripts/_common.sh` at startup
3. `SWARM_STATE_DIR` is exported and used by all scripts that need it
4. `SESSION_NAME` is exported (with CLAUDE_SESSION fallback for v1.3 compat)
5. Output format is consistent via log_info/log_warn/log_error functions
6. **Existing scripts modified**: claude_comm.sh, claude_poll.sh, claude_status.sh, swarm_status_log.sh, swarm_lock.sh, swarm_e2e_test.sh

---

### Phase 16: Auto-Rescue

**Goal:** Implement automatic confirmation for [y/n] and Press Enter patterns

**Dependencies:** Phase 15 (_common.sh for shared config)

**Requirements:** RESC-01, RESC-02, RESC-03, RESC-04

**Success Criteria:**

1. **Dangerous command blacklist runs first** (rm -rf, DROP, DELETE, sudo) → alert only, never auto-confirm
2. Script detects `[y/n]` prompt patterns and auto-sends Enter
3. Script detects "Press Enter", "press return", "hit enter" patterns
4. Script detects confirmation words: confirm, continue, proceed, yes
5. 30-second cooldown prevents duplicate confirmations per window
6. **Only triggers for Worker windows** (worker-0/1/2, not master)

---

### Phase 17: Status Broadcast

**Goal:** Worker automatically writes status entries at key lifecycle points

**Dependencies:** Phase 15 (_common.sh for shared config)

**Requirements:** AUTO-01, AUTO-02, AUTO-03, DOCS-02

**Success Criteria:**

1. Worker records START when receiving a new task (script-triggered only)
2. Worker records DONE when task completes successfully (script-triggered only)
3. Worker records ERROR when task fails or encounters error (script-triggered only)
4. Worker records WAIT when waiting for external input (script-triggered only)
5. All status records use JSON Lines format with task_id, status, worker, timestamp
6. CONTRIBUTING.md documents script conventions and testing requirements
7. **Auto-write only in script task flows** → no conflict with manual append

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
