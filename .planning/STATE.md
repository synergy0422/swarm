# State: AI Swarm

## Project Reference

See: .planning/PROJECT.md

**Core value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈
**Current focus:** Phase 4 - Master 实现

## Phase Status

| # | Phase | Status | Progress |
|---|-------|--------|----------|
| 1 | 项目初始化 | Complete | 100% (1/1 plans) |
| 2 | tmux 集成层 | Complete | 100% (1/1 plans) |
| 3 | 共享状态系统 | Complete | 100% (1/1 plans) |
| 4 | Master 实现 | In Progress | 67% (2/3 plans) |
| 5 | CLI 与启动脚本 | Pending | 0% |
| 6 | 集成测试 | Pending | 0% |

## Current Position

**Phase 4: Master 实现** - Plan 02 COMPLETE ✓

Completed:
- `swarm/master_scanner.py` with MasterScanner class (269 lines)
- `swarm/auto_rescuer.py` with WaitPatternDetector and AutoRescuer classes (397 lines)
- PatternCategory enum (INTERACTIVE_CONFIRM, PRESS_ENTER, CONFIRM_PROMPT, NONE)
- WaitPattern dataclass with should_auto_confirm flag
- Conservative auto-confirm policy (disabled by default, Press ENTER only)
- Blacklist keyword filtering (delete, rm -rf, sudo, password, key, 删除, etc.)
- Detection limited to last 20 lines and 30 second window
- Case-insensitive regex-based pattern matching
- 40 tests for master scanner and auto rescuer
- 138 tests pass total (no regressions)

## Recent Changes

- 2026-01-31: Phase 4 Plan 02 complete - Auto Rescuer
- 2026-01-31: Phase 4 Plan 01 complete - Master Scanner
- 6 commits for Phase 4 execution
- AutoRescuer with conservative WAIT detection and auto-confirm
- All must-haves verified

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

## Session Continuity

Last session: 2026-01-31T04:45:35Z
Stopped at: Completed Phase 4 Plan 02 - Auto Rescuer
Resume file: None

---
*State updated: 2026-01-31*
