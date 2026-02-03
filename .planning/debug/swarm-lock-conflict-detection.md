---
status: resolved
trigger: "Investigate swarm_tasks_bridge.sh lock conflict detection bug"
created: 2026-02-04T00:00:00Z
updated: 2026-02-04T00:45:00Z
goal: audit
---

## Current Focus

investigation_complete: Root cause identified and documented with fix recommendations
next_action: Present findings to user

## Symptoms

expected: cmd_claim should:
- Exit 0 when lock acquired successfully
- Exit 2 when lock is held by another worker (conflict)
- Exit 1 for other failures (permission, corruption, no lock)

actual: cmd_claim incorrectly exits with code 2 for ALL check command successes, including "No lock" scenarios
errors: "Error: Lock held by 'unknown' for '...' (exit 2)" when no lock exists
reproduction: |
  The bug manifests when:
  1. acquire fails for ANY reason (including edge cases like race conditions)
  2. check is called to determine lock holder
  3. check returns exit 0 for "No lock" (lock doesn't exist)
  4. cmd_claim incorrectly treats this as a conflict and exits 2

## Evidence

### Evidence #1: check command returns exit 0 for "No lock" scenario
- Checked: swarm_lock.sh lines 189-191
- Found: |
  ```bash
  if [ ! -f "$LOCK_FILE" ]; then
      echo "No lock for '$TASK_ID'"
      exit 0
  fi
  ```
- Implication: check returns 0 when lock does NOT exist

### Evidence #2: check command returns exit 0 for "Active" or "Expired" scenario
- Checked: swarm_lock.sh lines 226-232
- Found: No explicit exit code after printing status - defaults to 0
- Implication: check returns 0 when lock exists AND is Active/Expired

### Evidence #3: cmd_claim treats any successful check as conflict
- Checked: swarm_tasks_bridge.sh lines 141-145
- Found: |
  ```bash
  if check_output=$("$SCRIPT_DIR/swarm_lock.sh" check "$lock_key" 2>/dev/null); then
      lock_holder=$(echo "$check_output" | awk -F': ' '/^  Worker: /{print $2; exit}')
      echo "Error: Lock held by '$lock_holder' for '$lock_key' (exit 2)" >&2
      exit 2
  fi
  ```
- Implication: Any check output (including "No lock") triggers exit 2 with "unknown" holder

### Evidence #4: Output format differs between "No lock" and "Active/Expired"
- Verified: swarm_lock.sh check output formats
- "No lock for '...':" - NO Worker line
- "Lock for '...': Active" - HAS Worker line
- Implication: awk pattern `^  Worker: ` only matches when lock exists

### Evidence #5: Live testing confirmed behavior
- Tested: swarm_tasks_bridge.sh claim with active lock
- Result: Correctly reports "Lock held by 'worker-0' (exit 2)"
- Verified: awk extracts worker correctly when Worker line exists

### Evidence #6: Expired lock behavior
- Tested: swarm_lock.sh check on expired lock
- Result: "Lock for 'expired-task': Expired" with Worker line
- acquire correctly allows expired locks to be replaced
- If acquire fails on expired lock, claim would incorrectly exit 2

## Reproduction Steps

### Step 1: Verify check command behavior on non-existent task
```bash
./scripts/swarm_lock.sh check nonexistent-task
# Output: "No lock for 'nonexistent-task'"
# Exit code: 0
```

### Step 2: Verify check command behavior on existing active lock
```bash
./scripts/swarm_lock.sh acquire test-task worker-0
./scripts/swarm_lock.sh check test-task
# Output: "Lock for 'test-task': Active" with Worker line
# Exit code: 0
```

### Step 3: Verify cmd_claim correctly handles active lock
```bash
./scripts/swarm_tasks_bridge.sh claim test-task worker-1
# Output: "Error: Lock held by 'worker-0' for 'test-task' (exit 2)"
# Exit code: 2  ← CORRECT behavior
```

### Step 4: Test expired lock handling
```bash
./scripts/swarm_lock.sh acquire expired-task worker-0 1
sleep 2
./scripts/swarm_lock.sh check expired-task
# Output: "Lock for 'expired-task': Expired" (status is Expired but check returns 0)
```

## Root Cause

**The `check` command returns exit 0 for BOTH scenarios:**
1. "No lock for '...'" - lock doesn't exist (line 189-191 in swarm_lock.sh)
2. "Lock for '...': Active" or "Expired" - lock exists (lines 225-233)

**The cmd_claim function incorrectly assumes ANY successful check means conflict:**
- Line 141: `if check_output=$("$SCRIPT_DIR/swarm_lock.sh" check "$lock_key" 2>/dev/null); then`
- This condition is TRUE for BOTH "no lock" and "lock exists"
- For "no lock" scenario, awk fails to extract worker, resulting in "unknown"
- cmd_claim then exits 2 (conflict) instead of 1 (other failure)

**Exit Code Semantics (from usage):**
- 0 = success (lock acquired)
- 2 = lock occupied (held by another worker)
- 1 = other failure

## Fix Recommendations

### Option A: Parse check output for "No lock" prefix (RECOMMENDED)
Modify cmd_claim to check if output starts with "No lock" and exit 1 instead of 2:

```bash
if check_output=$("$SCRIPT_DIR/swarm_lock.sh" check "$lock_key" 2>/dev/null); then
    if [[ "$check_output" == "No lock for "* ]]; then
        # Lock doesn't exist - acquire failed for other reasons
        echo "Error: Failed to acquire lock for '$lock_key'" >&2
        [[ -n "$acquire_output" ]] && echo "$acquire_output" >&2
        exit 1
    fi
    # Lock exists - extract worker and report conflict
    lock_holder=$(echo "$check_output" | awk -F': ' '/^  Worker: /{print $2; exit}')
    echo "Error: Lock held by '$lock_holder' for '$lock_key' (exit 2)" >&2
    exit 2
fi
```

**Trade-offs:**
- Pros: Minimal change, preserves existing check behavior, clear semantics
- Cons: Relies on string matching, could break if check output format changes

### Option B: Modify check to return non-zero for "No lock"
Change swarm_lock.sh check to return exit 1 when lock doesn't exist:

```bash
if [ ! -f "$LOCK_FILE" ]; then
    echo "No lock for '$TASK_ID'"
    exit 1  # Changed from 0 to 1
fi
```

**Trade-offs:**
- Pros: More semantically correct, check failures are meaningful
- Cons: Breaking change - callers that expect exit 0 may break

### Option C: Use acquire's error message directly
Parse acquire's error message instead of calling check:

```bash
if ! acquire_output=$("$SCRIPT_DIR/swarm_lock.sh" acquire "$lock_key" "$worker" 2>&1); then
    if [[ "$acquire_output" == *"Lock already exists"* ]]; then
        # Extract worker from acquire error or call check
        exit 2
    else
        exit 1
    fi
fi
```

**Trade-offs:**
- Pros: No additional check call needed
- Cons: Fragile - relies on error message format

## Recommended Approach

**Option A** is recommended because:
1. Minimal change with low risk
2. Preserves backward compatibility with check command
3. Clear semantics: "No lock" = other failure, "Lock for..." = conflict
4. Easy to understand and maintain

## Verification Checklist

After fix is implemented, verify:
- [ ] "No lock" scenario: claim exits 1 with generic "Failed to acquire" message
- [ ] Active lock: claim exits 2 with correct worker name
- [ ] Expired lock: acquire succeeds (existing behavior), claim not triggered
- [ ] Other failures (permissions, etc.): claim exits 1

## Files Involved

- `/home/user/projects/AAA/swarm/scripts/swarm_tasks_bridge.sh` - Contains the bug (lines 141-145)
- `/home/user/projects/AAA/swarm/scripts/swarm_lock.sh` - check command returns exit 0 for both scenarios
