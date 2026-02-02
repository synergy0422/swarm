# Phase 15-01 Summary: _common.sh

**Plan:** 15-01
**Goal:** Create scripts/_common.sh with source guard, unified logging functions, and environment variable compatibility

## Tasks Completed

| # | Task | Status | Commit |
|---|------|--------|--------|
| 1 | Create scripts/_common.sh | ✓ | a42092a |
| 2 | Update claude_comm.sh | ✓ | 60e5c50 |
| 3 | Update claude_poll.sh | ✓ | 6517760 |
| 4 | Update claude_status.sh | ✓ | 5232723 |
| 5 | Update swarm_status_log.sh | ✓ | 8d4b407 |
| 6 | Update swarm_lock.sh | ✓ | 9a4f0c6 |
| 7 | Update swarm_e2e_test.sh | ✓ | 3dd15e2 |

## Files Modified

- `scripts/_common.sh` (new)
- `scripts/claude_comm.sh`
- `scripts/claude_poll.sh`
- `scripts/claude_status.sh`
- `scripts/swarm_status_log.sh`
- `scripts/swarm_lock.sh`
- `scripts/swarm_e2e_test.sh`

## What Was Created

### scripts/_common.sh

A shared library for all swarm scripts providing:

1. **Source Guard** - Prevents direct execution, only allows sourcing
2. **Environment Variables** with fallbacks:
   - `SWARM_STATE_DIR` (default: `/tmp/ai_swarm`)
   - `SESSION_NAME` (from `CLAUDE_SESSION` env var or default `swarm-claude-default`)
3. **Unified Logging Functions**:
   - `log_info()` - Timestamped INFO messages to stderr
   - `log_warn()` - Timestamped WARN messages to stderr
   - `log_error()` - Timestamped ERROR messages to stderr

## Key Design Decisions

1. **No `set -euo pipefail` in _common.sh** - This file is sourced, not executed. Each calling script sets its own error handling.

2. **Backward Compatibility** - `CLAUDE_SESSION` environment variable from v1.3 still works. Scripts set `SESSION="${SESSION_NAME}"` for callers expecting the old variable.

3. **Data Output vs Logging** - Status messages use `log_*` (stderr), actual data output (poll results, status content, query results) uses raw `echo` (stdout).

4. **E2E Test Isolation** - `swarm_e2e_test.sh` keeps its local `STATE_DIR` for test isolation, which takes precedence over `SWARM_STATE_DIR` from _common.sh.

## Verification Results

All tests passed:

- Source guard test: ✓ (exit code 1 when executed directly)
- claude_comm.sh: ✓ (help works)
- claude_poll.sh: ✓ (help works)
- claude_status.sh: ✓ (help works)
- swarm_status_log.sh: ✓ (help works)
- swarm_lock.sh: ✓ (help works)
- swarm_e2e_test.sh: ✓ (help works, E2E tests 8/8 pass)
- SESSION_NAME export: ✓ (default: `swarm-claude-default`)
- SWARM_STATE_DIR export: ✓ (default: `/tmp/ai_swarm`)
- CLAUDE_SESSION backward compat: ✓

## Deviations from Plan

None - plan executed exactly as written.

## Commits

```
a42092a feat(15-01): create scripts/_common.sh with source guard and logging
60e5c50 feat(15-01): update claude_comm.sh to source _common.sh
6517760 feat(15-01): update claude_poll.sh to source _common.sh
5232723 feat(15-01): update claude_status.sh to source _common.sh
8d4b407 feat(15-01): update swarm_status_log.sh to source _common.sh
9a4f0c6 feat(15-01): update swarm_lock.sh to source _common.sh
3dd15e2 feat(15-01): update swarm_e2e_test.sh to source _common.sh
```

## Duration

~1 second (verification)

## Related Decisions

- Phase 15: _common.sh before other phases - Foundational configuration needed by all scripts
