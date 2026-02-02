# Phase 20-01 Summary: System Self-Check Script

**Date:** 2026-02-02
**Status:** ✅ Complete
**Commits:** 3

---

## Tasks Completed

### Task 1: Core Script Structure
**Commit:** `5174d9c` - feat(20-01): create swarm_selfcheck.sh with core structure

Created `scripts/swarm_selfcheck.sh` with:
- Shebang (`#!/bin/bash`) with `set -euo pipefail` for error handling
- Local `SCRIPT_DIR` definition (handles symlinks and bash -c edge case)
- Source `_common.sh` for `SWARM_STATE_DIR` configuration
- Output control functions:
  - `print_pass()` - suppressed in quiet mode
  - `print_fail()` - always shown (even in quiet mode)
  - `print_info()` - only in verbose mode
- Command-line argument parsing:
  - `-v|--verbose` - detailed output
  - `-q|--quiet` - failures only
  - `-h|--help` - usage information
- `CORE_SCRIPTS` array with all .sh scripts
- `CONFIG_FILES` array with _config.sh and _common.sh

**Verification:**
- ✅ Script executable: `-rwxr-xr-x`
- ✅ `./scripts/swarm_selfcheck.sh --help` displays usage
- ✅ SCRIPT_DIR defined locally (not from _common.sh)

---

### Task 2: Check Functions
**Commit:** `39b3e08` - feat(20-01): implement check functions for tmux, scripts, and config

Added four check functions:

1. **`check_tmux()`**
   - Uses `command -v tmux` to detect installation
   - Captures version with `tmux -V`
   - Reports `[PASS] tmux is installed (tmux X.Y)`
   - Suggests install command if missing
   - Returns 1 on failure (sets FAILED=1)

2. **`check_scripts()`**
   - Iterates through CORE_SCRIPTS array
   - Skips swarm_selfcheck.sh itself
   - Checks execute bit with `[[ -x "$script" ]]`
   - Reports `[PASS] All N scripts are executable`
   - Lists failed scripts if any
   - Suggests `chmod +x scripts/<script_name>`

3. **`check_config()`**
   - Validates `_config.sh` readability
   - Validates `_common.sh` readability
   - Checks `SWARM_STATE_DIR` is set
   - Uses `print_pass`/`print_fail` for each check
   - Suggests fixes for each failure type

4. **`check_state_dir()`**
   - Checks `$SWARM_STATE_DIR/locks` can be created (mkdir -p test)
   - Checks `$SWARM_STATE_DIR/status.log` can be written (touch test)
   - Cleans up test files after check
   - Reports specific permission issues
   - Suggests fixes (chmod, mkdir)

**Verification:**
- ✅ All four check functions exist
- ✅ Functions use print_pass/print_fail/print_info
- ✅ Functions respect QUIET/VERBOSE modes

---

### Task 3: Main Runner and Exit Codes
**Commit:** `688d5a3` - feat(20-01): implement main check runner with exit codes

Added `main()` function that:
- Initializes `FAILED=0` global
- Prints header (skipped in quiet mode)
- Calls each check function in sequence:
  - `check_tmux || FAILED=1`
  - `check_scripts || FAILED=1`
  - `check_config || FAILED=1`
  - `check_state_dir || FAILED=1`
- Prints summary (skipped in quiet mode):
  - "All checks passed [OK]" if FAILED=0
  - "One or more checks failed [FAIL]" if FAILED=1
- Returns exit code 0 on success, 1 on failure

**Design Decision:** Removed duplicate `SWARM_STATE_DIR` existence check from `check_config()` to avoid redundant failures (state_dir check handles creation).

**Verification:**
- ✅ `main()` function exists
- ✅ `./scripts/swarm_selfcheck.sh` exits with code 0 on success
- ✅ `./scripts/swarm_selfcheck.sh` exits with code 1 on failure
- ✅ Verbose mode shows detailed output (`-v`)
- ✅ Quiet mode suppresses pass messages (`-q`)
- ✅ Help mode displays usage (`--help`)

---

## Files Modified

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/swarm_selfcheck.sh` | 280 | System health validation for tmux, scripts, and config |

---

## What Was Created

### Script Structure

**Shebang and Error Handling:**
```bash
#!/bin/bash
set -euo pipefail
```

**Local SCRIPT_DIR:**
```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
```

**Source _common.sh:**
```bash
source "$SCRIPT_DIR/_common.sh"
```

**Output Control Functions:**
- `print_pass()` - suppressed in `-q` mode
- `print_fail()` - always shown
- `print_info()` - only in `-v` mode

### Check Functions

1. **tmux availability** - Detects if tmux is installed and reports version
2. **Script executability** - Validates all .sh scripts have execute bit
3. **Configuration files** - Checks _config.sh and _common.sh are readable
4. **State directory** - Verifies SWARM_STATE_DIR structure and permissions

### Main Execution

```bash
main() {
    local FAILED=0

    # Run all checks
    check_tmux || FAILED=1
    check_scripts || FAILED=1
    check_config || FAILED=1
    check_state_dir || FAILED=1

    # Return exit code
    return $FAILED
}
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Local SCRIPT_DIR definition | _common.sh unsets SCRIPT_DIR after sourcing _config.sh, so we define it locally |
| print_fail always shown | Critical failures should never be suppressed, even in quiet mode |
| print_info only in verbose mode | Diagnostic details should be opt-in |
| Exit code 0 on success, 1 on failure | Enables CI/CD pipelines to fail on health check failures |
| Remove duplicate state_dir check from check_config | Avoid redundant failures - check_state_dir handles creation |
| All output to stderr (>&2) | Avoids interfering with data streams |

---

## Verification Results

### Manual Testing

✅ **Normal mode:**
```
AI Swarm System Health Check
==============================

[PASS] tmux is installed (tmux 3.4)
[PASS] All 3 scripts are executable
[PASS] _config.sh is readable
[PASS] _common.sh is readable
[PASS] SWARM_STATE_DIR is set (/tmp/ai_swarm)
[PASS] Locks directory is writable (/tmp/ai_swarm/locks)
[PASS] Status log created (/tmp/ai_swarm/status.log)

=== Summary ===
All checks passed [OK]
```

✅ **Verbose mode (`-v`):** Shows `[INFO]` messages for each check

✅ **Quiet mode (`-q`):** Suppresses all output when all checks pass

✅ **Help mode (`--help`):** Displays usage information

### Failure Scenarios

✅ **Non-executable script:**
```
[FAIL] The following scripts are not executable:
  - /home/user/projects/AAA/swarm/scripts/swarm_lock.sh
[INFO] Run: chmod +x scripts/<script_name>
```
Exit code: 1

✅ **Exit codes:**
- Success: `./scripts/swarm_selfcheck.sh; echo $?` outputs `0`
- Failure: Simulated failure outputs `1`

### Output Clarity

✅ **Pass/fail status:** Clearly indicated with `[PASS]`/`[FAIL]` prefixes

✅ **Fix suggestions:** Actionable and specific:
- "Install tmux: apt install tmux | brew install tmux"
- "Run: chmod +x scripts/<script_name>"
- "Fix permissions: chmod u+w $SWARM_STATE_DIR"

✅ **Verbose mode:** Provides additional detail without overwhelming output

✅ **Quiet mode:** Suppresses all but failures

---

## Deviations from Plan

**None.** All tasks completed as specified.

---

## Commits Made

| Commit | Message |
|--------|---------|
| `5174d9c` | feat(20-01): create swarm_selfcheck.sh with core structure |
| `39b3e08` | feat(20-01): implement check functions for tmux, scripts, and config |
| `688d5a3` | feat(20-01): implement main check runner with exit codes |

---

## Duration

**Start:** 2026-02-02 ~23:29
**End:** 2026-02-02 ~23:35
**Duration:** ~6 minutes

---

## Success Criteria

✅ **Script exists and is executable:**
- `scripts/swarm_selfcheck.sh` exists with `-rwxr-xr-x` permissions

✅ **All checks functional:**
- tmux availability check detects installed/missing tmux
- Script executability check validates all .sh files have execute bit
- Configuration check validates _config.sh and _common.sh are readable
- State directory check validates SWARM_STATE_DIR is writable

✅ **Clear output:**
- Pass/fail status indicated with `[PASS]`/`[FAIL]` prefixes
- Actionable fix suggestions for each failure type
- Summary line shows overall result (OK or FAIL)

✅ **Exit codes correct:**
- Exit 0 when all checks pass
- Exit 1 when any check fails

✅ **Command-line options work:**
- `--help` shows usage
- `-v|--verbose` enables detailed output
- `-q|--quiet` suppresses pass messages

---

**Phase 20-01 Status:** ✅ COMPLETE

All success criteria met. System self-check script is fully functional and ready for use.
