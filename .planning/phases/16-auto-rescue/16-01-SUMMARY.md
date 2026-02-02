---
phase: 16
plan: 1
subsystem: automation
tags:
  - bash
  - tmux
  - auto-rescue
  - prompt-detection
  - worker-automation
---

# Phase 16 Plan 1: Auto-Rescue Script Summary

## One-liner

Auto-confirmation script for Claude agent prompts with 30s cooldown, dangerous command blacklist, and worker-only enforcement.

## Objective

Create `scripts/claude_auto_rescue.sh` that automatically detects confirmation prompts in tmux worker windows and sends Enter, while blocking dangerous commands and enforcing cooldown periods.

## Context Files

- `scripts/_common.sh` - Shared configuration and logging functions

## Implementation Details

### Pattern Categories

**Dangerous Commands (Priority 1 - Block Auto-Rescue):**
- `rm -rf`, `rm -r`, `rm -f`
- `del`, `delete`, `drop`, `DROP`
- `truncate`, `sudo`, `password`, `passwd`

**Standard Prompts (Priority 2 - Auto-Confirm):**
- `[y/n]`, `[Y/n]`, `[y/N]`
- `press enter`, `press return`, `hit enter`
- `回车继续`, `按回车` (Chinese localization)

**Confirmation Words (Priority 3 - Auto-Confirm):**
- `confirm`, `continue`, `proceed`
- `yes` (with boundary checks)

### Key Functions

| Function | Purpose |
|----------|---------|
| `is_worker_window()` | Validates window is worker-0/1/2 (master excluded) |
| `check_cooldown()` | Enforces 30s minimum between actions per window |
| `detect_dangerous()` | Scans for dangerous command patterns |
| `detect_prompt()` | Scans for confirmation prompt patterns |
| `cmd_check()` | One-time check and auto-confirm |
| `cmd_run()` | Continuous monitoring loop (2s poll) |
| `cmd_status()` | Display last action timestamps |

### Cooldown Tracking

- Files: `${SWARM_STATE_DIR}/.auto_rescue_last_action_${window}`
- 30-second minimum between auto-confirm actions per window
- Prevents repeated Enter key sends

### Worker-Only Restriction

Only worker-0, worker-1, and worker-2 windows are affected:
- Master window is explicitly excluded
- Invalid window names are rejected
- Clear logging when windows are skipped

## Decisions Made

| Decision | Rationale | Status |
|----------|-----------|--------|
| Removed done/ready/ok patterns | Too broad, caused false positives | Implemented |
| Case-insensitive pattern matching | Handles varied capitalization | Implemented |
| Dangerous patterns checked first | Safety over convenience | Implemented |
| Chinese localization included | Multi-language support | Implemented |

## Key Files Created

- `scripts/claude_auto_rescue.sh` - Main auto-rescue script (7KB)

## Verification Results

| Test | Status |
|------|--------|
| Script exists and executable | PASS |
| Sources _common.sh | PASS |
| Pattern detection ([y/n], press enter) | PASS |
| Confirmation words (confirm, continue, proceed) | PASS |
| Cooldown logic (30s enforcement) | PASS |
| Dangerous pattern blocking (rm -rf, DROP) | PASS |
| Worker-only restriction (master excluded) | PASS |
| check command | PASS |
| run command | PASS |
| status command | PASS |

## Deviations from Plan

None - plan executed exactly as written.

## Authentication Gates

None - no authentication required for this script.

## Metrics

| Metric | Value |
|--------|-------|
| Duration | 176 seconds |
| Files created | 1 |
| Lines of code | ~300 |
| Test cases passed | 100% |

## Next Phase Readiness

Phase 16 complete. Ready for Phase 17 (Status Broadcast) or continue with additional Auto-Rescue plans if needed.
