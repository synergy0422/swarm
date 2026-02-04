---
phase: 27-status-summary-enhancement
plan: "01"
type: execute
subsystem: "master"
tags: ["status", "timestamp", "tracking", "ui"]
tech-stack:
  added: []
  patterns: ["state tracking", "timestamp formatting", "duration calculation"]
---

# Phase 27 Plan 01: Status Summary Enhancement Summary

Enhanced the status summary table with three new fields for improved situational awareness.

## One-Liner

Added `last_update_ts`, `wait_since_ts`, and `error_streak` fields to PaneSummary with enhanced table formatting showing wait durations and error streaks.

## Changes Made

### Fields Added to PaneSummary

| Field | Type | Purpose |
|-------|------|---------|
| `last_update_ts` | float | Unix timestamp of last state update |
| `wait_since_ts` | Optional[float] | Timestamp when entered WAIT state |
| `error_streak` | int | Consecutive ERROR state count |

### Methods Added to PaneSummary

- `update_state(new_state: str, timestamp: float)` - Updates state and maintains tracking fields
- `_format_timestamp(ts: float) -> str` - Formats timestamp as "HH:MM:SS"
- `_format_wait_duration(wait_ts: float, now: float) -> str` - Formats duration as "30s", "2m", "1h"

### Enhanced Table Format

```
WINDOW         STATE    TASK_ID    LAST_UPDATE  WAIT_FOR   ERR  NOTE
--------------------------------------------------------------------------
master         WAIT     task-001   14:32:05     30s        -    "[y/n]"
worker-0       ERROR    task-002   14:31:45     -          3    Connection refused
```

### Key Behaviors

1. **ERROR Streak**: Increments on consecutive ERROR states, resets on other states
2. **WAIT Duration**: Set on entry, cleared on exit (except ERROR preserves it)
3. **Timestamp Updates**: Always updated on state change (including consecutive same states)

## Files Modified

| File | Changes |
|------|---------|
| `swarm/master.py` | Enhanced PaneSummary class, updated `_handle_pane_wait_states()`, `_update_summary_from_workers()`, `_format_summary_table()` |
| `tests/test_status_summary.py` | New test file with 15 unit tests |

## Test Coverage

| Test | Description |
|------|-------------|
| `test_pane_summary_new_fields_exist` | Verifies all new fields exist and are initialized correctly |
| `test_error_streak_increments_on_consecutive_errors` | Verifies error_streak increments on consecutive ERROR states |
| `test_error_streak_resets_on_non_error_state` | Verifies error_streak resets when leaving ERROR |
| `test_wait_since_ts_set_on_enter_wait` | Verifies wait_since_ts is set when entering WAIT |
| `test_wait_since_ts_cleared_on_leave_wait` | Verifies wait_since_ts is cleared when leaving WAIT |
| `test_timestamp_updated_on_state_change` | Verifies last_update_ts updates on state change |
| `test_timestamp_updated_on_repeated_state` | Verifies timestamp updates even on consecutive same state |
| `test_error_streak_preserves_wait_since_ts` | Verifies ERROR does NOT clear wait_since_ts |
| `test_state_updated_correctly` | Verifies last_state is updated by update_state |
| `test_format_timestamp` | Verifies _format_timestamp produces HH:MM:SS |
| `test_format_wait_duration_seconds` | Verifies seconds formatting |
| `test_format_wait_duration_minutes` | Verifies minutes formatting |
| `test_format_wait_duration_hours` | Verifies hours formatting |
| `test_format_wait_duration_no_wait` | Verifies dash for invalid timestamps |
| `test_initial_timestamp_is_recent` | Verifies initial timestamp is recent |

**Result**: 15 tests passed

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| ERROR does not clear wait_since_ts | Consecutive errors during a wait should still show total wait time |
| Duration calculated as `now - wait_ts` | Shows how long the pane has been in current state |
| Invalid timestamps (0 or negative) return "-" | Prevents confusion from malformed timestamps |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

```
PaneSummary fields: OK
error_streak logic: OK
wait_since_ts logic: OK
ERROR preserves wait_since_ts: OK
All verifications passed!
```

---

**Completed**: 2026-02-04
**Duration**: ~15 minutes
**Commit**: 83323cf
