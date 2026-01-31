---
phase: 05-cli-startup
plan: "02"
subsystem: cli
tags: [argparse, cli, flags]

# Dependency graph
requires:
  - phase: 05-cli-startup
    provides: Initial CLI structure with argparse-based command routing
provides:
  - --cluster-id flag available after subcommands (e.g., swarm status --cluster-id default)
affects: [05-cli-startup]

# Tech tracking
tech-stack:
  added: []
  patterns: [argparse parents pattern for shared subparser arguments]

key-files:
  created: []
  modified: [swarm/cli.py]

key-decisions:
  - "Used argparse parents pattern to share --cluster-id across subparsers"
  - "Excluded 'init' command from --cluster-id (cluster not relevant for environment initialization)"

patterns-established:
  - "Parent parser pattern: shared arguments via parents=[parent_parser]"

# Metrics
duration: 2min
completed: 2026-01-31
---

# Phase 5 Plan 2: --cluster-id Flag Position Fix Summary

**argparse parents pattern for --cluster-id flag availability after subcommands**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-31T06:22:31Z
- **Completed:** 2026-01-31T06:24:33Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Moved --cluster-id from main parser to parent parser
- Added parent parser to up, master, worker, status, down subparsers
- Kept init command without --cluster-id (cluster not relevant for environment init)

## Task Commits

1. **Task 1: Add --cluster-id to subparsers using argparse parents pattern** - `e6180df` (feat)

## Files Modified
- `swarm/cli.py` - Refactored argparse structure with parent parser pattern

## Decisions Made
- Used argparse parents pattern instead of custom argparse handling
- Excluded 'init' subcommand from --cluster-id (creates environment before cluster concept exists)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## Verification Results

```
$ python3 -m swarm.cli status --cluster-id default
[SWARM] No swarm session running: swarm-default

$ python3 -m swarm.cli status --cluster-id=default
[SWARM] No swarm session running: swarm-default

$ python3 -m swarm.cli down --cluster-id test
[SWARM] No swarm session running: swarm-test

$ python3 -m swarm.cli status --help
usage: cli.py status [-h] [--cluster-id CLUSTER_ID]
  --cluster-id CLUSTER_ID  Cluster identifier (default: default)
```

All commands execute without "unrecognized arguments" error.

## Next Phase Readiness
- CLI flag position issue resolved
- Ready for Phase 6 integration testing

---
*Phase: 05-cli-startup*
*Completed: 2026-01-31*
