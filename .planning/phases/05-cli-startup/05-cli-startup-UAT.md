---
status: diagnosed
phase: 05-cli-startup
source: 05-01-SUMMARY.md
started: 2026-01-31T14:15:42Z
updated: 2026-01-31T14:20:00Z
---

## Current Test

[testing complete - see results below]

## Tests

### 1. CLI commands exist and work
expected: All 6 commands (init, up, master, worker, status, down) should work
result: pass

### 2. Configuration priority (flags > env > defaults)
expected: CLI flags should override environment variables and defaults for --cluster-id
result: issue
reported: "--cluster-id 作为全局参数只能在子命令前使用；用户常见写法 swarm status --cluster-id default 报错 'unrecognized arguments'。flags 优先级要求无法在常见用法下成立。"
severity: major
root_cause: "argparse global flag only defined before subcommand routing, not within individual subcommand parsers"
missing:
  - "Use argparse parents feature to add --cluster-id to all subparsers (init除外)"
  - "Implement priority logic: flags > env > defaults"
debug_session: ".planning/debug/cluster-id-flag-position.md"

### 3. Python module import warning
expected: No RuntimeWarning when running python -m swarm.cli
result: issue
reported: "RuntimeWarning: swarm.cli found in sys.modules after import"
severity: minor
root_cause: "swarm/__init__.py line 32 eagerly imports cli module"
missing:
  - "Remove 'from swarm import cli' from line 32"
  - "Remove 'cli' from __all__ list"
debug_session: ".planning/debug/runtime-warning-cli-import.md"

## Summary

total: 3
passed: 1
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "CLI flags override environment variables for --cluster-id"
  status: failed
  reason: "swarm status --cluster-id default fails with unrecognized arguments"
  severity: major
  test: 2
  root_cause: argparse global flag only works before subcommand
  artifacts:
    - path: "swarm/cli.py"
      issue: "Global --cluster-id only defined before subcommand routing"
  missing:
    - Use argparse parents to add --cluster-id to all subparsers (except init)
    - Implement priority: flags > env > defaults
  debug_session: ".planning/debug/cluster-id-flag-position.md"

- truth: "No RuntimeWarning when running python -m swarm.cli"
  status: failed
  reason: swarm.cli found in sys.modules after import
  severity: minor
  test: 3
  root_cause: swarm/__init__.py eagerly imports cli module
  artifacts:
    - path: "swarm/__init__.py"
      issue: "Line 32 imports cli module eagerly"
  missing:
    - Remove 'from swarm import cli' from swarm/__init__.py
    - Remove 'cli' from __all__ exports
  debug_session: ".planning/debug/runtime-warning-cli-import.md"
