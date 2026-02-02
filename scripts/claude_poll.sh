#!/usr/bin/env bash
set -euo pipefail

# Claude Swarm Continuous Monitor
# Continuously monitors worker windows for [DONE] and [ERROR] markers
# Press Ctrl+C to stop
#
# Environment:
#   CLAUDE_SESSION - Override default session name (default: swarm-claude-default)
#
# Usage:
#   CLAUDE_SESSION=custom-session ./claude_poll.sh
#   ./claude_poll.sh --session custom-session

# Default session name
SESSION="${CLAUDE_SESSION:-swarm-claude-default}"
WINDOWS="worker-0 worker-1 worker-2"
POLL_INTERVAL=5

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

echo "Starting Claude Swarm monitor..."
echo "Session: $SESSION"
echo "Windows: ${WINDOWS}"
echo "Poll interval: ${POLL_INTERVAL}s"
echo "Press Ctrl+C to stop"
echo ""

# Cleanup handler for Ctrl+C
trap 'echo "Stopping monitor..."; exit 0' INT

while true; do
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="

    for window in $WINDOWS; do
        local pane_content
        pane_content=$(tmux capture-pane -t "$SESSION:$window" -p | tail -200)

        # Check for DONE markers
        local done_count
        done_count=$(echo "$pane_content" | grep -c '\[DONE\]' || true)

        # Check for ERROR markers
        local error_count
        error_count=$(echo "$pane_content" | grep -c '\[ERROR\]' || true)

        # Show status line for this window
        if [[ "$done_count" -gt 0 ]]; then
            echo "[$window] DONE: $done_count tasks completed"
        elif [[ "$error_count" -gt 0 ]]; then
            echo "[$window] ERROR: $error_count failures detected"
        else
            echo "[$window] Running..."
        fi
    done

    echo ""
    sleep "$POLL_INTERVAL"
done
