---
status: resolved
trigger: "selfcheck-script-errors"
created: 2026-02-02T23:45:00Z
updated: 2026-02-02T23:58:00Z
---

## Current Focus
hypothesis: Fixes applied and verified
test: Run selfcheck script with -v flag and test with non-existent state directory
expecting: All 9 scripts discovered, no files created during health check
next_action: Archive session after final verification

## Symptoms
expected: Self-check script should validate existing scripts and not modify system state
actual:
  1. CORE_SCRIPTS array contains non-existent scripts (sworm-start.sh, sworm-stop.sh, worker.sh)
  2. check_state_dir() creates locks/ directory and status.log file, modifying system state
errors: Script will report failures for non-existent scripts, and creates/modify files during "read-only" health check
reproduction: Run ./scripts/swarm_selfcheck.sh and check CORE_SCRIPTS array and check_state_dir function
started: Script was just created in Phase 20-01 (commit 5174d9c, 39b3e08, 688d5a3)

## Evidence

### Evidence 1: Confirmed non-existent scripts
- timestamp: 2026-02-02T23:45:00Z
- checked: Listing all .sh files in /home/user/projects/AAA/swarm/scripts/
- found: Actual scripts are:
  - claude_auto_rescue.sh
  - claude_comm.sh
  - claude_poll.sh
  - claude_status.sh
  - _common.sh
  - _config.sh
  - swarm_broadcast.sh
  - swarm_e2e_test.sh
  - swarm_lock.sh
  - swarm_selfcheck.sh
  - swarm_status_log.sh
  - swarm_task_wrap.sh
- implication: sworm-start.sh, sworm-stop.sh, worker.sh do NOT exist, but are in CORE_SCRIPTS

### Evidence 2: Typo in script names
- timestamp: 2026-02-02T23:45:00Z
- checked: CORE_SCRIPTS array lines 88-95
- found: "sworm-start.sh" and "sworm-stop.sh" have typo "sworm" instead of "swarm"
- implication: These look like typos for "swarm-start.sh" and "swarm-stop.sh"

### Evidence 3: check_state_dir creates files/directories
- timestamp: 2026-02-02T23:45:00Z
- checked: check_state_dir() function lines 185-240
- found:
  - Line 207: mkdir -p "$lock_dir" creates directory if not exists
  - Line 228: touch "$status_file" creates file if not exists
  - Line 231: rm -f "$status_file" attempts cleanup but may fail silently
- implication: Health check modifies system state, not read-only

### Evidence 5: Fix verified - all 9 scripts discovered
- timestamp: 2026-02-02T23:55:00Z
- checked: Ran ./scripts/swarm_selfcheck.sh -v
- found: Output shows "All 9 scripts are executable"
- implication: Dynamic script discovery working correctly

### Evidence 6: Fix verified - no files created
- timestamp: 2026-02-02T23:55:00Z
- checked: Set SWARM_STATE_DIR=/tmp/test_ai_swarm (non-existent) and ran selfcheck
- found: Directory does NOT exist after health check completes
- implication: check_state_dir() is now truly read-only

## Eliminated

## Resolution

root_cause:
  - Issue 1: CORE_SCRIPTS hardcoded with typos (sworm vs swarm) and non-existent scripts
  - Issue 2: check_state_dir() created directories/files with mkdir and touch, violating read-only health check principle
fix:
  - Issue 1: Changed CORE_SCRIPTS from hardcoded array to dynamic discovery using find command, excluding config and selfcheck scripts
  - Issue 2: Removed mkdir -p and touch commands, now only checks if directories/files exist and are writable, reports info for non-existent items
verification:
  - All 9 scripts now discovered correctly
  - No files or directories created when state directory doesn't exist
  - All health checks pass in normal environment
files_changed:
  - /home/user/projects/AAA/swarm/scripts/swarm_selfcheck.sh
