#!/usr/bin/env bash
set -euo pipefail

# Claude Swarm Status Check
# Displays last 10 lines from all swarm windows
#
# Environment:
#   CLAUDE_SESSION - Override default session name (default: swarm-claude-default)
#
# Usage:
#   CLAUDE_SESSION=custom-session ./claude_status.sh
#   ./claude_status.sh --session custom-session

# Default session name
SESSION="${CLAUDE_SESSION:-swarm-claude-default}"

# Parse --session flag
while [[ $# -gt 0 ]]; do
    case "$1" in
        --session)
            if [[ -n "${2:-}" ]]; then
                SESSION="$2"
                shift 2
            else
                echo "Error: --session requires a value" >&2
                exit 1
            fi
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Usage: $0 [--session <name>]" >&2
            exit 1
            ;;
    esac
done

echo "=== Claude Swarm Status ==="
echo ""

WINDOWS="master worker-0 worker-1 worker-2"

for window in $WINDOWS; do
    echo "--- $window ---"
    tmux capture-pane -t "$SESSION:$window" -p | tail -10
    echo ""
done
