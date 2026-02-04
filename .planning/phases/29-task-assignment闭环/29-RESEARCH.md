# Phase 29: 任务指派回执闭环 - Research

**Researched:** 2026-02-04
**Domain:** Master-Worker Task Assignment State Chain
**Confidence:** HIGH

## Summary

This phase implements proper state chain tracking for task assignment: **ASSIGNED → START → DONE/ERROR**. The current implementation has a critical inconsistency where Master broadcasts `START` with `event: ASSIGNED` meta instead of using the dedicated `ASSIGNED` state in `BroadcastState`.

**Key findings:**
1. `BroadcastState.ASSIGNED` exists in status_broadcaster.py but is never used correctly
2. Master writes `START` state with `meta.event = ASSIGNED` (wrong - should be pure ASSIGNED)
3. Worker writes `START` when beginning task execution (correct - Worker START = task execution begins)
4. Worker writes `DONE/ERROR` when completing task (correct)
5. The state chain `ASSIGNED → START → DONE` requires Master to broadcast ASSIGNED, not START

**Primary recommendation:** Modify `master_dispatcher.py dispatch_one()` to use `BroadcastState.ASSIGNED` instead of `BroadcastState.START` when assigning tasks.

## Standard Stack

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| StatusBroadcaster | swarm/status_broadcaster.py | JSONL status logging to status.log |
| MasterDispatcher | swarm/master_dispatcher.py | Task assignment from queue to workers |
| MasterScanner | swarm/master_scanner.py | Reads worker status from status.log |
| TaskLockManager | swarm/task_lock.py | Atomic task lock acquisition/release |
| SmartWorker | swarm/worker_smart.py | Worker task execution and status reporting |

### State Enum (BroadcastState)

```python
# From swarm/status_broadcaster.py lines 23-35
class BroadcastState(str, Enum):
    START = 'START'      # Worker began task execution
    ASSIGNED = 'ASSIGNED'  # Master assigned task to worker
    DONE = 'DONE'        # Worker completed task successfully
    WAIT = 'WAIT'        # Worker waiting for input
    ERROR = 'ERROR'      # Worker task failed
    HELP = 'HELP'         # Worker needs human assistance
    SKIP = 'SKIP'         # Task skipped
```

### File Paths

| Path | Purpose |
|------|---------|
| /tmp/ai_swarm/status.log | Shared JSONL status log |
| /tmp/ai_swarm/tasks.json | Task queue with status tracking |
| /tmp/ai_swarm/locks/{task_id}.lock | Task lock files |
| /tmp/ai_swarm/instructions/{worker_id}.jsonl | Worker mailbox for RUN_TASK |

## Architecture Patterns

### Current Flow (INCORRECT - Phase 29 to Fix)

```
Master Dispatch:
  1. Acquire task lock using worker_id
  2. Broadcast START with meta={event: ASSIGNED}  <- WRONG
  3. Write RUN_TASK to worker mailbox
  4. Update tasks.json status to ASSIGNED

Worker Execution:
  5. Poll mailbox, read RUN_TASK
  6. Broadcast START (task execution begins)       <- CORRECT
  7. Execute task (API calls, etc.)
  8. Broadcast DONE/ERROR (task complete)
  9. Release lock
```

### Corrected Flow (After Phase 29)

```
Master Dispatch:
  1. Acquire task lock using worker_id
  2. Broadcast ASSIGNED (task assigned to worker)  <- FIXED
  3. Write RUN_TASK to worker mailbox
  4. Update tasks.json status to ASSIGNED

Worker Execution:
  5. Poll mailbox, read RUN_TASK
  6. Broadcast START (task execution begins)
  7. Execute task (API calls, etc.)
  8. Broadcast DONE/ERROR (task complete)
  9. Release lock
```

### State Chain Validation

The correct state chain for a single task:

| State | Broadcaster | When |
|-------|-------------|------|
| ASSIGNED | Master | When dispatch_one() assigns task to worker |
| START | Worker | When worker begins executing the task |
| DONE/ERROR | Worker | When worker finishes (success/failure) |

**Gap Analysis:**
- `ASSIGNED` exists in BroadcastState but dispatch_one() uses START
- Need to verify Worker recognizes ASSIGNED before START
- Need to ensure status summary displays ASSIGNED state correctly

### Worker Idle Detection (master_dispatcher.py)

```python
# Lines 215-251: is_worker_idle() checks
def is_worker_idle(self, worker_status: WorkerStatus) -> bool:
    # WAIT state = not idle (waiting for human input)
    if worker_status.state == 'WAIT':
        return False
    # DONE, SKIP, ERROR with no lock = idle
    if worker_status.state in ('DONE', 'SKIP', 'ERROR'):
        if worker_status.task_id:
            lock_info = self._scanner.read_lock_state(worker_status.task_id)
            if lock_info and not lock_info.is_expired():
                return False  # Still holds lock
        return True
    # All other states (START, ASSIGNED) = not idle
    return False
```

**Note:** `is_worker_idle()` treats both `START` and `ASSIGNED` as not idle (returns False), which is correct behavior.

## Don't Hand-Roll

### Problem: Custom Status State Machine

**Don't Build:** A custom state machine for tracking task lifecycle.

**Use Instead:** The existing `BroadcastState` enum and `StatusBroadcaster` class, which already support:
- Atomic status broadcasts via fcntl.flock
- JSONL append format for audit trail
- Meta field for additional context (worker_id, timestamps, etc.)

**Why:** The existing implementation handles concurrent writes safely, provides consistent formatting, and integrates with the entire swarm ecosystem.

### Problem: Custom Lock Validation

**Don't Build:** Custom logic for validating lock ownership.

**Use Instead:** `TaskLockManager` which provides:
- Atomic O_CREAT|O_EXCL file creation (no race conditions)
- Lock expiration via TTL
- Heartbeat updates for long-running tasks
- JSON metadata for debugging

### Problem: Custom Worker Mailbox

**Don't Build:** Custom message passing between Master and Workers.

**Use Instead:** The existing JSONL mailbox format at `{instructions_dir}/{worker_id}.jsonl`:
- Master appends RUN_TASK instructions
- Worker reads and processes sequentially
- Offset tracking prevents duplicate processing

## Common Pitfalls

### Pitfall 1: Using START Instead of ASSIGNED (CRITICAL)

**What goes wrong:** status.log shows confusing state progression

Current incorrect entry:
```json
{"ts": "...", "worker_id": "master-dispatcher", "task_id": "task-001", "state": "START", "message": "Task assigned to worker-1", "meta": {"event": "ASSIGNED", "assigned_worker_id": "worker-1"}}
```

**Why it happens:** dispatch_one() uses `BroadcastState.START` instead of `BroadcastState.ASSIGNED`

**How to avoid:** In `master_dispatcher.py dispatch_one()`, line 302:
```python
# WRONG (current):
state=status_broadcaster.BroadcastState.START

# CORRECT (fix):
state=status_broadcaster.BroadcastState.ASSIGNED
```

**Warning signs:**
- status.log contains START entries with "assigned" in message
- Worker status shows START before Worker actually started work
- State priority sorting doesn't place ASSIGNED correctly

### Pitfall 2: Master Broadcasting with Worker ID

**What goes wrong:** Status log shows master-dispatcher as worker_id for ASSIGNED

**Why it happens:** Master dispatcher broadcasts with its own broadcaster (worker_id='master-dispatcher')

**How to avoid:** Include `assigned_worker_id` in meta so status scanning can match:
```python
meta={
    'assigned_worker_id': worker_id,  # The actual worker
    'source': 'master'  # Broadcasting source
}
```

**Impact:** Minor - this is acceptable behavior since ASSIGNED from master is distinguishable from START from worker.

### Pitfall 3: Race Condition Between ASSIGNED and START

**What goes wrong:** Master ASSIGNED, but Worker hasn't polled yet; Master might reassign

**Why it happens:** Task lock acquisition should prevent this, but timing gaps exist

**How to avoid:** The existing lock mechanism in dispatch_one():
1. Master acquires lock (O_CREAT|O_EXCL) - atomic
2. Master broadcasts ASSIGNED
3. Worker polls, verifies lock ownership via _verify_task_lock()
4. Worker broadcasts START

**Warning signs:** status.log shows ASSIGNED from master, then START from different worker (should not happen with proper locking)

### Pitfall 4: Summary Table Missing ASSIGNED State

**What goes wrong:** Status summary doesn't show ASSIGNED in priority ordering

**Why it happens:** STATE_PRIORITY in master.py doesn't include ASSIGNED

**Current STATE_PRIORITY (lines 54-61):**
```python
STATE_PRIORITY = {
    'ERROR': 0,
    'WAIT': 1,
    'RUNNING': 2,
    'START': 3,
    'DONE': 4,
    'SKIP': 5,
}
```

**How to avoid:** Add ASSIGNED to STATE_PRIORITY:
```python
STATE_PRIORITY = {
    'ERROR': 0,
    'WAIT': 1,
    'RUNNING': 2,
    'START': 3,
    'ASSIGNED': 4,  # Add this
    'DONE': 5,
    'SKIP': 6,
}
```

### Pitfall 5: Worker Not Recognizing ASSIGNED State

**What goes wrong:** Worker tries to poll for instructions while still in ASSIGNED state

**Why it happens:** Worker only checks mailbox offset, not state

**How to avoid:** This is actually fine - Worker polling is independent of state. Worker polls mailbox regardless of status.log state. Only the lock verification matters.

## Code Examples

### Fix: master_dispatcher.py dispatch_one()

```python
# Lines 297-323: Current (INCORRECT)
def dispatch_one(self, task: TaskInfo, worker_id: str) -> bool:
    # Acquire task lock using worker's ID
    worker_lock_manager = task_lock.TaskLockManager(worker_id=worker_id)
    acquired = worker_lock_manager.acquire_lock(task.task_id)
    if not acquired:
        return False

    try:
        # CURRENT (WRONG): Broadcast START with ASSIGNED meta
        self._broadcaster._broadcast(
            state=status_broadcaster.BroadcastState.START,
            task_id=task.task_id,
            message=f'Task assigned to {worker_id}',
            meta={
                'assigned_worker_id': worker_id,
                'event': 'ASSIGNED'
            }
        )
        # ... rest of method
```

```python
# FIXED: Broadcast ASSIGNED state (no meta needed)
def dispatch_one(self, task: TaskInfo, worker_id: str) -> bool:
    # Acquire task lock using worker's ID
    worker_lock_manager = task_lock.TaskLockManager(worker_id=worker_id)
    acquired = worker_lock_manager.acquire_lock(task.task_id)
    if not acquired:
        return False

    try:
        # FIXED: Broadcast ASSIGNED state
        self._broadcaster._broadcast(
            state=status_broadcaster.BroadcastState.ASSIGNED,
            task_id=task.task_id,
            message=f'Task assigned to {worker_id}',
            meta={
                'assigned_worker_id': worker_id
            }
        )
        # ... rest of method
```

### Worker START (Already Correct - worker_smart.py)

```python
# Lines 312-314: Worker broadcasts START when beginning execution
# START = worker actually started working on the task
self.broadcaster.broadcast_start(
    task_id=task_id,
    message=f'Starting task: {task_id}'
)
```

### Worker DONE (Already Correct - worker_smart.py)

```python
# Lines 360-363: Worker broadcasts DONE when complete
# DONE = task finished successfully
self.broadcaster.broadcast_done(
    task_id=task_id,
    message=f'Completed: {task_id} | Tokens: {input_tokens}+{output_tokens}'
)
```

### Verify State Chain in status.log

```bash
# After fix, status.log should show:
# 1. ASSIGNED from master-dispatcher (task assigned)
# 2. START from worker-X (worker started)
# 3. DONE from worker-X (worker finished)

cat /tmp/ai_swarm/status.log | grep task-001
# {"ts": "...", "worker_id": "master-dispatcher", "task_id": "task-001", "state": "ASSIGNED", "message": "Task assigned to worker-1", "meta": {"assigned_worker_id": "worker-1"}}
# {"ts": "...", "worker_id": "worker-1", "task_id": "task-001", "state": "START", "message": "Starting task: task-001"}
# {"ts": "...", "worker_id": "worker-1", "task_id": "task-001", "state": "DONE", "message": "Completed: task-001"}
```

## State of the Art

### Current State (Before Phase 29)

| Aspect | Current | Issue |
|--------|---------|-------|
| Dispatch broadcast | `START` with `meta.event=ASSIGNED` | Wrong state, confusing meta |
| Worker broadcast | `START` on task begin | Correct |
| Done broadcast | `DONE` on completion | Correct |
| State priority | No ASSIGNED | Missing from enum |
| Status summary | Doesn't show ASSIGNED | Not tracked |

### After Phase 29

| Aspect | After Fix | Notes |
|--------|-----------|-------|
| Dispatch broadcast | `ASSIGNED` (pure state) | Clean state chain |
| Worker broadcast | `START` on task begin | Unchanged |
| Done broadcast | `DONE` on completion | Unchanged |
| State priority | ASSIGNED at priority 4 | Between START and DONE |
| Status summary | Shows ASSIGNED | New column or state |

### Deprecated/Outdated Approaches

- `meta.event='ASSIGNED'` pattern: Was used to fake ASSIGNED state - no longer needed after fix
- START with assignment message: Confusing, replaced with dedicated ASSIGNED state

## Open Questions

### Q1: Should Master broadcast ASSIGNED using its own ID or worker's ID?

**Current behavior:** Master uses `worker_id='master-dispatcher'` for broadcasts.

**Options:**
1. Keep master-dispatcher as worker_id, put real worker in meta
2. Use the assigned worker's ID directly

**Recommendation:** Option 1 is current pattern, but Option 2 may be cleaner for state chain. Need to check if any code depends on broadcaster.worker_id matching actual worker.

**What we know:** `MasterDispatcher.__init__()` creates broadcaster with `worker_id='master-dispatcher'`.

**What's unclear:** Whether any downstream code expects ASSIGNED to come from the actual worker.

### Q2: Should ASSIGNED be visible in status summary?

**Current STATE_PRIORITY** in master.py:
```python
STATE_PRIORITY = {
    'ERROR': 0,
    'WAIT': 1,
    'RUNNING': 2,
    'START': 3,
    'DONE': 4,
    'SKIP': 5,
}
```

**Recommendation:** Add ASSIGNED between START (3) and DONE (4) so ASSIGNED tasks show as "in progress".

### Q3: What happens if Worker cannot be modified?

**Requirement:** "若无法修改 Worker，则通过 Master 侧广播 ASSIGNED，并确保 DONE 仍能匹配"

**Analysis:** The SmartWorker class (worker_smart.py) is modifiable Python code in this repository. We can change Worker behavior.

**However, if Worker cannot be modified:**
- Master broadcasts ASSIGNED (done)
- Worker continues to write START when it polls mailbox (unchanged)
- DONE matching happens via task_id (unchanged - DONE includes task_id)

## Sources

### Primary (HIGH confidence)
- `swarm/status_broadcaster.py` - BroadcastState enum with ASSIGNED state defined (line 30)
- `swarm/master_dispatcher.py` - dispatch_one() incorrectly uses START instead of ASSIGNED (line 302)
- `swarm/worker_smart.py` - process_task_streaming() broadcasts START then DONE correctly (lines 314, 360)
- `swarm/master.py` - STATE_PRIORITY missing ASSIGNED (lines 54-61)

### Secondary (MEDIUM confidence)
- `tests/test_master_dispatcher.py` - Tests for dispatch but don't verify ASSIGNED state
- `tests/test_status_broadcaster.py` - Tests all states except ASSIGNED (line 219-222 shows tested states)

### Tertiary (LOW confidence)
- Git history for master_dispatcher.py to understand original intent for ASSIGNED state

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components identified and verified
- Architecture: HIGH - State chain clearly understood
- Pitfalls: HIGH - Root cause identified (dispatch_one uses START instead of ASSIGNED)
- Code examples: HIGH - Exact line numbers and fix provided

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (stable codebase, changes are localized)

**Files needing modification for Phase 29:**
1. `swarm/master_dispatcher.py` - Change dispatch_one() to use ASSIGNED state
2. `swarm/master.py` - Add ASSIGNED to STATE_PRIORITY
3. `tests/test_master_dispatcher.py` - Add test verifying ASSIGNED state broadcast
