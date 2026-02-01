#!/usr/bin/env bash
set -euo pipefail

# Claude Swarm Communication Script
# Provides send, poll, and status commands for tmux window communication

SESSION="swarm-claude-default"

# Usage examples:
#   claude_comm.sh send worker-0 task-001 "创建文件 hello.py"
#   claude_comm.sh poll worker-0 30 task-001
#   claude_comm.sh status worker-0

# Send a task to a specific window
# Usage: send <window> <task_id> "<description>"
send() {
    local window="$1"
    local task_id="$2"
    local description="$3"

    # Send [TASK] marker with task_id
    tmux send-keys -t "$SESSION:$window" "[TASK] $task_id "

    # Send the description (trim any extra whitespace)
    echo "$description" | tmux send-keys -t "$SESSION:$window" ""

    # Send Enter to execute
    tmux send-keys -t "$SESSION:$window" "Enter"

    echo "Sent task $task_id to window $window"
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
            echo "Usage: $0 <send|poll|status> [args]" >&2
            echo "" >&2
            echo "Commands:" >&2
            echo "  send <window> <task_id> \"<description>\"  - Send task to window" >&2
            echo "  poll <window> [timeout] [task_id]    - Poll for marker response" >&2
            echo "  status <window>                       - Get window status" >&2
            exit 1
            ;;
    esac
}

# Run main if called directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    if [[ $# -lt 1 ]]; then
        echo "Usage: $0 <send|poll|status> [args]" >&2
        exit 1
    fi
    main "$@"
fi
