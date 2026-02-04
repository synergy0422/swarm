# Quick Task 001 Summary: Test Mode for Swarm Task

## Objective

Add test mode and safe execution to `swarm task run`.

## Changes Made

### 1. swarm/cli.py

**Changes:**
- Added `--dry-run` flag preprocessing in `main()` function
- Modified `cmd_task()` to preserve `dry_run` flag when parsing subcommand arguments
- Updated `cmd_task_run()` to handle dry-run mode
- Fixed argument parsing to support commands with flags (e.g., `rm -rf`)

**Key modifications:**
- Pre-parse `--dry-run` flag before argparse processes arguments
- Pass `dry_run` flag through nested argument parsing
- Manual parsing of `run` subcommand to handle flag arguments

### 2. scripts/swarm_task_wrap.sh

**Changes:**
- Added `DRY_RUN` global variable
- Added `DANGEROUS_PATTERNS` array for safety detection
- Added `is_command_safe()` function to check for dangerous commands
- Added `warn_dangerous()` function to log warnings
- Updated `usage()` with `--dry-run` documentation
- Modified `cmd_run()` to support dry-run mode and dangerous command detection
- Added `--dry-run` option parsing in `main()`

**Dangerous patterns detected:**
- `rm -rf`
- `dd if=/dev`
- `mkfs`
- `shred`
- `format`
- `:(){:|:&}` (fork bomb)
- `>$`
- `dd of=/dev`

## Verification

### Dry-run mode tests:
```
$ python3 -m swarm.cli task run --dry-run test-worker-0 worker-0 echo hello
[DRY-RUN] Would execute: echo hello
[DRY-RUN] Task: test-worker-0 on worker-0

$ python3 -m swarm.cli task run --dry-run test-worker-0 worker-0 rm -rf /tmp/test
[DRY-RUN] Would execute: rm -rf /tmp/test
[DRY-RUN] Task: test-worker-0 on worker-0
```

### Dangerous command warnings:
```
$ scripts/swarm_task_wrap.sh --dry-run run test-worker-0 worker-0 rm -rf /tmp/test
[WARN] DANGEROUS COMMAND DETECTED: contains 'rm -rf'
[WARN] Command: rm -rf /tmp/test
[WARN] This command may cause data loss or system damage!
[INFO] [DRY-RUN] Would execute: rm -rf /tmp/test
```

### Normal execution preserved:
```
$ python3 -m swarm.cli task run test-worker-0 worker-0 echo hello
hello
[INFO] Task test-worker-0 completed
```

## Files Modified

| File | Changes |
|------|---------|
| `swarm/cli.py` | Added --dry-run flag support, fixed argument parsing |
| `scripts/swarm_task_wrap.sh` | Added --dry-run, dangerous command detection |

## Exit Codes

- `--dry-run` mode: Always returns 0 (no execution)
- Normal mode: Returns command's exit code

## Notes

- `--dry-run` must come after `run` subcommand: `swarm task run --dry-run <task_id> <worker> <command...>`
- Dangerous commands are flagged with warnings but still executed in normal mode (for flexibility)
- Wrap script's `--dry-run` works independently of CLI flag
