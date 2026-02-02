#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# Backward compatibility: SESSION variable for scripts expecting it
SESSION="${SESSION_NAME}"

# Valid status types for broadcast commands
VALID_TYPES=("START" "DONE" "ERROR" "WAIT")

# Get worker window name from tmux pane
get_worker_from_tmux() {
    if [[ -z "${TMUX_PANE:-}" ]]; then
        log_error "TMUX_PANE not set. Are you running inside a tmux session?"
        return 1
    fi

    local window_name
    window_name=$(tmux display-message -p -t "$TMUX_PANE" '#{window_name}' 2>/dev/null) || {
        log_error "Failed to get window name from tmux"
        return 1
    }

    # Validate it's a worker window
    case "$window_name" in
        worker-0|worker-1|worker-2)
            echo "$window_name"
            return 0
            ;;
        *)
            log_error "Not a worker window: $window_name (expected: worker-0, worker-1, or worker-2)"
            return 1
            ;;
    esac
}

# Usage function
usage() {
    cat <<EOF
Usage: $(basename "$0") <command> <task_id> [reason] [--session <name>]

Broadcast status updates for worker lifecycle events.

Commands:
    start <task_id> [reason]    Broadcast START status
    done <task_id> [reason]     Broadcast DONE status
    error <task_id> [reason]    Broadcast ERROR status
    wait <task_id> [reason]     Broadcast WAIT status
    help                        Show this help message

Options:
    --session <name>    tmux session name (default: swarm-claude-default)

Examples:
    # Broadcast START status (auto-detects worker from TMUX)
    $(basename "$0") start task-001

    # Broadcast DONE status with reason
    $(basename "$0") done task-001 "Completed successfully"

    # Broadcast ERROR status with reason
    $(basename "$0") error task-002 "File not found"

    # Broadcast WAIT status with reason
    $(basename "$0") wait task-003 "Waiting for dependency"

    # With custom session
    $(basename "$0") --session custom-session start task-004

Environment:
    SWARM_STATE_DIR    State directory (default: /tmp/ai_swarm)
EOF
}

# Broadcast a status update
broadcast_status() {
    local type="$1"
    local task_id="$2"
    local reason="${3:-}"

    # Get worker from tmux
    local worker
    worker=$(get_worker_from_tmux) || return 1

    # Call swarm_status_log.sh append (no timestamp - it handles that internally)
    local cmd=("$SCRIPT_DIR/swarm_status_log.sh" "append" "$type" "$worker" "$task_id")
    if [[ -n "$reason" ]]; then
        cmd+=("$reason")
    fi

    if "${cmd[@]}"; then
        log_info "Broadcasted $type for $task_id (worker: $worker)"
        return 0
    else
        log_error "Failed to broadcast $type for $task_id"
        return 1
    fi
}

# Command handlers
cmd_start() {
    if [[ $# -lt 1 ]]; then
        log_error "Usage: $0 start <task_id> [reason]"
        exit 1
    fi
    broadcast_status "START" "$1" "${2:-}"
}

cmd_done() {
    if [[ $# -lt 1 ]]; then
        log_error "Usage: $0 done <task_id> [reason]"
        exit 1
    fi
    broadcast_status "DONE" "$1" "${2:-}"
}

cmd_error() {
    if [[ $# -lt 1 ]]; then
        log_error "Usage: $0 error <task_id> [reason]"
        exit 1
    fi
    broadcast_status "ERROR" "$1" "${2:-}"
}

cmd_wait() {
    if [[ $# -lt 1 ]]; then
        log_error "Usage: $0 wait <task_id> [reason]"
        exit 1
    fi
    broadcast_status "WAIT" "$1" "${2:-}"
}

# Main entry point
main() {
    # Handle --session flag first
    if [[ "${1:-}" == "--session" ]] && [[ -n "${2:-}" ]]; then
        SESSION="$2"
        shift 2
    elif [[ "${1:-}" == "--session" ]]; then
        log_error "Error: --session requires a value"
        exit 1
    fi

    if [[ $# -lt 1 ]]; then
        usage
        exit 1
    fi

    local command="$1"
    shift

    case "$command" in
        start)
            cmd_start "$@"
            ;;
        done)
            cmd_done "$@"
            ;;
        error)
            cmd_error "$@"
            ;;
        wait)
            cmd_wait "$@"
            ;;
        -h|--help|help)
            usage
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

main "$@"
