#!/usr/bin/env bash
set -euo pipefail

# Claude Swarm Communication Script
# Provides send, poll, and status commands for tmux window communication
#
# Usage:
#   ./claude_comm.sh send <window> <task_id> "<description>"
#   ./claude_comm.sh poll <window> [timeout] [task_id]
#   ./claude_comm.sh status <window>
#
# Environment:
#   CLAUDE_SESSION - Override default session name (default: swarm-claude-default)
#
# Examples:
#   CLAUDE_SESSION=custom-session ./scripts/claude_comm.sh send worker-0 task-001 "创建文件 hello.py"
#   ./scripts/claude_comm.sh --session custom-session send worker-0 task-001 "创建文件 hello.py"
#   ./scripts/claude_comm.sh poll worker-0 30 task-001  # timeout: 30s (default)
#   ./scripts/claude_comm.sh status worker-0

SESSION="${CLAUDE_SESSION:-swarm-claude-default}"

# Parse --session flag early
parse_args() {
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
                break
                ;;
        esac
    done
}

# Send a task to a specific window
# Usage: send <window> <task_id> "<description>"
send() {
    local window="$1"
    local task_id="$2"
    local description="$3"

    # Send complete task message on single line (no newlines)
    tmux send-keys -t "$SESSION:$window" "[TASK] $task_id $description"

    # Send Enter to execute
    tmux send-keys -t "$SESSION:$window" "Enter"

    echo "Sent task $task_id to window $window"
}

# Send raw text (no [TASK] prefix) for protocol setup messages
# Usage: send-raw <window> "<message>"
send_raw() {
    local window="$1"
    local message="$2"

    # Send raw message on single line
    tmux send-keys -t "$SESSION:$window" "$message"

    # Send Enter to execute
    tmux send-keys -t "$SESSION:$window" "Enter"

    echo "Sent raw message to window $window"
}

# Poll for a marker response from a window
# Usage: poll <window> [timeout] [task_id]
# Markers: [ACK], [DONE], [ERROR], [WAIT], [HELP]
poll() {
    local window="$1"
    local timeout="${2:-30}"
    local task_id="${3:-}"

    local start_time=$(date +%s)
    local end_time=$((start_time + timeout))

    while [[ $(date +%s) -lt $end_time ]]; do
        local pane_content
        pane_content=$(tmux capture-pane -t "$SESSION:$window" -p | tail -200)

        if [[ -n "$task_id" ]]; then
            # Look for marker with specific task_id
            local match
            match=$(echo "$pane_content" | grep -E "\[(ACK|DONE|ERROR|WAIT|HELP)\] *$task_id" | head -1)
            if [[ -n "$match" ]]; then
                echo "$match"
                return 0
            fi
        else
            # Look for any marker
            local match
            match=$(echo "$pane_content" | grep -E "\[(ACK|DONE|ERROR|WAIT|HELP)\]" | tail -1)
            if [[ -n "$match" ]]; then
                echo "$match"
                return 0
            fi
        fi

        sleep 1
    done

    echo "Timeout: No marker found for task $task_id in ${timeout}s" >&2
    return 1
}

# Get status from a specific window
# Usage: status <window>
status() {
    local window="$1"
    tmux capture-pane -t "$SESSION:$window" -p | tail -20
}

# Main entry point
main() {
    parse_args "$@"
    shift $?

    if [[ $# -lt 1 ]]; then
        echo "Usage: $0 <send|send-raw|poll|status> [options]"
        echo ""
        echo "Commands:"
        echo "  send <window> <task_id> \"<description>\"  - Send task to window (with [TASK] prefix)"
        echo "  send-raw <window> \"<message>\"            - Send raw message (no prefix)"
        echo "  poll <window> [timeout] [task_id]         - Poll for marker response (default timeout: 30s)"
        echo "  status <window>                           - Get window status"
        echo ""
        echo "Options:"
        echo "  --session <name>  Override default session (default: swarm-claude-default)"
        echo ""
        echo "Environment:"
        echo "  CLAUDE_SESSION  Override default session name"
        exit 1
    fi

    local subcommand="$1"
    shift

    case "$subcommand" in
        send)
            if [[ $# -lt 3 ]]; then
                echo "Usage: $0 send <window> <task_id> \"<description>\"" >&2
                exit 1
            fi
            send "$1" "$2" "$3"
            ;;
        send-raw)
            if [[ $# -lt 2 ]]; then
                echo "Usage: $0 send-raw <window> \"<message>\"" >&2
                exit 1
            fi
            send_raw "$1" "$2"
            ;;
        poll)
            poll "$@"
            ;;
        status)
            if [[ $# -lt 1 ]]; then
                echo "Usage: $0 status <window>" >&2
                exit 1
            fi
            status "$1"
            ;;
        *)
            echo "Unknown command: $subcommand" >&2
            echo "" >&2
            echo "Available commands: send, send-raw, poll, status" >&2
            exit 1
            ;;
    esac
}

# Run main if called directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ $# -lt 1 ]]; then
        echo "Usage: $0 <send|send-raw|poll|status> [options]" >&2
        echo "" >&2
        echo "Commands: send, send-raw, poll, status" >&2
        echo "" >&2
        echo "Options:" >&2
        echo "  --session <name>  Override default session" >&2
        echo "" >&2
        echo "Run '$0 help' for full usage" >&2
        exit 1
    fi
    main "$@"
fi
