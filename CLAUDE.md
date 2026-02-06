# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Swarm is a multi-agent task processing system where a Master node coordinates multiple Worker nodes running in tmux panes. Workers process tasks in parallel using Anthropic's Claude API.

## Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_task_lock.py -v

# Run with coverage
pytest --cov=swarm --cov-report=html

# Lint
flake8 swarm/ tests/

# Run single test
pytest tests/test_task_queue.py::TestTaskQueue::test_add_task -v

# E2E test with cc-switch proxy
export LLM_BASE_URL="http://127.0.0.1:15721/v1/messages"
export ANTHROPIC_API_KEY="dummy"
python3 scripts/swarm_e2e_ccswitch_test.py
```

## Architecture

### Core Components

```
swarm/
├── master.py          # Master coordination loop (status scan, task dispatch, auto-rescue)
├── worker_smart.py    # Worker with Claude API integration
├── cli.py             # CLI entry point (swarm init/up/master/worker/status/down)
├── task_queue.py     # tasks.json persistence and task state management
├── task_lock.py       # Atomic task locking to prevent duplicate execution
├── fifo_input.py     # FIFO channel for task dispatch
├── claude_bridge.py   # Monitor master window, parse /task commands, write to FIFO
├── auto_rescuer.py   # Detect and auto-confirm interactive prompts
├── status_broadcaster.py  # Unified JSONL logging to status.log
├── master_scanner.py  # Read worker states from status.log
├── master_dispatcher.py # Task assignment via mailbox files
└── tmux_collaboration.py  # Tmux pane capture and send-keys
```

### Shared State (Filesystem-based)

All coordination uses the shared filesystem at `$AI_SWARM_DIR` (default: `/tmp/ai_swarm`):

| File/Directory | Purpose |
|----------------|---------|
| `status.log` | JSONL: worker states (START, RUNNING, WAIT, DONE, ERROR) |
| `tasks.json` | Task queue with priorities and assignments |
| `locks/{task_id}.lock` | Atomic task locks (O_CREAT\|O_EXCL) |
| `results/{task_id}.md` | Task execution results |
| `instructions/{worker}.jsonl` | Per-worker mailbox for dispatch |
| `master_inbox` | FIFO for interactive task input |

### Data Flow

1. **Task Input**: `/task <prompt>` in master window → Bridge captures → FIFO
2. **Task Queue**: Master reads FIFO → adds to tasks.json
3. **Dispatch**: Master scans status.log → finds idle workers → writes to worker mailbox
4. **Execution**: Worker polls mailbox → acquires task lock → calls Claude API → saves result
5. **Cleanup**: Worker releases lock → updates status.log

### Master Loop (master.py:600)

```python
while running:
    # 1. Scan worker status from status.log
    workers = scanner.scan_workers()

    # 2. Handle WAIT states (auto-rescue via pane scanning)
    handle_wait_states(workers)

    # 3. Dispatch tasks to idle workers
    dispatcher.dispatch_all(worker_statuses)

    # 4. Scan panes and auto-rescue (independent interval)
    _handle_pane_wait_states()

    # 5. Output status summary (every 30s)
    output_status_summary()

    sleep(poll_interval)
```

## Key Patterns

### Status Broadcasting

Use `StatusBroadcaster` for unified logging:

```python
from swarm.status_broadcaster import StatusBroadcaster, BroadcastState

broadcaster = StatusBroadcaster(worker_id='worker-1')
broadcaster.broadcast_start(task_id='task-001', message='Starting')
broadcaster.broadcast_done(task_id='task-001', message='Completed')
broadcaster.broadcast_error(task_id='task-001', message='Failed')
```

### Task Locking

Atomic lock acquisition prevents duplicate task execution:

```python
from swarm.task_lock import TaskLockManager

lock_manager = TaskLockManager(worker_id='worker-1')
if lock_manager.acquire_lock('task-001'):
    try:
        # Do work
    finally:
        lock_manager.release_lock('task-001')
```

### Tmux Operations

Use `TmuxCollaboration` for pane operations:

```python
from swarm.tmux_collaboration import TmuxCollaboration

tmux = TmuxCollaboration()
contents = tmux.capture_all_windows('swarm-default')
tmux.send_keys('worker-0', 'Enter')  # Literal mode
```

### Interactive Mode (FIFO)

Master reads from FIFO for task input:

```bash
export AI_SWARM_INTERACTIVE=1
python3 -m swarm.cli master
```

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Claude API key | Required (unless using proxy) |
| `LLM_BASE_URL` | Proxy endpoint | - |
| `AI_SWARM_DIR` | State directory | `/tmp/ai_swarm` |
| `AI_SWARM_POLL_INTERVAL` | Master scan interval | 1.0s |
| `AI_SWARM_INTERACTIVE` | Enable FIFO input | 0 |
| `AI_SWARM_BRIDGE_PANE` | tmux pane for Bridge | - |
| `AI_SWARM_BRIDGE_WORKER_PANES` | Worker panes for dispatch | - |

## Bridge Configuration (Important)

**Bridge monitors the Master Claude Code pane, NOT the master process pane.**

```
Claude Code window (input /task here) ──capture-pane──▶ Bridge ──▶ FIFO
                                              │
                                              ▼ send-keys
                                    Master Claude Code confirms dispatch
```

Set `AI_SWARM_BRIDGE_PANE` to the pane running Claude Code (where you type `/task`).
