---
status: resolved
trigger: "Phase 24 follow-up issues investigation"
created: 2026-02-04T00:00:00.000Z
updated: 2026-02-04T00:00:00.000Z
---

## Current Focus
<!-- COMPLETE - All issues analyzed and fixed -->

## Optimization Notes (Non-Blocking)

These are improvements to consider in future iterations:

### 1. broadcast_done Still Pollutes status.log
**Observation:** broadcast_done writes to status.log with worker_id=master.
**Impact:** May affect worker status chain statistics.
**Suggestion:** Consider writing to separate log or using INFO-type messages.

### 2. IDLE Override Limited Scope
**Observation:** IDLE override only handles ERROR/WAIT.
**Impact:** If pane is "stuck" but not in ERROR/WAIT state, may not recover.
**Suggestion:** Add additional rules for other stuck scenarios if discovered.

## Symptoms

### Issue 1: State Priority Merge Never Downgrades
- **Expected:** ERROR/WAIT states should eventually clear when conditions resolve
- **Actual:** ERROR/WAIT become permanent once set
- **Root Cause:** Priority merge only allows upward movement (ERROR→WAIT→RUNNING→...), never downward

### Issue 2: Dangerous Patterns Too Broad
- **Expected:** Block only truly dangerous shell operations
- **Actual:** Blocks common operations like `cat file.txt | grep pattern`
- **Root Cause:** Regex patterns lack context awareness and are too greedy

### Issue 3: broadcast_wait Semantics Confused
- **Expected:** WAIT means "waiting for user input"
- **Actual:** Auto-rescue events use broadcast_wait but don't wait for user
- **Root Cause:** No INFO state available, [AUTO-RESCUE] prefix in message but state is still WAIT

---

## Evidence

### Issue 1 Evidence

**Code Path Analysis (master.py lines 415-444):**
```python
def _update_summary_from_workers(self, workers: Dict[str, dict]) -> None:
    # ...
    worker_priority = self._get_state_priority(worker_state)
    pane_priority = self._get_state_priority(summary.last_state)

    if worker_priority < pane_priority:
        summary.last_state = worker_state
```

**STATE_PRIORITY (master.py lines 54-61):**
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

**State Transition Scenario:**
1. Pane detects dangerous pattern → `_handle_pane_wait_states()` sets `summary.last_state = 'ERROR'`
2. Auto-rescue executes → Pane content changes (no dangerous pattern)
3. Next scan → `_handle_pane_wait_states()` returns action='none'
4. Worker reports DONE → `_update_summary_from_workers()` checks:
   - worker_priority (DONE=4) vs pane_priority (ERROR=0)
   - 4 < 0 is FALSE → No update
5. Summary remains ERROR permanently

**Wait, let me re-read the flow more carefully...**

Actually, looking at `_handle_pane_wait_states()` again:
```python
elif action == 'none':
    # Reset to IDLE when no patterns detected
    summary.last_state = 'IDLE'
    summary.last_action = ''
    summary.note = ''
```

When action='none', it DOES reset to IDLE. So when would the bug manifest?

Let me trace through more carefully:

**Scenario 1: Dangerous pattern detected**
1. Pane scan finds dangerous pattern
2. `check_and_rescue()` returns action='dangerous_blocked'
3. Code sets: `summary.last_state = 'ERROR'`, `summary.last_action = 'BLOCKED'`
4. Worker reports ERROR to status.log (dangerous pattern blocked)

**Scenario 2: Next pane scan - still dangerous**
1. Pane scan still finds dangerous pattern
2. `check_and_rescue()` returns action='dangerous_blocked'
3. Code sets: `summary.last_state = 'ERROR'` (already was ERROR, no change)

**Scenario 3: Auto-rescue executed (Enter sent)**
1. Auto-rescue sends Enter
2. Next pane scan - pattern no longer visible
3. `check_and_rescue()` returns action='none'
4. Code sets: `summary.last_state = 'IDLE'`

**Scenario 4: Worker still reporting ERROR from Scenario 1**
1. `_update_summary_from_workers()` called with worker_state='ERROR'
2. summary.last_state='IDLE' (from Scenario 3)
3. worker_priority=0 (ERROR), pane_priority=99 (IDLE, not in STATE_PRIORITY)
4. 0 < 99 is TRUE → Updates to ERROR
5. Summary now ERROR again!

**Root Cause Found:** There's a race condition. When pane scan resets to IDLE, but worker still has old ERROR state, the worker update overwrites the IDLE back to ERROR.

The fix needs to: when worker reports ERROR but pane scan shows 'none', the pane scan (IDLE) should take precedence.

### Issue 2 Evidence

**Current DANGEROUS_PATTERNS (auto_rescuer.py lines 75-103):**
```python
DANGEROUS_PATTERNS = [
    # Shell/command injection
    r'\$\(',              # Command substitution - TOO BROAD
    r'\|.*\w',             # Pipe to command - TOO BROAD
    r'&&\s*\w',            # Chained command execution - TOO BROAD
    r';\s*\w',             # Sequential command execution - TOO BROAD
    r'>>\s*\/',            # Append redirect to root - REASONABLE
    r'>\s*\/',             # Write redirect to root - REASONABLE
]
```

**Problematic Pattern Analysis:**

| Pattern | Matches (Good) | Matches (Bad) | Verdict |
|---------|---------------|----------------|---------|
| `\$\(` | `$(command)` injection | `value=$((1+2))` arithmetic | TOO BROAD |
| `\|.*\w` | `cat file | rm` | `cat file.txt \| grep pattern` | TOO BROAD |
| `&&\s*\w` | `cmd && rm` | `cmd1 && cmd2` normal chaining | TOO BROAD |
| `;\s*\w` | `; rm` | `cmd1; cmd2` normal separator | TOO BROAD |
| `>>\s*\/` | `>> /etc/passwd` | N/A | OK |
| `>\s*\/` | `> /etc/passwd` | `> file.txt` normal redirect | TOO BROAD |

**Impact Assessment:**
- Any command with pipes will be blocked
- Common patterns like `cmd1 && cmd2` won't work
- Arithmetics like `$((1+2))` blocked
- User will be constantly interrupted for false positives

### Issue 3 Evidence

**broadcast_wait Usage (auto_rescuer.py lines 241-244):**
```python
self.broadcaster.broadcast_wait(
    task_id='',
    message=f'[AUTO-RESCUE] {window_name}: detected "{auto_pattern}"'
)
```

**BroadcastState Enum (status_broadcaster.py lines 23-35):**
```python
class BroadcastState(str, Enum):
    START = 'START'
    ASSIGNED = 'ASSIGNED'
    DONE = 'DONE'
    WAIT = 'WAIT'      # <-- Used for auto-rescue
    ERROR = 'ERROR'
    HELP = 'HELP'
    SKIP = 'SKIP'
```

**Semantic Analysis:**
- WAIT definition: "waiting for user input"
- Auto-rescue scenario: System automatically sends Enter, NOT waiting
- Mismatch: WAIT state suggests user intervention needed, but system is proceeding

**Message Prefix Observation:**
- Message includes `[AUTO-RESCUE]` prefix to distinguish
- But state is still WAIT, creating cognitive dissonance
- Logs will show WAIT state for events that aren't actually waiting

---

## Root Cause Analysis

### Issue 1: Race Condition Between Pane Scan and Worker Status

**Root Cause:** Two sources update pane summary with different timing:
1. Pane scanning (can reset to IDLE via action='none')
2. Worker status (can set to ERROR)

When pane scan resets to IDLE but worker hasn't updated its ERROR yet, the worker update overwrites IDLE back to ERROR.

**Evidence:** The race condition is visible in the code flow:
1. `_handle_pane_wait_states()` resets to IDLE when action='none'
2. `_update_summary_from_workers()` can immediately overwrite with ERROR if worker hasn't updated

**Fix Direction:** When pane scan shows 'none' (IDLE), it should take precedence over worker status until worker updates to match.

### Issue 2: Regex Patterns Too Broad

**Root Cause:** Patterns are designed for worst-case but match common legitimate operations.

**Analysis of Each Problematic Pattern:**

1. **`r'\$\('`** - Matches command substitution `$(cmd)`
   - Good: Catches `$(whoami)` injection
   - Bad: Catches `result=$(date)` normal usage
   - Bad: Catches `$((1+2))` arithmetic (different syntax!)

2. **`r'\|.*\w'`** - Matches pipes
   - Good: Catches `cat file | rm` (pipe to remove)
   - Bad: Catches `cat file.txt | grep pattern` normal pipe
   - Bad: Matches any `\w` after pipe, too greedy

3. **`r'&&\s*\w'`** - Matches && chains
   - Good: Catches `cmd && rm` destructive chain
   - Bad: Catches `npm install && npm test` normal chain

4. **`r';\s*\w'`** - Matches ; separators
   - Good: Catches `; rm` malicious
   - Bad: Catches `cmd1; cmd2` normal

5. **`r'>\s*\/'`** - Matches writes to root
   - Good: Catches `> /etc/passwd` destructive
   - Bad: Catches `> file.txt` normal redirect
   - Pattern should require `/` immediately after `>`

**Fix Direction:** Keep patterns that are clearly dangerous, remove or narrow those that match common operations.

### Issue 3: Semantic Mismatch in Broadcast State

**Root Cause:** BroadcastState enum lacks an INFO or AUTO status. The system uses WAIT for everything that isn't START/DONE/ERROR.

**Current Approach (commit 0f49583):**
- Use `[AUTO-RESCUE]` prefix in message
- But state remains WAIT

**Why This Doesn't Work:**
- WAIT semantically means "waiting for user input"
- Auto-rescue is NOT waiting - it's automatically proceeding
- State should reflect reality, not just message prefix

**Fix Direction:** Use DONE (auto-rescue completed successfully) instead of WAIT.

---

## Recommended Fixes

### Issue 1 Fix: Pane Scan Should Override Worker Status When Clean

Modify `_update_summary_from_workers()` to respect pane scan results:

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

        worker_priority = self._get_state_priority(worker_state)
        pane_priority = self._get_state_priority(summary.last_state)

        # Pane scan showing IDLE (clean) takes precedence over worker ERROR/WAIT
        # This handles the race condition where pane cleared but worker hasn't updated
        if summary.last_state == 'IDLE' and worker_state in ('ERROR', 'WAIT'):
            # Don't update - pane is clean, worker will eventually update
            continue

        if worker_priority < pane_priority:
            summary.last_state = worker_state
```

**Alternative (Simpler):** Always trust pane scan over worker status for ERROR/WAIT:
```python
# If pane scan shows IDLE, don't let worker ERROR override it
if summary.last_state == 'IDLE' and worker_state in ('ERROR', 'WAIT'):
    continue
```

**Risk:** Low - only affects the race condition path.

### Issue 2 Fix: Narrow Dangerous Patterns

**Remove overly broad patterns:**
- `r'\|.*\w'` - matches normal pipes
- `r'&&\s*\w'` - matches normal chaining
- `r';\s*\w'` - matches normal separators
- `r'\$\('` - matches arithmetic and normal usage

**Keep focused patterns:**
```python
DANGEROUS_PATTERNS = [
    # File deletion
    r'rm\s+-rf',           # Force recursive delete
    r'rm\s+-r',            # Recursive delete
    r'rm\s+-fr',           # Force recursive delete
    r'shred',              # Secure file deletion

    # Database operations
    r'DROP\s+DATABASE',
    r'DROP\s+TABLE',
    r'DROP\s+INDEX',
    r'DROP\s+VIEW',
    r'DROP\s+SCHEMA',
    r'TRUNCATE',
    r'DELETE\s+FROM',
    r'ALTER\s+.*\s+DROP',

    # Shell injection - focused on clear danger
    r'\$\(.*\)',           # Command substitution (require closing paren)
    r'>>\s*\/',            # Append to root
    r'>\s*\/',             # Write to root (with space before /)

    # Destructive
    r'mkfs',
    r'dd\s+if=\/dev\/zero',
]
```

**Changes:**
1. Remove `r'&&\s*\w'`, `r';\s*\w'`, `r'\|.*\w'`
2. `r'\$\('` → `r'\$\(.*\)'` - Require closing paren to reduce false positives

**Risk:** Medium - removes some security coverage, but keeps high-risk patterns.

### Issue 3 Fix: Use broadcast_done for Auto-Rescue

Since auto-rescue completes successfully (Enter sent, prompt cleared), use DONE:

```python
# In check_and_rescue(), change:
self.broadcaster.broadcast_wait(
    task_id='',
    message=f'[AUTO-RESCUE] {window_name}: detected "{auto_pattern}"'
)

# To:
self.broadcaster.broadcast_done(
    task_id='',
    message=f'[AUTO-RESCUE] {window_name}: detected "{auto_pattern}"'
)
```

**Rationale:**
- Auto-rescue IS a completed operation
- DONE semantically means "task/operation finished"
- State now matches reality

**Risk:** Low - correct semantics, no breaking changes.

---

## Risk Assessment

| Issue | Fix | Risk Level | Rationale |
|-------|-----|------------|-----------|
| #1 | Pane IDLE overrides worker ERROR | LOW | Fixes race condition, improves accuracy |
| #2 | Narrow patterns to high-risk | MEDIUM | Removes some coverage, reduces false positives |
| #3 | broadcast_done instead of broadcast_wait | LOW | Correct semantics |

---

## Files to Modify

1. **swarm/master.py**
   - Function: `_update_summary_from_workers()` (lines 415-444)
   - Add IDLE override logic for race condition

2. **swarm/auto_rescuer.py**
   - Constant: `DANGEROUS_PATTERNS` (lines 75-103)
   - Remove overly broad patterns

3. **swarm/auto_rescuer.py**
   - Method: `check_and_rescue()` (lines 241-244)
   - Change `broadcast_wait` to `broadcast_done`

---

## Verification Plan

### Issue 1 Verification
```python
# Test: Pane IDLE should override worker ERROR (race condition fix)
def test_pane_idle_overrides_worker_error():
    summary = PaneSummary('test')
    summary.last_state = 'IDLE'  # Pane scan shows clean

    workers = {'test': {'state': 'ERROR', 'task_id': '-'}}  # Worker hasn't updated

    master._update_summary_from_workers(workers)

    # Should NOT update to ERROR - pane is clean
    assert summary.last_state == 'IDLE', "Pane IDLE should override worker ERROR"
```

### Issue 2 Verification
```python
# Test: Normal commands should NOT be blocked
def test_normal_commands_not_blocked():
    normal_commands = [
        'cat file.txt | grep pattern',
        'cmd1 && cmd2',
        'cmd1; cmd2',
        'value=$((1+2))',
        'echo "test" > file.txt',
    ]

    for cmd in normal_commands:
        result = rescuer._match_dangerous(cmd)
        assert result == '', f"Normal command '{cmd}' should not be blocked"
```

### Issue 3 Verification
```python
# Test: Auto-rescue uses broadcast_done, not broadcast_wait
def test_auto_rescue_uses_done():
    # Patch broadcaster
    original_broadcast_wait = broadcaster.broadcast_wait
    broadcaster.broadcast_wait = Mock()
    broadcaster.broadcast_done = Mock()

    rescuer.check_and_rescue(pane_output, 'test', 'session')

    assert broadcaster.broadcast_done.called, "Should use broadcast_done"
    assert not broadcaster.broadcast_wait.called, "Should not use broadcast_wait"
```

---

## Summary

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| #1 | Race condition: pane IDLE overwritten by worker ERROR | Pane IDLE takes precedence |
| #2 | Patterns too broad, match normal usage | Narrow to high-risk only |
| #3 | WAIT semantically wrong for auto-rescue | Use broadcast_done |

**Total Files to Modify:** 2 (master.py, auto_rescuer.py)
**Estimated Complexity:** Low - all fixes are localized changes
