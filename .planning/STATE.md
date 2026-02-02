# State: AI Swarm

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-02)

**Core value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈
**Current focus:** v1.6 - 长期可维护性 + 流程闭环 (Phase 18 in progress)

## Phase Status

| # | Phase | Status | Progress |
|---|-------|--------|----------|
| 1-6 | v1.0 MVP | Complete | 100% |
| 7-8 | v1.1 | Complete | 2/2 plans |
| 9-10 | v1.2 | Complete | 2/2 plans |
| 11 | v1.3 通信协议 | Complete | 1/1 plans |
| 12-14 | v1.4 共享状态与任务锁 | Complete | 3/3 plans |
| 15-17 | v1.5 维护性改进 | Complete | 3/3 plans |
| 18-21 | v1.6 长期可维护性 + 流程闭环 | In Progress | 1/4 plans |

## Current Position

**v1.6 In Progress** — 2026-02-02

- **Milestone:** 长期可维护性 + 流程闭环 (Phases 18-21)
- **Focus:** 统一配置入口、任务流程闭环、自检与文档、维护文档
- **Status:** Phase 18-01 complete, ready for 18-02
- **Next action:** Execute 18-02 (or plan remaining phases)

## v1.6 Summary

| Aspect | Value |
|--------|-------|
| Phases | 4 (18, 19, 20, 21) |
| Requirements | 10 (CFGN-01~02, WRAP-01~02, CHK-01, DOCS-03~06) |
| Focus | 维护性 + 流程闭环 |
| Completed | 1/4 phases (18-01) |

## Key Decisions

| Phase | Decision | Rationale | Status |
|-------|----------|-----------|--------|
| 15 | _common.sh before other phases | Foundational configuration needed by all scripts | ✅ Validated |
| 16 | Auto-Rescue after _common.sh | Uses shared config for output formatting | ✅ Validated |
| 16-01 | Removed done/ready/ok patterns | Too broad, caused false positives | ✅ Validated |
| 16-01 | Case-insensitive matching | Handles varied capitalization | ✅ Validated |
| 16-01 | Dangerous patterns checked first | Safety over convenience | ✅ Validated |
| 17 | Status Broadcast after _common.sh | Uses shared config for consistent logging | ✅ Validated |
| 01 | Path config uses AI_SWARM_DIR env var with /tmp/ai_swarm/ default | Flexible override, auto-create | ✅ Validated |
| 01 | API key only from environment variables | Security - no .env loading in code | ✅ Validated |
| 01 | Tests use pytest monkeypatch fixture for isolation | Repeatable tests, no pollution | ✅ Validated |
| 01 | Imports use "from swarm import" pattern | Package cohesion | ✅ Validated |
| 02 | libtmux for tmux automation | Full programmatic control | ✅ Validated |
| 02 | AgentStatus enum for agent state tracking | PENDING, RUNNING, STOPPED, etc. | ✅ Validated |
| 03 | JSON Lines format for status broadcasting | Simple, parseable, tool-friendly | ✅ Validated |
| 03 | O_CREAT|O_EXCL for atomic lock acquisition | Platform-independent | ✅ Validated |
| 04-01 | MasterScanner uses polling (1s default) | Simple, reliable, no external deps | ✅ Validated |
| 04-02 | Auto-confirm disabled by default - opt-in policy | Prevents unintended automated actions | ✅ Validated |
| 04-02 | Only Press ENTER patterns auto-confirm (never y/n) | Conservative safety | ✅ Validated |
| 04-02 | Blacklist keywords always block auto-action | delete, rm -rf, sudo, password | ✅ Validated |
| 04-03 | FIFO dispatch within priority groups | First-in-first-out | ✅ Validated |
| 04-03 | Lock acquisition before dispatch (atomic) | Prevents duplicate execution | ✅ Validated |
| 05-01 | Use argparse only (not typer/click) | Minimize dependencies | ✅ Validated |
| 05-01 | Direct class instantiation for master/worker | Avoids argparse conflicts | ✅ Validated |
| 05-01 | Session naming: swarm-{cluster_id} | Multi-cluster support | ✅ Validated |
| 05-02 | argparse parents pattern for --cluster-id | Flag after subcommands | ✅ Validated |
| 05-03 | Removed eager cli import from __init__.py | Prevents RuntimeWarning | ✅ Validated |
| 07-01 | Updated to libtmux 0.53.0 modern API | Server.sessions.get() instead of find_where() | ✅ Validated |
| 08-01 | Pane poll interval: 3 seconds | Independent from poll_interval, configurable via constructor | ✅ Validated |
| 08-01 | ENTER patterns: 5 total | press enter, press return, hit enter, 回车继续, 按回车 | ✅ Validated |
| 08-01 | Cooldown: 30 seconds per window | Prevents repeated ENTERs | ✅ Validated |
| 08-01 | Minimal logging for auto-ENTER | `[Master] Auto-ENTER for {window_name}` | ✅ Validated |
| 08-01 | tmux unavailable: silently skip | No errors raised | ✅ Validated |
| 09-01 | --panes flag with store_true action | Boolean flag for optional pane display | ✅ Validated |
| 09-01 | Status icon logic: Error/Failed -> [ERROR], DONE/Complete -> [DONE] | Visual status at a glance | ✅ Validated |
| 09-01 | 20-line content limit per window | Readable output, prevents terminal flood | ✅ Validated |
| 11-01 | Single-line task delivery via tmux send-keys | Prevents Claude from processing partial messages | ✅ Validated |
| 11-01 | send-raw subcommand for protocol setup | Protocol messages without [TASK] prefix | ✅ Validated |
| 12-01 | Shell script for status.log operations | append/tail/query with JSON Lines format | ✅ Validated |
| 13-01 | JSON lock format with 4 fields (task_id, worker, acquired_at, expires_at) | TTL optional - null means never expires | ✅ Validated |
| 13-01 | Python os.open(O_CREAT|O_EXCL) for atomic lock creation | Platform-independent, race-condition safe | ✅ Validated |
| 14-01 | E2E test uses mktemp -d for complete isolation | No pollution of real /tmp/ai_swarm data | ✅ Validated |
| 14-01 | Used grep -F (fixed strings) for simpler matching | More reliable than regex, no escaping needed | ✅ Validated |
| 14-01 | Replaced ((var++)) with $((var + 1)) for set -e | Prevents premature exit when value is 0 | ✅ Validated |
| 15-01 | _common.sh source guard pattern | Prevents direct execution, only sourcing | ✅ Validated |
| 15-01 | log_info/log_warn/log_error to stderr | Separates status from data output | ✅ Validated |
| 15-01 | CLAUDE_SESSION backward compatibility | Existing scripts continue to work | ✅ Validated |
| 18-01 | Centralized _config.sh entry point | Single source of truth for configuration | ✅ Validated |
| 18-01 | BASH_SOURCE[0] + cd/pwd for path resolution | Handles bash -c sourcing edge case | ✅ Validated |
| 18-01 | SWARM_NO_CONFIG=1 for graceful degradation | Testing defaults without _config.sh | ✅ Validated |
| 18-01 | log_debug conditional on LOG_LEVEL=DEBUG | Debug logging without performance impact | ✅ Validated |

## Session Continuity

Last session: 2026-02-02
Completed: Phase 18-01 (Unified Configuration Entry Point)
- scripts/_config.sh created with centralized defaults
- scripts/_common.sh updated to source _config.sh with graceful degradation
- log_debug function added for conditional debug output
- All integration tests pass (swarm_status_log.sh, swarm_lock.sh, swarm_broadcast.sh)

Current: v1.6 milestone in progress (1/4 phases complete)
Next action: Execute 18-02 or plan remaining phases (19-21)

---

*State updated: 2026-02-02 after Phase 18-01 completion*
