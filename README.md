# AI Swarm - Multi-Agent Task Processing System

A distributed multi-agent system where a Master coordinates multiple Worker nodes to process tasks in parallel using Anthropic's Claude API.

## Features

- **Parallel Task Processing**: Multiple workers process tasks concurrently
- **Tmux Integration**: Visual session management with real-time output
- **Fault Tolerance**: Automatic worker rescuing and wait state detection
- **Task Locking**: Prevents duplicate task execution across workers
- **Cost Tracking**: Built-in token usage and cost calculation

## Usage

```bash
# Initialize swarm environment
swarm init

# Launch cluster (master + 3 workers)
swarm up

# Attach to tmux session
tmux attach -t swarm-default

# Check status
swarm status

# Stop cluster
swarm down
```

## Requirements

- Python 3.8+
- tmux
- libtmux (`pip install libtmux`)
- ANTHROPIC_API_KEY or LLM_BASE_URL environment variable

## Installation

```bash
# Install from source
pip install -e .

# Or install dependencies manually
pip install requests libtmux
```

## Configuration

Set environment variables **before** running swarm commands:

```bash
# Option 1: Direct Anthropic API
export ANTHROPIC_API_KEY="sk-ant-..."

# Option 2: Local proxy (cc-switch or similar)
export LLM_BASE_URL="http://127.0.0.1:15721"
export ANTHROPIC_API_KEY="dummy"  # Optional placeholder

# Optional: Custom swarm directory
export AI_SWARM_DIR="/path/to/swarm/dir"

# Optional: Poll interval for master (default: 1.0)
export AI_SWARM_POLL_INTERVAL="1.0"
```

**Note:** LLM_BASE_URL is inherited by tmux worker windows. Make sure to export it in the same shell before running `swarm up`.

## Commands

### `swarm init`
Initialize swarm environment, check dependencies, and create directory structure.

### `swarm up [--workers N] [--cluster-id ID]`
Launch tmux session with master + N workers (default: 3 workers).

### `swarm master [--cluster-id ID]`
Launch only the master process (for debugging).

### `swarm worker --id N [--cluster-id ID]`
Launch a single worker with specified ID (for debugging).

### `swarm status [--cluster-id ID]`
Display tmux session and agent status.

### `swarm down [--cluster-id ID]`
Terminate swarm tmux session.

## Architecture

```
┌─────────────────────────────────────┐
│         Tmux Session                │
│  ┌──────────┬──────────┬──────────┐ │
│  │  Master  │ Worker-1 │ Worker-2 │ │
│  │          │          │          │ │
│  │  - Scan  │  - Poll  │  - Poll  │ │
│  │  - Assign│  - Task  │  - Task  │ │
│  │  - Rescue│  - API   │  - API   │ │
│  └──────────┴──────────┴──────────┘ │
│         ↓        ↓         ↓        │
│  ┌──────────────────────────────┐  │
│  │     Shared Filesystem       │  │
│  │  - status.log (JSON Lines)  │  │
│  │  - tasks.json                │  │
│  │  - locks/*.lock              │  │
│  │  - results/*.md              │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Development

```bash
# Run tests
pytest

# Check test coverage
pytest --cov=swarm --cov-report=html

# Lint
flake8 swarm/
```

## Maintenance Guide

Complete maintenance documentation available at [docs/MAINTENANCE.md](docs/MAINTENANCE.md):

- Environment recovery procedures
- Troubleshooting guide
- Emergency procedures (5-step recovery)
- Maintenance checklist

## Script Index

All script documentation available at [docs/SCRIPTS.md](docs/SCRIPTS.md):

- Configuration scripts (_config.sh, _common.sh)
- Communication scripts (claude_comm.sh, claude_poll.sh, claude_status.sh, claude_auto_rescue.sh)
- Task management scripts (swarm_task_wrap.sh, swarm_lock.sh, swarm_broadcast.sh)
- System tools (swarm_selfcheck.sh)
- Utility scripts (swarm_status_log.sh)

## Command Mapping

Note: `claude status` is a Claude CLI command, not a swarm command. Swarm commands use `swarm <verb>` format.

| Command | Script File | Description |
|---------|-------------|-------------|
| `claude status` | `claude_status.sh` | Quick status check for all windows |
| `swarm task-wrap` | `swarm_task_wrap.sh` | Task lifecycle wrapper |
| `swarm selfcheck` | `swarm_selfcheck.sh` | System health check |
| `swarm lock` | `swarm_lock.sh` | Task lock operations |
| `swarm broadcast` | `swarm_broadcast.sh` | Status broadcasting |
| `swarm rescue` | `claude_auto_rescue.sh` | Auto-confirm prompts |

## Changelog

Version history available at [CHANGELOG.md](CHANGELOG.md).

## License

MIT License - See LICENSE file for details.
