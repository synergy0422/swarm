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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# Backward compatibility: SESSION variable for scripts expecting it
SESSION="${SESSION_NAME}"

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

log_info "=== Claude Swarm Status ==="
echo ""

WINDOWS="master worker-0 worker-1 worker-2"

for window in $WINDOWS; do
    log_info "--- $window ---"
    tmux capture-pane -t "$SESSION:$window" -p | tail -10
    echo ""
done
