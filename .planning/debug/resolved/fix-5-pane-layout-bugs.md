---
status: resolved
trigger: fix-5-pane-layout-bugs
created: 2026-02-03T10:00:00+00:00
updated: 2026-02-03T10:01:00+00:00
---

## Current Focus

hypothesis: Issue 1: split-window -v -l creates NEW pane BELOW, so -l sets height of NEW pane (codex), not master. Current codex height = LEFT_HEIGHT (wrong), should = WIN_HEIGHT - LEFT_HEIGHT. Issue 2: WORKER_HEIGHT calculation - actually might be correct since horizontal split preserves height.
test: Analyze tmux split-window -v -l semantics and verify pane height calculations
expecting: Issue 1 confirmed - need to invert the -l value. Issue 2 needs verification - horizontal split preserves full height.
next_action: Apply fixes based on analysis

## Evidence

- timestamp: 2026-02-03T10:00:00+00:00
  checked: "scripts/swarm_layout_5.sh lines 147-154"
  found: |
    Line 147: RIGHT_PANE=$(tmux split-window -h ...) - horizontal split, preserves full window height
    Line 150: WORKER1_PANE=$(tmux split-window -v -l "$WORKER_HEIGHT" ...) - uses WIN_HEIGHT / 3
    Line 154: CODEX_PANE=$(tmux split-window -v -l "$LEFT_HEIGHT" ...) - sets codex height = LEFT_HEIGHT
  implication: |
    Issue 1: -v split creates pane BELOW, -l sets NEW pane size. Code sets codex height = LEFT_HEIGHT,
    but LEFT_HEIGHT is calculated as master height (WIN_HEIGHT * LEFT_RATIO / 100).
    FIX: codex height should be WIN_HEIGHT - LEFT_HEIGHT.

    Issue 2: Horizontal split (-h) preserves original pane height. RIGHT_PANE has full WIN_HEIGHT.
    So WORKER_HEIGHT = WIN_HEIGHT / 3 is actually correct. But we can still improve by using
    RIGHT_PANE_HEIGHT dynamically to handle edge cases.

## Symptoms

expected: "5-pane layout works correctly with proper pane sizing"
actual: "Two bugs in pane sizing logic"
errors: "N/A - logical bugs, not errors"
reproduction: "Run scripts/swarm_layout_5.sh and observe incorrect pane sizes"
started: "Always broken - never worked correctly"

## Eliminated

## Evidence

## Resolution

root_cause: "Issue 1: split-window -v creates pane BELOW target pane, and -l sets the NEW pane's height. Code used LEFT_HEIGHT (master target height) for codex size, but codex should get remaining height = WIN_HEIGHT - LEFT_HEIGHT. Issue 2: Analysis shows horizontal split (-h) preserves full window height, so WIN_HEIGHT / 3 is actually correct for WORKER_HEIGHT."
fix: "Issue 1: Changed line 154 from `-l \"$LEFT_HEIGHT\"` to `-l \"$((WIN_HEIGHT - LEFT_HEIGHT))\"`. Issue 2: No change needed - horizontal split preserves full height, so WORKER_HEIGHT calculation is correct."
verification: "Review code changes to confirm fix is correct"
files_changed: ["scripts/swarm_layout_5.sh"]
