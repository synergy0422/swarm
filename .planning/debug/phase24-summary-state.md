---
status: resolved
trigger: "Investigate 4 issues in AI Swarm Phase 24 implementation"
created: 2026-02-04T00:00:00Z
updated: 2026-02-04T00:00:00Z
---

## Current Focus
Investigation complete. All issues analyzed with root causes identified.

---

## Root Cause Analysis Summary

| Issue | Priority | Root Cause | Status |
|-------|----------|------------|--------|
| Issue 1 | HIGH | `_update_summary_from_workers()` unconditionally overwrites pane-detected states | CONFIRMED |
| Issue 2 | MEDIUM | `broadcast_start()` creates START records that pollute status statistics | CONFIRMED |
| Issue 3 | MEDIUM | No IDLE reset when pane patterns no longer match | CONFIRMED |
| Issue 4 | LOW | DANGEROUS_PATTERNS list is limited | CONFIRMED |

---

## Issue 1: 状态汇总表会覆盖自动救援状态 (高优先级)

### Root Cause
**`_update_summary_from_workers()` unconditionally overwrites `PaneSummary.last_state`**

The state flow is broken in `output_status_summary()`:

1. `_handle_pane_wait_states()` detects dangerous/auto-enter patterns in pane content
2. Sets `PaneSummary.last_state` to ERROR/WAIT/RUNNING based on detection
3. `output_status_summary()` then calls `_update_summary_from_workers()` which **unconditionally overwrites** `last_state` with the latest state from status.log

### Code Evidence

**master.py lines 427-435 - output_status_summary():**
```python
def output_status_summary(self) -> None:
    """Output status summary table to stdout."""
    workers = self.scanner.scan_workers()
    self._update_summary_from_workers(workers)  # OVERWRITES pane state!

    summary_table = self._format_summary_table()
    print(summary_table)
```

**master.py lines 406-425 - _update_summary_from_workers():**
```python
def _update_summary_from_workers(self, workers: Dict[str, dict]) -> None:
    for worker_id, status in workers.items():
        window_name = worker_id

        if window_name not in self._pane_summaries:
            self._pane_summaries[window_name] = PaneSummary(window_name)
        summary = self._pane_summaries[window_name]

        state = status.get('state', 'IDLE')
        task_id = status.get('task_id', '-')

        summary.task_id = task_id
        summary.last_state = state  # <-- UNCONDITIONAL OVERWRITE!
```

**master.py lines 288-329 - _handle_pane_wait_states():**
```python
def _handle_pane_wait_states(self) -> None:
    # ... scans panes and updates summary ...
    if action == 'auto_enter':
        summary.last_state = 'RUNNING'
        summary.last_action = 'AUTO_ENTER'
        summary.note = f'"{pattern}"'
    elif action == 'manual_confirm_needed':
        summary.last_state = 'WAIT'  # <-- Set here...
        summary.last_action = 'MANUAL'
        summary.note = f'"{pattern}"'
    elif action == 'dangerous_blocked':
        summary.last_state = 'ERROR'  # <-- Set here...
        summary.last_action = 'BLOCKED'
        summary.note = f'[DANGEROUS] {pattern}'
```

### Impact
- Dangerous patterns detected in panes show ERROR state briefly
- But when `output_status_summary()` is called, status.log state (e.g., RUNNING, DONE) overwrites it
- Summary table never shows ERROR for dangerous patterns
- Manual confirm needed states are also hidden

### Recommended Fix
Priority-based state merging: when updating from workers, only overwrite if:
- Worker state has higher priority than pane-detected state
- OR pane-detected state was IDLE

State priority (highest first): ERROR > WAIT > RUNNING > DONE > IDLE

```python
def _update_summary_from_workers(self, workers: Dict[str, dict]) -> None:
    for worker_id, status in workers.items():
        window_name = worker_id

        if window_name not in self._pane_summaries:
            self._pane_summaries[window_name] = PaneSummary(window_name)
        summary = self._pane_summaries[window_name]

        worker_state = status.get('state', 'IDLE')
        task_id = status.get('task_id', '-')

        summary.task_id = task_id

        # Priority-based merge: only update if worker state has higher priority
        # ERROR(0) > WAIT(1) > RUNNING(2) > DONE(4) > IDLE(99)
        worker_priority = self._get_state_priority(worker_state)
        pane_priority = self._get_state_priority(summary.last_state)

        if worker_priority < pane_priority:
            summary.last_state = worker_state
```

---

## Issue 2: broadcast_start() 污染状态日志 (中优先级)

### Root Cause
**AutoRescuer uses `broadcast_start()` for auto-enter operations, creating master START records**

When AutoRescuer executes auto-enter rescue, it broadcasts a START state:
- `worker_id = 'master'` (from StatusBroadcaster initialization)
- `state = 'START'`
- This pollutes status.log with non-worker events

### Code Evidence

**auto_rescuer.py lines 221-225 - check_and_rescue():**
```python
# Use broadcast with START state as generic status indicator
self.broadcaster.broadcast_start(
    task_id='',
    message=f'Auto-rescued {window_name}: detected "{auto_pattern}"'
)
```

**master.py line 267 - Master.__init__():**
```python
self.broadcaster = StatusBroadcaster(worker_id='master')
```

**status_broadcaster.py lines 166-174 - broadcast_start():**
```python
def broadcast_start(self, task_id: str, message: str = "") -> None:
    """Convenience method to broadcast START state."""
    self._broadcast(BroadcastState.START, task_id, message)
```

### Impact
- Status statistics include master START events from auto-rescue
- May cause incorrect "active worker" counts
- Interferes with worker availability tracking

### Recommended Fix
Use neutral status broadcast instead of START:

Option A: Add INFO/STATUS state to BroadcastState enum
```python
# In status_broadcaster.py
class BroadcastState(str, Enum):
    # ... existing states ...
    INFO = 'INFO'  # or 'STATUS' for neutral events
```

Option B: Use meta field to mark internal events (less intrusive)
```python
self.broadcaster.broadcast_start(
    task_id='',
    message=f'Auto-rescued {window_name}: detected "{auto_pattern}"',
    meta={'internal_event': True, 'auto_rescue': True}
)
```

Then filter in scanner if needed.

---

## Issue 3: 汇总表状态可能过期不更新 (中优先级)

### Root Cause
**`_handle_pane_wait_states()` never resets state to IDLE when patterns no longer match**

When pane content no longer contains any patterns:
- `action = 'none'` or `action = 'cooldown'`
- `last_state` is NOT updated
- Previously set ERROR/WAIT states persist indefinitely

### Code Evidence

**master.py lines 288-329 - _handle_pane_wait_states():**
```python
def _handle_pane_wait_states(self) -> None:
    pane_contents = self.pane_scanner.scan_all(self.session_name)

    for window_name, content in pane_contents.items():
        if window_name not in self._pane_summaries:
            self._pane_summaries[window_name] = PaneSummary(window_name)
        summary = self._pane_summaries[window_name]

        should_rescue, action, pattern = self.auto_rescuer.check_and_rescue(...)

        # Update summary based on action
        if action == 'auto_enter':
            summary.last_state = 'RUNNING'
            # ...
        elif action == 'manual_confirm_needed':
            summary.last_state = 'WAIT'
            # ...
        elif action == 'dangerous_blocked':
            summary.last_state = 'ERROR'
            # ...
        elif action == 'cooldown':
            summary.last_action = 'COOLDOWN'
            # ...
        # NO else clause for 'none' or other actions!
```

**PaneSummary initialization (lines 212-217):**
```python
def __init__(self, window_name: str):
    self.window_name = window_name
    self.last_state = 'IDLE'
    self.last_action = ''
    self.task_id = '-'
    self.note = ''
```

### Impact
- Pane that previously had ERROR (dangerous pattern) shows ERROR forever
- Even after pattern is gone and pane is doing normal work
- Summary table becomes misleading

### Recommended Fix
Reset state to IDLE when no significant action detected:

```python
def _handle_pane_wait_states(self) -> None:
    pane_contents = self.pane_scanner.scan_all(self.session_name)

    for window_name, content in pane_contents.items():
        if window_name not in self._pane_summaries:
            self._pane_summaries[window_name] = PaneSummary(window_name)
        summary = self._pane_summaries[window_name]

        should_rescue, action, pattern = self.auto_rescuer.check_and_rescue(...)

        if action == 'auto_enter':
            summary.last_state = 'RUNNING'
            summary.last_action = 'AUTO_ENTER'
            summary.note = f'"{pattern}"'
        elif action == 'manual_confirm_needed':
            summary.last_state = 'WAIT'
            summary.last_action = 'MANUAL'
            summary.note = f'"{pattern}"'
        elif action == 'dangerous_blocked':
            summary.last_state = 'ERROR'
            summary.last_action = 'BLOCKED'
            summary.note = f'[DANGEROUS] {pattern}'
        elif action == 'cooldown':
            summary.last_action = 'COOLDOWN'
            remaining = self.auto_rescuer.get_cooldown_time(window_name)
            summary.note = f'Wait {remaining:.1f}s'
        elif action == 'none':
            # Reset to IDLE when no patterns detected
            summary.last_state = 'IDLE'
            summary.last_action = ''
            summary.note = ''
        elif action == 'rescue_failed':
            # Failed rescue - could be ERROR or WAIT
            summary.last_state = 'WAIT'
            summary.last_action = 'FAILED'
            summary.note = f'Rescue failed: "{pattern}"'
```

---

## Issue 4: 危险关键字列表较窄 (低优先级)

### Root Cause
**DANGEROUS_PATTERNS in auto_rescuer.py only covers 8 patterns**

Current list focuses on file deletion and database operations but misses many dangerous patterns.

### Code Evidence

**auto_rescuer.py lines 73-84 - DANGEROUS_PATTERNS:**
```python
DANGEROUS_PATTERNS = [
    r'rm\s+-rf',           # Force recursive delete
    r'rm\s+-r',            # Recursive delete
    r'rm\s+-fr',           # Force recursive delete
    r'shred',              # Secure file deletion
    r'DROP\s+DATABASE',    # Database deletion
    r'DROP\s+TABLE',       # Table deletion
    r'DROP\s+INDEX',       # Index deletion
    r'TRUNCATE',           # Table truncation
]
```

### Missing Patterns

**Shell/Command Injection:**
- `\$\(` - Command substitution
- `|` - Pipe to shell
- `&&` / `||` - Command chaining
- `;` - Command separator
- `>>` / `>` - Redirect overwrite
- `mkfs` - Filesystem creation (destructive)
- `dd if=/dev/zero` - Disk writing

**Database (expanded):**
- `DELETE\s+FROM` - Data deletion
- `ALTER\s+.*\s+DROP` - Schema modification
- `DROP\s+VIEW` - View deletion
- `DROP\s+SCHEMA` - Schema deletion

**Filesystem (expanded):**
- `chmod\s+[0-7]{3,4}` - Permission changes
- `chown` - Ownership changes
- `mv\s+.*\s+/dev/null` - Move to null

**Time-based attacks:**
- `sleep\s+[0-9]+` - Could be DoS
- `while\s+true` - Infinite loop

### Recommended Fix
Expand DANGEROUS_PATTERNS to include:

```python
DANGEROUS_PATTERNS = [
    # File deletion (existing)
    r'rm\s+-rf',
    r'rm\s+-r',
    r'rm\s+-fr',
    r'shred',

    # Database operations (existing + expanded)
    r'DROP\s+DATABASE',
    r'DROP\s+TABLE',
    r'DROP\s+INDEX',
    r'DROP\s+VIEW',
    r'DROP\s+SCHEMA',
    r'TRUNCATE',
    r'DELETE\s+FROM',
    r'ALTER\s+.*\s+DROP',

    # Shell/command injection (NEW)
    r'\$\(',
    r'\|.*\w',  # Pipe to command
    r'&&\s*\w',
    r';\s*\w',
    r'>>\s*\/',
    r'>\s*\/',

    # Destructive operations (NEW)
    r'mkfs',
    r'dd\s+if=\/dev\/zero',

    # Permission changes (NEW)
    r'chmod\s+[0-7]{3,4}',
]
```

### Risk Assessment
- HIGH: File/database deletion patterns - CONFIRMED
- MEDIUM: Shell injection - worth adding
- LOW: Permission changes - depends on security requirements

---

## Resolution

### Root Causes Identified

| Issue | Root Cause |
|-------|------------|
| Issue 1 | `_update_summary_from_workers()` unconditionally overwrites pane-detected ERROR/WAIT states |
| Issue 2 | `broadcast_start()` creates master START records that pollute status.log |
| Issue 3 | `_handle_pane_wait_states()` doesn't reset state to IDLE when patterns no longer match |
| Issue 4 | DANGEROUS_PATTERNS only covers 8 basic patterns, missing many dangerous commands |

### Fix Priority

1. **Issue 1 (HIGH)** - Priority-based state merging in `_update_summary_from_workers()`
2. **Issue 3 (MEDIUM)** - Add IDLE reset in `_handle_pane_wait_states()` for 'none' action
3. **Issue 2 (MEDIUM)** - Use INFO/STATUS state or meta flags for internal events
4. **Issue 4 (LOW)** - Expand DANGEROUS_PATTERNS based on security requirements

### Files to Modify

- `/home/user/projects/AAA/swarm/swarm/master.py`
  - `_update_summary_from_workers()`: Add priority-based state merging
  - `_handle_pane_wait_states()`: Add IDLE reset for 'none' action

- `/home/user/projects/AAA/swarm/swarm/auto_rescuer.py`
  - `check_and_rescue()`: Change broadcast_start() to use neutral state

- `/home/user/projects/AAA/swarm/swarm/status_broadcaster.py`
  - Optionally add INFO/STATUS state for neutral events
