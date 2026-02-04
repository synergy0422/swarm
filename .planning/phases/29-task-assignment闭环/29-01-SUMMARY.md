---
phase: 29-task-assignment闭环
plan: "01"
type: execute
subsystem: master_dispatcher
tags: [task-assignment, state-chain, broadcast]
tech-stack:
  added: []
  patterns: [pure-state-broadcast, state-chain-tracking]
key-files:
  created: []
  modified: ["swarm/master_dispatcher.py", "swarm/master.py", "tests/test_master_dispatcher.py"]
decisions: []
---

# Phase 29 Plan 01: Task Assignment State Broadcast Summary

## Objective

Fix task assignment to broadcast proper ASSIGNED state, creating clear state chain: ASSIGNED → START → DONE/ERROR.

## One-Liner

Master dispatcher now broadcasts ASSIGNED state with proper state priority.

## Commits

| Hash | Message |
|------|---------|
| 68b1351 | feat(29-01): broadcast ASSIGNED state instead of START in dispatch |

## Changes Made

### Task 1: Change dispatch_one() to Broadcast ASSIGNED

- **File:** `swarm/master_dispatcher.py`
- **Change:** `BroadcastState.START` → `BroadcastState.ASSIGNED`
- **Removed:** `'event': 'ASSIGNED'` from meta (no longer needed)
- **Kept:** `'assigned_worker_id': worker_id` for tracking

**Before:**
```python
self._broadcaster._broadcast(
    state=status_broadcaster.BroadcastState.START,
    meta={'assigned_worker_id': worker_id, 'event': 'ASSIGNED'}
)
```

**After:**
```python
self._broadcaster._broadcast(
    state=status_broadcaster.BroadcastState.ASSIGNED,
    meta={'assigned_worker_id': worker_id}
)
```

### Task 2: Add ASSIGNED to STATE_PRIORITY

- **File:** `swarm/master.py`
- **Change:** Added `'ASSIGNED': 4` between START(3) and DONE(5)

```python
STATE_PRIORITY = {
    'ERROR': 0,
    'WAIT': 1,
    'RUNNING': 2,
    'START': 3,
    'ASSIGNED': 4,  # Tasks assigned but not yet started by worker
    'DONE': 5,
    'SKIP': 6,
}
```

### Task 3: Add Test for ASSIGNED State Broadcast

- **File:** `tests/test_master_dispatcher.py`
- **Test:** `test_dispatch_one_broadcasts_assigned_state`
- **Verifies:**
  - ASSIGNED state is broadcast (not START)
  - task_id is correct
  - message contains worker_id
  - assigned_worker_id in meta
  - No 'event' key in meta

## Verification Results

- `test_dispatch_one_broadcasts_assigned_state`: PASSED
- All 18 tests in `test_master_dispatcher.py`: PASSED

## State Chain After Fix

| State | Broadcaster | When |
|-------|-------------|------|
| ASSIGNED | Master | When dispatch_one() assigns task to worker |
| START | Worker | When worker begins executing the task |
| DONE/ERROR | Worker | When worker finishes (success/failure) |

## Deviations from Plan

None - plan executed exactly as written.

## Authentication Gates

None - no authentication required.

## Next Phase Readiness

Phase 29 is 100% complete. All three requirements for v1.87 are now done:
- ✓ Phase 27: Status summary enhancement (last_update, wait_for, error_streak)
- ✓ Phase 28: Auto-rescue configurable (ENABLED, ALLOW, BLOCK env vars)
- ✓ Phase 29: Task assignment闭环 (ASSIGNED → START → DONE/ERROR)

Ready for `/gsd:complete-milestone V1.87`

## Metrics

- **Duration:** < 5 min
- **Completed:** 2026-02-04
- **Files Modified:** 3 (swarm/master_dispatcher.py, swarm/master.py, tests/test_master_dispatcher.py)
- **Commits:** 1
