# Project Milestones: AI Swarm

## v1.86 主控自动救援闭环 + 状态汇总表 (Shipped: 2026-02-04)

**Delivered:** Master 自动救援系统，支持 WAIT/confirm/press-enter 状态自动检测和安全确认；窗口状态汇总表输出，优先级排序。

**Phases completed:** 24-26 (5 plans total)

**Key accomplishments:**

1. **AutoRescuer 核心** — Created `swarm/auto_rescuer.py` (644 lines) with:
   - AUTO_ENTER_PATTERNS: 自动 Enter 模式
   - MANUAL_CONFIRM_PATTERNS: 手动确认模式
   - DANGEROUS_PATTERNS: 危险操作黑名单
   - 30s 冷却机制防止重复确认
   - 环境变量: `AI_SWARM_AUTO_RESCUE_COOLING`, `AI_SWARM_AUTO_RESCUE_DRY_RUN`

2. **状态汇总表** — Implemented `_format_summary_table()` in `swarm/master.py`:
   - 格式: `window | state | task_id | note`
   - 状态优先级: ERROR > WAIT > RUNNING > DONE/IDLE
   - 每 30 秒周期性输出

3. **Bug 修复** — During execution, fixed 4 critical issues:
   - Priority-based state merging (Issue 1)
   - IDLE reset for 'none' action (Issue 3)
   - broadcast_wait for internal events (Issue 2)
   - Expanded DANGEROUS_PATTERNS (Issue 4)

4. **集成验证** — Phase 25 & 26 verified:
   - PaneScanner/WaitDetector 复用
   - status_broadcaster.py 统一日志
   - Clean function encapsulation
   - Environment variable configuration

**Stats:**

- 2 files created/modified: swarm/auto_rescuer.py (644 lines), swarm/master.py (365 lines)
- 3 phases, 5 plans, 18 commits
- 1 day from start to ship (2026-02-04)
- 13/13 v1.86 requirements complete

**Git range:** `docs(24): create phase plan - Master 自动救援核心 + 状态汇总表` → `docs(26): complete Phase 26 integration & configuration validation`

**What's next:**
- v1.87: 待规划

---

## v1.8 诊断快照 (Shipped: 2026-02-03)

**Delivered:** 一键采集 tmux swarm 运行状态的诊断快照脚本，支持 `--session`/`--lines`/`--out` 参数，只读操作不修改状态文件。

**Phases completed:** 23 (1 plan total)

**Key accomplishments:**

1. 诊断快照脚本 — Created `scripts/swarm_snapshot.sh` (353 lines) with:
   - `--session` / `--lines` / `--out` 参数支持
   - tmux 结构信息捕获（sessions/windows/panes）
   - 窗格输出捕获带 `[session:window.pane]` 前缀
   - 状态文件和锁目录只读复制/列表
   - Git 版本信息捕获
   - 自动时间戳目录冲突解决
   - 只读约束验证（不写入 SWARM_STATE_DIR）

2. 文档完善 — README.md 和 docs/SCRIPTS.md 新增完整文档：
   - 诊断快照使用说明
   - 参数表格和示例
   - 输出目录结构说明

3. Bug 修复 — 验收发现并修复：
   - Session 不存在时退出码从 0 改为 1
   - 可选文件缺失不再计入 errors
   - Summary 显示 "(missing)" 标注

**Stats:**

- 1 script created: swarm_snapshot.sh (353 lines)
- 2 documentation files updated
- 1 phase, 1 plan, 15 commits
- 2 days from start to ship (2026-02-01 → 2026-02-03)
- 11/11 v1.8 requirements satisfied
- 6/6 success criteria verified

**Git range:** `docs(23): capture phase context` → `docs(23): update verification with fix details`

**What's next:**
- v1.9: 待规划

---

## v1.7 5 窗格布局 + Codex (Shipped: 2026-02-03)

**Delivered:** 5-pane tmux layout script with dedicated codex pane, configurable split ratios, and comprehensive documentation.

**Phases completed:** 22 (1 plan total)

**Key accomplishments:**

1. 5 窗格布局脚本 — Created `scripts/swarm_layout_5.sh` with:
   - Single tmux window: master + codex (left) + 3 workers (right)
   - Configurable left-ratio (50-80%) for master/codex split
   - Parameters: --session, --workdir, --left-ratio, --codex-cmd, --attach
   - Environment variables: CLAUDE_SESSION, SWARM_WORKDIR, CODEX_CMD

2. 代码集成 — Inherited `_config.sh`/`_common.sh` configuration system
   - Consistent with other swarm scripts in scripts/ directory
   - Uses tmux display-message for dynamic pane sizing

3. Bug 修复 — Fixed during verification:
   - split-window -l direction semantics (tmux creates pane below)
   - pane sizing from -p to -l for tmux 3.4 compatibility

4. 文档完善 — README.md and docs/SCRIPTS.md updated with:
   - Layout diagram and usage examples
   - Complete parameter documentation
   - Customization guide

**Stats:**

- 1 script created: swarm_layout_5.sh (246 lines)
- 2 documentation files updated: +164 lines
- 1 phase, 1 plan, 10 commits
- 3 days from start to ship (2026-01-31 → 2026-02-03)
- 9/9 v1.7 verification criteria passed

**Git range:** `feat(22-01): create 5-pane tmux layout script` → `docs(22-01): final verification after -l fix`

**What's next:**
- v1.8: UI 面板, P2P/流水线模式 (待规划)

---

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
