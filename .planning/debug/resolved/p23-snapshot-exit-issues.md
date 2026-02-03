---
status: resolved
trigger: "Phase 23 snapshot script exit issues - tmux session not found should exit non-zero, exit code logic inconsistent with partial failure strategy"
created: 2026-02-03T00:00:00+08:00
updated: 2026-02-03T18:30:00+08:00
---

## Current Focus
hypothesis: "Confirmed - Issue 1: Line 317-319 shows warning but doesn't exit; Issue 2: Exit code treats all errors equally (critical + optional)"
test: "Complete code analysis"
expecting: "Both issues confirmed - ready to implement fix"
next_action: "Implement fix: 1) Exit 1 on session not found, 2) Separate CRITICAL vs OPTIONAL errors"

## Symptoms
expected: |
  1. Session not found should exit non-zero (exit 1) with clear message
  2. Partial failure should continue (exit 0) for optional files like status.log, locks
  3. Summary should show "Session: NOT FOUND" when session missing
actual: |
  1. Session not found shows warning but continues, generates empty snapshot
  2. Any error (missing session, status.log, locks) causes exit 1
  3. Shows misleading "snapshot complete" message
errors: |
  - "No such session" warning at line 317-319 but continues execution
  - exit 1 triggered by missing optional files
reproduction: |
  Run: ./swarm_snapshot.sh --session NONEEXISTENT
  - Should fail with exit 1
  - Currently shows warning then continues
started: "Always broken - implementation doesn't match plan requirement"

## Evidence
- timestamp: 2026-02-03T00:05:00+08:00
  checked: "Line 89-95 - check_tmux_session() function"
  found: "Function correctly returns 1 and adds error when session not found"
  implication: "Session check works correctly at function level"

- timestamp: 2026-02-03T00:05:00+08:00
  checked: "Line 317-319 - main() session check"
  found: "Shows warning but continues execution with '|| true' on dump functions"
  implication: "ROOT CAUSE for Issue 1 - Warning instead of exit 1 allows empty snapshot"

- timestamp: 2026-02-03T00:05:00+08:00
  checked: "Lines 322-326 - dump functions with || true"
  found: "All dump functions use '|| true' to suppress errors and continue"
  implication: "Script continues even when critical failures occur"

- timestamp: 2026-02-03T00:05:00+08:00
  checked: "Lines 344-348 - exit code logic"
  found: "Any error in ERRORS array causes exit 1 (includes optional file errors)"
  implication: "ROOT CAUSE for Issue 2 - Missing CRITICAL vs OPTIONAL error distinction"

- timestamp: 2026-02-03T00:05:00+08:00
  checked: "Lines 161-178 - dump_state_files()"
  found: "Adds 'status.log: NOT FOUND' as error (line 176)"
  implication: "This is OPTIONAL - file may not exist in all setups"

- timestamp: 2026-02-03T00:05:00+08:00
  checked: "Lines 181-198 - dump_locks()"
  found: "Adds 'locks: NOT FOUND' as error (line 196)"
  implication: "This is OPTIONAL - locks dir may not exist in all setups"

- timestamp: 2026-02-03T18:25:00+08:00
  checked: "Test with non-existent session"
  found: "Script exits 1 with clear error message: 'Error: Session 'NONEEXISTENT' not found. Cannot create snapshot.'"
  implication: "Issue 1 FIXED - Session not found now exits non-zero"

- timestamp: 2026-02-03T18:29:00+08:00
  checked: "Test with valid session but missing optional files"
  found: "Script exits 0, summary shows 'Errors: 0', status.log and locks/list.txt show 'NOT FOUND' without adding errors"
  implication: "Issue 2 FIXED - Optional files missing don't cause exit 1"

## Eliminated
- []

## Resolution
root_cause: |
  1. Issue 1: Line 317-319 only shows warning when session not found, doesn't exit with code 1
  2. Issue 2: Lines 344-348 treat all errors equally - missing status.log, locks, and session all cause exit 1

fix: |
  1. Session not found (lines 317-319):
     - Changed to `exit 1` with clear message
     - generate_summary called before exit to create summary file

  2. Exit code logic (lines 344-348):
     - Changed to always exit 0
     - Critical errors (session not found) exit earlier at line 320

  3. Updated dump_state_files() and dump_locks():
     - Removed add_error calls when files/dirs don't exist (they're optional)
     - Just create the "NOT FOUND" marker files without adding errors

verification: |
  Verified with tests:
  1. `./swarm_snapshot.sh --session NONEEXISTENT` - Exit code: 1 (FIXED)
  2. `./swarm_snapshot.sh --session test23` - Exit code: 0 (FIXED)
  3. Summary shows "Errors: 0" even when status.log and locks are missing

files_changed:
  - /home/user/projects/AAA/swarm/scripts/swarm_snapshot.sh
