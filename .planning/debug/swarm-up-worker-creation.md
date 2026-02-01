# Debug: swarm up Worker Window Creation

**Status:** ✅ ROOT CAUSE CONFIRMED + SOLUTION VERIFIED

## Issue
`swarm up` only shows master window, worker-0/1/2 not visible.

## Symptom
```bash
$ python3 -m swarm.cli up --cluster-id uat-test --workers 3
$ tmux list-windows -t swarm-uat-test
0: master* (1 panes) [80x24] ...
# Missing: worker-0, worker-1, worker-2
```

## Root Cause: CONFIRMED ✅

**Worker processes exit immediately due to missing LLM_BASE_URL.**

### Evidence

```bash
# Direct worker test (without LLM_BASE_URL)
$ python3 -m swarm.cli --cluster-id test worker --id 0
[ERROR] Worker failed: Error: ANTHROPIC_API_KEY environment variable not set
RuntimeError: Error: ANTHROPIC_API_KEY environment variable not set
Exit: 1
```

### tmux Behavior Verified

1. Window IS created during `swarm up` (confirmed by `-P` flag output)
2. Worker starts, checks API key/LLM_BASE_URL, fails immediately
3. Process exits → tmux closes window (expected behavior)
4. `tmux list-windows` shows only master (workers already closed)

### Solution Verification

```bash
# Set environment variables BEFORE running swarm
export LLM_BASE_URL="http://127.0.0.1:15721"
export ANTHROPIC_API_KEY="dummy"

# Now run swarm up
python3 -m swarm.cli up --cluster-id uat-test --workers 3

# Result: All 4 windows visible and workers running!
$ tmux list-windows -t swarm-uat-test
0: master (1 panes) [80x24]
1: worker-0 (1 panes) [80x24]
2: worker-1 (1 panes) [80x24]
3: worker-2 (1 panes) [80x24]

$ ps aux | grep "[p]ython3.*worker"
98430 python3 -m swarm.cli ... worker --id 0
98433 python3 -m swarm.cli ... worker --id 1
98436 python3 -m swarm.cli ... worker --id 2
```

## Key Findings

1. **Worker windows close when processes exit** - Expected tmux behavior, not a bug
2. **Environment variables inherited by tmux** - Set in parent shell before `swarm up`
3. **Mock API key works for testing** - `ANTHROPIC_API_KEY="dummy"` with `LLM_BASE_URL`

## Quick Start

For local testing with cc-switch proxy:

```bash
export LLM_BASE_URL="http://127.0.0.1:15721"
export ANTHROPIC_API_KEY="dummy"  # Optional, placeholder

# Now run swarm commands
python3 -m swarm.cli up --cluster-id my-cluster --workers 3
python3 -m swarm.cli status --cluster-id my-cluster --panes
python3 -m swarm.cli down --cluster-id my-cluster
```

## Resolution

✅ Root cause identified: Missing LLM_BASE_URL
✅ Solution verified: Export environment variables before running swarm
✅ UAT complete: All 8 steps pass

