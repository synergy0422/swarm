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

## License

MIT License - See LICENSE file for details.
