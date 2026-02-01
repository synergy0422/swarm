# State: AI Swarm

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-01)

**Core value:** 多 Agent 并行推进，Master 协调去重，减少人作为瓶颈
**Current focus:** Phase 10 - v1.2 Claude Code CLI 多窗口

## Phase Status

| # | Phase | Status | Progress |
|---|-------|--------|----------|
| 1 | 项目初始化 | Complete | 100% (1/1 plans) |
| 2 | tmux 集成层 | Complete | 100% (1/1 plans) |
| 3 | 共享状态系统 | Complete | 100% (1/1 plans) |
| 4 | Master 实现 | Complete | 100% (3/3 plans) |
| 5 | CLI 与启动脚本 | Complete | 100% (3/3 plans) |
| 6 | 集成测试 | Complete | 100% (5/5 plans) |
| 7 | 协作命令封装 | Complete | 100% (1/1 plans) |
| 8 | Master tmux 扫描 | Complete | 100% (1/1 plans) |
| 9 | CLI 状态增强 | Complete | 100% (1/1 plans) |
| 10 | v1.2 Claude Code CLI | Complete | 100% (1/1 plans) |

## Current Position

**Phase 10: v1.2 Claude Code CLI 多窗口**

Status: Complete
Last activity: 2026-02-01 — Phase 10 completed, run_claude_swarm.sh created

## Key Decisions

| Phase | Decision | Rationale | Outcome |
|-------|----------|-----------|---------|
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

## Session Continuity

Last session: 2026-02-01T08:30:00Z
Resumed: 2026-02-01 — Started v1.2 milestone
Next action: Define requirements and create roadmap

---
*State updated: 2026-02-01*
