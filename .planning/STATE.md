# State: AI Swarm

## Project Reference

See: .planning/PROJECT.md

**Core value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈
**Current focus:** Phase 6 - 集成测试

## Phase Status

| # | Phase | Status | Progress |
|---|-------|--------|----------|
| 1 | 项目初始化 | Complete | 100% (1/1 plans) |
| 2 | tmux 集成层 | Complete | 100% (1/1 plans) |
| 3 | 共享状态系统 | Complete | 100% (1/1 plans) |
| 4 | Master 实现 | Complete | 100% (3/3 plans) |
| 5 | CLI 与启动脚本 | Complete | 100% (1/1 plans) |
| 6 | 集成测试 | Pending | 0% |

## Current Position

**Phase 5: CLI 与启动脚本** - COMPLETE ✓

Completed:
- `swarm/cli.py` with argparse-based command routing (472 lines)
- 6 CLI commands: init, up, master, worker, status, down
- Tmux session orchestration via libtmux
- `setup.py` with console_scripts entry point for global `swarm` command
- `README.md` with 5-line usage section and documentation
- Direct class instantiation for master/worker (no subprocess)
- Session naming: `swarm-{cluster_id}` for multi-cluster support
- Preflight checks for tmux/libtmux dependencies
- Helper functions: get_session(), parse_status_log()
- All commands tested and working

## Recent Changes

- 2026-01-31: Phase 5 Plan 01 complete - CLI 与启动脚本
- 2026-01-31: Phase 4 Plan 03 complete - Master Dispatcher
- 2026-01-31: Phase 4 Plan 02 complete - Auto Rescuer
- 2026-01-31: Phase 4 Plan 01 complete - Master Scanner
- 14 commits for Phase 5 execution (5 tasks)
- All Phase 5 modules exported from swarm package

## Decisions Made

| Phase | Decision | Rationale |
|-------|----------|-----------|
| 01 | Path config uses AI_SWARM_DIR env var with /tmp/ai_swarm/ default | Flexible override, auto-create with os.makedirs |
| 01 | API key only from environment variables | Security - no .env loading in code |
| 01 | Tests use pytest monkeypatch fixture for isolation | Repeatable tests, no pollution between runs |
| 01 | Imports use "from swarm import" pattern | Package cohesion |
| 02 | libtmux for tmux automation | Full programmatic control, dynamic session creation |
| 02 | AgentStatus enum for agent state tracking | PENDING, RUNNING, STOPPED, FAILED, UNKNOWN |
| 02 | Async methods for output streaming | Non-blocking real-time output capture |
| 03 | JSON Lines format for status broadcasting | Simple, parseable, tool-friendly |
| 03 | O_CREAT|O_EXCL for atomic lock acquisition | Platform-independent, no fcntl dependency |
| 03 | Heartbeat 10s, TTL 300s, lazy cleanup | Fault-tolerant lock management |
| 04-01 | MasterScanner uses polling (1s default) rather than event-driven | Simple, reliable, no external dependencies |
| 04-01 | read_worker_status returns last status per worker | Latest state is most relevant for dispatch |
| 04-01 | scan_loop uses threading.Event for graceful shutdown | Standard Python pattern |
| 04-01 | Factory function create_scanner() for consistency | Clean instantiation pattern |
| 04-02 | Auto-confirm disabled by default - opt-in policy | Prevents unintended automated actions |
| 04-02 | Only Press ENTER patterns auto-confirm (never y/n) | Conservative safety - only send Enter key |
| 04-02 | Blacklist keywords always block auto-action | delete, rm -rf, sudo, password, key, 删除, etc. |
| 04-02 | Detection limited to last 20 lines and 30 seconds | Reduces false positives from old prompts |
| 04-02 | Priority-based pattern detection | INTERACTIVE_CONFIRM > PRESS_ENTER > CONFIRM_PROMPT |
| 04-03 | FIFO dispatch within priority groups | First-in-first-out for same-priority tasks |
| 04-03 | Lock acquisition before dispatch (atomic O_CREAT|O_EXCL) | Prevents duplicate task execution |
| 04-03 | Idle worker = terminal state (DONE/SKIP/ERROR) + no lock | Ensures worker truly available |
| 04-03 | Synchronous dispatch_loop (not async) | Simpler implementation, easier testing |
| 04-03 | Factory function create_dispatcher() for consistency | Matches create_scanner() pattern |
| 05-01 | Use argparse only (not typer/click) | Minimize dependencies, use stdlib |
| 05-01 | Direct class instantiation for master/worker | Avoids argparse conflicts with subprocess calls |
| 05-01 | Session naming: swarm-{cluster_id} | Multi-cluster support |
| 05-01 | CLI flags > env vars > defaults priority | Configuration flexibility |
| 05-01 | Preflight checks before session creation | Fail fast with clear error messages |

## Session Continuity

Last session: 2026-01-31T05:24:14Z
Stopped at: Completed Phase 5 Plan 01 - CLI 与启动脚本
Resume file: None

---
*State updated: 2026-01-31*
