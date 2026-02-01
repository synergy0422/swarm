#!/usr/bin/env bash

# Claude Swarm Continuous Monitor
# Continuously monitors worker windows for [DONE] and [ERROR] markers
# Press Ctrl+C to stop

SESSION="swarm-claude-default"
WINDOWS="worker-0 worker-1 worker-2"
POLL_INTERVAL=5

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
