# Project Milestones: AI Swarm

## v1.0 MVP (Shipped: 2026-01-31)

**Delivered:** Multi-agent collaboration system with tmux integration, shared state management, Master coordination, and CLI tools.

**Phases completed:** 1-6 (14 plans total)

**Key accomplishments:**

1. 项目初始化 — Created swarm package with config.py, task_queue.py, worker_smart.py; paths configured to /tmp/ai_swarm/
2. tmux 集成层 — Implemented TmuxSwarmManager with resource discovery, capture, and control
3. 共享状态系统 — Implemented status broadcasting protocol and atomic task lock mechanism
4. Master 实现 — MasterScanner, AutoRescuer (conservative auto-confirm), MasterDispatcher (FIFO dispatch)
5. CLI 与启动脚本 — Unified swarm CLI with init/up/master/worker/status/down commands
6. 集成测试 — 207 tests passing, E2E tests verify tmux lifecycle, pattern detection tests

**Stats:**

- 14 source files created/modified
- 4,315 lines of Python
- 6 phases, 14 plans, 67 commits
- 1 day from start to ship (2026-01-31)
- 207 tests passing

**Git range:** `feat(01-PLAN)` → `feat(06-05)`

**What's next:**
- v1.1: Pipeline 模式, P2P 对等模式, Web 状态面板

---

## v1.1 UAT & CLI Enhancement (Shipped: 2026-02-01)

**Delivered:** CLI status enhancement with `--panes` flag, completed UAT verification, and documented LLM_BASE_URL requirement.

**Phases completed:** 9-10 (2 plans total)

**Key accomplishments:**

1. CLI 状态增强 — Implemented `swarm status --panes` flag showing tmux window snapshots with status icons ([ERROR]/[DONE]/[ ])
2. UAT 执行 — Executed 8-step manual acceptance test, discovered worker window lifecycle behavior
3. 根因定位 — Root cause: Workers exit without LLM_BASE_URL → tmux closes window (expected behavior)
4. 文档完善 — Updated README.md and run_swarm.sh with local proxy configuration example

**Stats:**

- 1 source file modified (swarm/cli.py)
- 2 phases, 2 plans, ~10 commits
- 1 day from start to ship (2026-02-01)
- 8/8 UAT tests passing

**Git range:** `feat(09-01)` → `docs(10-01)`

**What's next:**
- v1.2: 4 Claude Code CLI 窗口

---

## v1.2 Claude Code CLI 多窗口 (Shipped: 2026-02-01)

**Delivered:** 4 tmux windows with Claude CLI running (master + worker-0/1/2), one executable script.

**Phases completed:** 10 (1 plan total)

**Key accomplishments:**

1. 4 窗口启动脚本 — Created `run_claude_swarm.sh` with:
   - Session: `swarm-claude-default`
   - 4 windows: master, worker-0, worker-1, worker-2
   - Each window runs `cd $WORKDIR && claude`
   - `--attach`/`--no-attach` flags (default attach)
   - `--workdir`/`-d` flag for directory override
   - Claude CLI availability check

2. Human verification checkpoint passed — Confirmed 4 Claude CLI windows visible in tmux

**Stats:**

- 1 file created: run_claude_swarm.sh (132 lines)
- 1 phase, 1 plan, 5 commits
- 1 day from start to ship (2026-02-01)
- 8/8 v1.2 requirements complete

**Git range:** `docs(v1.2): start milestone` → `docs(v1.2): scope correction`

**What's next:**
- v1.3: 通信协议 (Master ↔ Worker 消息传递)

---

## v1.3 Claude Code 通信协议 (Shipped: 2026-02-02)

**Delivered:** External scripts that control Claude CLI via tmux send-keys/capture-pane, with [TASK]/[ACK]/[DONE] protocol markers.

**Phases completed:** 11 (1 plan total)

**Key accomplishments:**

1. 通信脚本套件 — Created 3 executable bash scripts:
   - `claude_comm.sh`: send / send-raw / poll / status commands
   - `claude_poll.sh`: continuous monitoring of worker-0/1/2
   - `claude_status.sh`: quick status check for all 4 windows

2. 协议实现 — Implemented marker-based communication:
   - `[TASK]` for task delivery
   - `[ACK]` for task acknowledgment
   - `[DONE]` for completion
   - `[ERROR]`, `[WAIT]`, `[HELP]` for status reporting

3. Bug 修复 — During execution, fixed critical issues:
   - Multi-line send → single-line (prevents Claude misinterpretation)
   - Added `send-raw` for protocol setup messages
   - Line-start marker matching with `tail -1` for latest status

4. 用户验收 — Manual verification passed:
   - send → ACK: ✓ (poll returns `[ACK] task-001`)
   - ACK → DONE: ✓ (poll returns `[DONE] task-001`)
   - No swarm/*.py files modified

**Stats:**

- 3 shell scripts created: 317 lines total
- 1 phase, 1 plan, ~10 commits
- 1 day from start to ship (2026-02-02)
- 11/14 v1.3 requirements complete (2 deferred: error/concurrency tests)

**Git range:** `feat(11-01): create claude_comm.sh` → `docs(phase-11): complete v1.3`

**What's next:**
- v1.4: Pipeline 模式, P2P 对等模式, 错误场景处理

---

## v1.6 长期可维护性 + 流程闭环 (Shipped: 2026-02-03)

**Delivered:** Unified configuration entry point, task lifecycle management, system self-check script, and comprehensive maintenance documentation.

**Phases completed:** 18-21 (4 plans total)

**Key accomplishments:**

1. 统一配置入口 — Created `_config.sh` with 4 config vars, `_common.sh` sources it with graceful degradation
2. 任务流程闭环 — Created `swarm_task_wrap.sh` (289 lines) with atomic lock + status lifecycle
3. 一键自检 — Created `swarm_selfcheck.sh` (280 lines) checking tmux/scripts/config/state_dir
4. 维护文档 — Created MAINTENANCE.md (314 lines), SCRIPTS.md (587 lines), CHANGELOG.md (136 lines), updated README.md

**Stats:**

- 4 shell scripts created: 651 lines total
- 4 documentation files created/modified: 1,201 lines total
- 4 phases, 4 plans, ~25 commits
- 1 day from start to ship (2026-02-03)
- 9/9 v1.6 requirements complete

**Git range:** `feat(18-01): create _config.sh` → `docs(21): complete maintenance documentation phase`

**What's next:**
- v1.7: UI 面板, P2P/流水线模式

---

*Milestone completed: 2026-02-03*
