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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# Backward compatibility: SESSION variable for scripts expecting it
SESSION="${SESSION_NAME}"

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
                log_error "Error: --session requires a value"
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

log_info "Starting Claude Swarm monitor..."
log_info "Session: $SESSION"
log_info "Windows: ${WINDOWS}"
log_info "Poll interval: ${POLL_INTERVAL}s"
log_info "Press Ctrl+C to stop"
echo ""

# Cleanup handler for Ctrl+C
trap 'echo "Stopping monitor..."; exit 0' INT

while true; do
    log_info "=== $(date '+%Y-%m-%d %H:%M:%S') ==="

    for window in $WINDOWS; do
        pane_content=$(tmux capture-pane -t "$SESSION:$window" -p | tail -200)

        # Check for DONE markers
        done_count=$(echo "$pane_content" | grep -c '\[DONE\]' || true)

        # Check for ERROR markers
        error_count=$(echo "$pane_content" | grep -c '\[ERROR\]' || true)

        # Show status line for this window
        if [[ "$done_count" -gt 0 ]]; then
            log_info "[$window] DONE: $done_count tasks completed"
        elif [[ "$error_count" -gt 0 ]]; then
            log_info "[$window] ERROR: $error_count failures detected"
        else
            log_info "[$window] Running..."
        fi
    done

    echo ""
    sleep "$POLL_INTERVAL"
done
