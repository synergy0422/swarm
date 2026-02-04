# Debug: Test Rewriting for AutoRescuer API Change

**Created:** 2026-02-04
**Status:** RESOLVED

**Fix Applied:** 2026-02-04

## Problem

Tests reference removed classes:
- `WaitPatternDetector`
- `PatternCategory`
- `WaitPattern`
- `BLACKLIST_KEYWORDS`
- `DETECTION_LINE_COUNT`
- `DETECTION_TIME_WINDOW`

These were removed during v1.86/v1.87 AutoRescuer refactoring.

## New API

```python
# Main class
AutoRescuer(tmux_manager=None, cooling_time=None, broadcaster=None, dry_run=None)

# Main method
AutoRescuer.check_and_rescue(pane_output, window_name, session_name)
# Returns: (should_rescue: bool, action: str, pattern: str)

# Pattern constants (module-level)
AUTO_ENTER_PATTERNS
MANUAL_CONFIRM_PATTERNS
DANGEROUS_PATTERNS

# Actions
'auto_enter'           # Pattern matched, rescue executed
'manual_confirm_needed'  # Manual confirmation required
'dangerous_blocked'    # Dangerous pattern detected
'none'                  # No pattern matched
'cooldown'              # In cooldown period
'disabled'              # Auto-rescue disabled
'blocked_by_config'     # Blocked by config
'allowlist_missed'      # Not matching allowlist
```

## Affected Files

| File | Lines | Issue |
|------|-------|-------|
| tests/test_auto_rescuer.py | 348 | Imports removed classes |
| tests/test_auto_rescuer_patterns.py | 479 | Imports removed classes |
| tests/test_e2e_auto_rescue.py | 125 | Imports removed classes |

## Test Coverage Needed

1. **Pattern Detection Tests**
   - AUTO_ENTER_PATTERNS: Press Enter variants, Chinese patterns
   - MANUAL_CONFIRM_PATTERNS: y/n, confirm, continue
   - DANGEROUS_PATTERNS: rm -rf, DROP, etc.

2. **AutoRescuer Integration Tests**
   - check_and_rescue() returns correct (action, pattern)
   - Cooldown mechanism
   - Config-based evaluation (ENABLED, ALLOW, BLOCK)
   - Statistics tracking

3. **E2E Tests**
   - Full workflow with mock tmux_manager

## Proposed Approach

Rewrite tests to use new API:

```python
# Old
from swarm.auto_rescuer import WaitPatternDetector, PatternCategory
detector = WaitPatternDetector()
pattern = detector.detect(output, threshold)
assert pattern.category == PatternCategory.INTERACTIVE_CONFIRM

# New
from swarm.auto_rescuer import AutoRescuer, AUTO_ENTER_PATTERNS
rescuer = AutoRescuer()
should_rescue, action, pattern = rescuer.check_and_rescue(output, 'test', 'session')
assert action == 'manual_confirm_needed'
```

## Fix Plan

1. Rewrite `test_auto_rescuer.py` to test `AutoRescuer` directly
2. Rewrite `test_auto_rescuer_patterns.py` to test module-level pattern constants
3. Update `test_e2e_auto_rescue.py` to use new API
4. Run pytest to verify

---
