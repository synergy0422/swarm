# CLI Command Bug Diagnosis: run_swarm_command omits subcommand

## Issue Summary
The `run_swarm_command` helper function in the E2E test suite fails to include the `command` subcommand in the constructed CLI command, causing all swarm CLI invocations to fail.

## Root Cause Analysis

### Bug Location
**File:** `/home/user/AAA/swarm/tests/test_e2e_happy_path.py`
**Function:** `run_swarm_command` (line 50-77)
**Specific Bug:** Lines 63-66

### Current (Buggy) Code
```python
cmd = [
    sys.executable, '-m', 'swarm.cli',
    '--cluster-id', cluster_id
] + args
```

### Problem
The `command` parameter (which should be the CLI subcommand like `init`, `up`, `status`, `down`, `master`, or `worker`) is completely omitted from the command array. The command is constructed as:
```
python -m swarm.cli --cluster-id <cluster_id> <args>
```

Instead of:
```
python -m swarm.cli --cluster-id <cluster_id> <command> <args>
```

### Impact
All E2E tests that use `run_swarm_command` will fail because:
1. Line 137: `run_swarm_command(unique_cluster_id, 'init', [], isolated_swarm_dir)` - runs `python -m swarm.cli --cluster-id <id>` (missing `init`)
2. Line 175: `run_swarm_command(unique_cluster_id, 'status', [], isolated_swarm_dir)` - runs `python -m swarm.cli --cluster-id <id>` (missing `status`)
3. Line 185: `run_swarm_command(unique_cluster_id, 'down', [], isolated_swarm_dir)` - runs `python -m swarm.cli --cluster-id <id>` (missing `down`)

The swarm CLI parser expects a subcommand and will either:
- Show help and exit with code 1
- Raise an error about missing required arguments

## CLI Structure (from swarm/cli.py)

The swarm CLI uses argparse with subparsers:

```python
parser = argparse.ArgumentParser(...)
subparsers = parser.add_subparsers(dest='command', help='Available commands')

subparsers.add_parser('init', ...)
subparsers.add_parser('up', ...)
subparsers.add_parser('master', ...)
subparsers.add_parser('worker', ...)
subparsers.add_parser('status', ...)
subparsers.add_parser('down', ...)
```

The `command` argument is **required** for all operations except `init` (which doesn't use `--cluster-id`).

## Required Fix

**File:** `/home/user/AAA/swarm/tests/test_e2e_happy_path.py`
**Lines:** 63-66

### Current Code (lines 63-66)
```python
cmd = [
    sys.executable, '-m', 'swarm.cli',
    '--cluster-id', cluster_id
] + args
```

### Fixed Code
```python
cmd = [
    sys.executable, '-m', 'swarm.cli',
    '--cluster-id', cluster_id,
    command
] + args
```

### Explanation
Add `command` as a separate element in the command list after `--cluster-id` and before `args`. This ensures the subcommand is properly included in the CLI invocation.

## Files Requiring Modification

| File | Change Type | Description |
|------|-------------|-------------|
| `/home/user/AAA/swarm/tests/test_e2e_happy_path.py` | Bug fix | Add `command` to cmd list at line 65 |

## Verification

After the fix, commands should be constructed correctly:

```python
# Before fix:
# python -m swarm.cli --cluster-id test-123

# After fix:
# python -m swarm.cli --cluster-id test-123 init
# python -m swarm.cli --cluster-id test-123 status
# python -m swarm.cli --cluster-id test-123 down
```
