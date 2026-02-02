---
phase: 19-任务流程闭环
plan: 19-01
subsystem: scripts
tags: [bash, task-lifecycle, lock-management, status-broadcasting]
completed: 2026-02-02
---

# Phase 19 Plan 01: Task Flow Wrapper Summary

## Objective

Create `scripts/swarm_task_wrap.sh` that wraps task execution with complete lock and state lifecycle management.

## One-Liner

Task lifecycle wrapper with atomic lock acquisition, status broadcasting (START → DONE/ERROR), and proper cleanup - integrates with swarm_lock.sh and swarm_status_log.sh.

## Key Files Created

| File | Purpose |
|------|---------|
| `scripts/swarm_task_wrap.sh` | Task lifecycle wrapper with lock/state integration |

## Key Links

| From | To | Via |
|------|----|-----|
| `scripts/swarm_task_wrap.sh` | `scripts/swarm_lock.sh` | acquire/release commands for task locking |
| `scripts/swarm_task_wrap.sh` | `scripts/swarm_status_log.sh` | append command for status updates |
| `scripts/swarm_task_wrap.sh` | `scripts/_common.sh` | source statement for config and logging |

## Commands Implemented

| Command | Description | Lock Operation |
|---------|-------------|----------------|
| `run <task_id> <worker> <cmd> [args...]` | Full lifecycle: acquire → START → execute → DONE/ERROR → release | Acquire then release |
| `acquire-only <task_id> [worker]` | Acquire lock and write START status | Acquire only |
| `release-only <task_id> [worker]` | Release lock and write DONE status | Release only |
| `skip <task_id> [worker] <reason>` | Write SKIP status | None |
| `wait <task_id> [worker] <reason>` | Write WAIT status | None |

## Global Options

| Option | Description |
|--------|-------------|
| `--ttl SECONDS` | Lock TTL in seconds (default: no expiry) |
| `--no-status` | Skip status logging (for testing) |

## Lifecycle Flow

```
run command:
  1. Acquire lock via swarm_lock.sh acquire
  2. Write START status via swarm_status_log.sh append
  3. Execute command (NO eval - uses "$@")
  4. On success: write DONE status, release lock, exit 0
  5. On failure: write ERROR status, release lock, exit code
```

## Implementation Details

- **No eval**: Command executed via `"$@"` for proper argument handling
- **Global state**: `LOCK_ACQUIRED`, `LOCK_TASK_ID`, `LOCK_WORKER` for lifecycle tracking
- **Worker detection**: Supports explicit worker argument or auto-detection via WORKER env var
- **Owner validation**: Uses swarm_lock.sh's strict owner validation on release
- **skip/wait**: Only write status, no lock operations (as specified in plan)

## Test Results

| Test | Result |
|------|--------|
| Help command | PASS |
| Acquire-only | PASS |
| Release-only | PASS |
| START logged | PASS |
| DONE logged | PASS |
| SKIP (no lock) | PASS |
| WAIT (no lock) | PASS |
| Run success | PASS |
| Run failure | PASS |
| ERROR logged | PASS |
| Lock released | PASS |
| Wrong worker cannot release | PASS |
| Correct worker releases | PASS |

## Decisions Made

1. **Subshell for command execution**: Used `(subshell)` with `set +e` to capture exit code without affecting main script's error handling
2. **Manual lock release**: Released lock manually after command execution instead of using EXIT trap for clearer control flow
3. **Worker pattern detection**: skip/wait commands detect `worker-*` pattern to correctly parse arguments

## Deviations from Plan

None - plan executed as written.

## Authentication Gates

None - no external authentication required for this script.

## Tech Stack

- **Language**: Bash 4+
- **Dependencies**: swarm_lock.sh, swarm_status_log.sh, _common.sh
- **Lock Format**: JSON (via swarm_lock.sh Python helper)

## Metrics

| Metric | Value |
|--------|-------|
| Duration | ~33 minutes |
| Lines | 289 |
| Tests | 15/15 passing |
