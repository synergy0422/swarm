#!/usr/bin/env bash
set -euo pipefail

# AI Swarm - Claude Code CLI Multi-Window Launcher
# Creates 4 tmux windows (master, worker-0, worker-1, worker-2) each running Claude CLI
#
# Usage:
#   ./run_claude_swarm.sh              # Create and attach (default)
#   ./run_claude_swarm.sh --no-attach  # Create only, don't attach
#   ./run_claude_swarm.sh --attach     # Explicitly attach
#   ./run_claude_swarm.sh -d /path     # Override working directory
#
# Environment:
#   SWARM_WORKDIR - Default working directory (default: /home/user/projects/AAA/swarm)

# Configuration
SESSION_NAME="swarm-claude-default"
WORKDIR="${SWARM_WORKDIR:-/home/user/projects/AAA/swarm}"

# Parse arguments
ATTACH=true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --attach)
            ATTACH=true
            shift
            ;;
        --no-attach)
            ATTACH=false
            shift
            ;;
        --workdir|-d)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --workdir requires a directory argument"
                exit 1
            fi
            WORKDIR="$2"
            shift 2
            ;;
        --help|-h)
            echo "AI Swarm - Claude Code CLI Multi-Window Launcher"
            echo
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  --attach, -a        Attach to tmux session after creation (default)"
            echo "  --no-attach, -n     Create session but don't attach"
            echo "  --workdir, -d DIR   Set working directory (default: /home/user/projects/AAA/swarm)"
            echo "  --help, -h          Show this help message"
            echo
            echo "Environment variables:"
            echo "  SWARM_WORKDIR       Default working directory"
            echo
            echo "Creates tmux session '$SESSION_NAME' with 4 windows:"
            echo "  - master (focused)"
            echo "  - worker-0"
            echo "  - worker-1"
            echo "  - worker-2"
            echo
            echo "Each window runs Claude Code CLI in the specified directory."
            exit 0
            ;;
        *)
            echo "Error: Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Dependency check
echo "[CLAUDE-SWARM] Checking dependencies..."
if ! command -v claude >/dev/null 2>&1; then
    echo "[ERROR] Claude CLI not found. Please install Anthropic's Claude Code CLI."
    echo "        Visit: https://claude.com/claude-code"
    exit 1
fi

if ! command -v tmux >/dev/null 2>&1; then
    echo "[ERROR] tmux not found. Please install tmux."
    exit 1
fi

# Validate working directory
if [[ ! -d "$WORKDIR" ]]; then
    echo "[ERROR] Working directory does not exist: $WORKDIR"
    exit 1
fi

# Check if session already exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "[WARNING] Session '$SESSION_NAME' already exists."
    echo "          Use 'tmux attach -t $SESSION_NAME' to connect, or"
    echo "          Run 'tmux kill-session -t $SESSION_NAME' to remove it first."
    exit 1
fi

echo "[CLAUDE-SWARM] Creating tmux session '$SESSION_NAME'..."
echo "               Working directory: $WORKDIR"

# Create master window (detached, in session)
tmux new-session -d -s "$SESSION_NAME" -n master

# Launch claude in master window
tmux send-keys -t "$SESSION_NAME:master" "cd $WORKDIR && claude" Enter

# Create worker windows
for i in 0 1 2; do
    tmux new-window -n "worker-$i" -t "$SESSION_NAME"
    tmux send-keys -t "$SESSION_NAME:worker-$i" "cd $WORKDIR && claude" Enter
done

# Select master window as starting point
tmux select-window -t "$SESSION_NAME:master"

echo "[CLAUDE-SWARM] Session created successfully!"
echo "               4 windows: master, worker-0, worker-1, worker-2"
echo
echo "[CLAUDE-SWARM] Commands:"
printf "               Attach:   tmux attach -t %s\n" "$SESSION_NAME"
printf "               Status:   tmux list-windows -t %s\n" "$SESSION_NAME"
printf "               Kill:     tmux kill-session -t %s\n" "$SESSION_NAME"
echo

# Attach or exit
if [[ "$ATTACH" == true ]]; then
    echo "[CLAUDE-SWARM] Attaching to session..."
    tmux attach-session -t "$SESSION_NAME"
else
    echo "[CLAUDE-SWARM] Session ready. Run 'tmux attach -t $SESSION_NAME' to connect."
    exit 0
fi
