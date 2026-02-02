#!/usr/bin/env bash
set -euo pipefail

# Configuration
STATE_DIR="${SWARM_STATE_DIR:-/tmp/ai_swarm}"
STATUS_LOG="$STATE_DIR/status.log"

# Valid status types
VALID_TYPES=("START" "DONE" "ERROR" "WAIT" "HELP" "SKIP")

# Usage function
usage() {
    cat <<EOF
Usage: $(basename "$0") <command> [arguments]

Commands:
    append <type> <worker> <task_id> [reason]
        Append a status record to the log
        Valid types: START, DONE, ERROR, WAIT, HELP, SKIP

    tail <n>
        Display the last N status records (default: 10)

    query <task_id>
        Search and display records for a specific task_id

Examples:
    # Append START record with default state directory
    SWARM_STATE_DIR=/custom/path ./scripts/swarm_status_log.sh append START worker-0 task-001

    # Append DONE record
    ./scripts/swarm_status_log.sh append DONE worker-0 task-001

    # Append ERROR record with reason
    ./scripts/swarm_status_log.sh append ERROR worker-1 task-002 "File not found"

    # Tail last 10 records
    ./scripts/swarm_status_log.sh tail 10

    # Query specific task
    ./scripts/swarm_status_log.sh query task-001

Environment:
    SWARM_STATE_DIR - Override default state directory (/tmp/ai_swarm)
EOF
}

# Validate status type
validate_type() {
    local type="$1"
    for valid in "${VALID_TYPES[@]}"; do
        if [[ "$type" == "$valid" ]]; then
            return 0
        fi
    done
    echo "Error: Invalid type '$type'. Valid types: ${VALID_TYPES[*]}" >&2
    return 1
}

# Append status record
cmd_append() {
    if [[ $# -lt 3 ]]; then
        echo "Error: append requires at least 3 arguments: <type> <worker> <task_id>" >&2
        echo "Usage: $(basename "$0") append <type> <worker> <task_id> [reason]" >&2
        return 1
    fi

    local type="$1"
    local worker="$2"
    local task_id="$3"
    local reason="${4:-}"

    # Validate type
    if ! validate_type "$type"; then
        return 1
    fi

    # Generate timestamp
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Ensure state directory exists
    mkdir -p "$STATE_DIR"

    # Build JSON object
    local json
    if [[ -n "$reason" ]]; then
        # Escape quotes in reason if present
        reason_escaped="${reason//\"/\\\"}"
        json="{\"timestamp\":\"$timestamp\",\"type\":\"$type\",\"worker\":\"$worker\",\"task_id\":\"$task_id\",\"reason\":\"$reason_escaped\"}"
    else
        json="{\"timestamp\":\"$timestamp\",\"type\":\"$type\",\"worker\":\"$worker\",\"task_id\":\"$task_id\"}"
    fi

    # Append to log file
    echo "$json" >> "$STATUS_LOG"

    # Print success message
    echo "Appended: $json"
}

# Tail status records
cmd_tail() {
    local n="${1:-10}"

    # Validate N is a positive integer
    if ! [[ "$n" =~ ^[0-9]+$ ]] || [[ "$n" -le 0 ]]; then
        n=10
    fi

    # Handle non-existent or empty file
    if [[ ! -f "$STATUS_LOG" ]]; then
        echo "No status log found at: $STATUS_LOG"
        return 0
    fi

    if [[ ! -s "$STATUS_LOG" ]]; then
        echo "Status log is empty"
        return 0
    fi

    # Output last N lines
    tail -n "$n" "$STATUS_LOG"
}

# Query status records by task_id
cmd_query() {
    if [[ $# -lt 1 ]]; then
        echo "Error: query requires 1 argument: <task_id>" >&2
        echo "Usage: $(basename "$0") query <task_id>" >&2
        return 1
    fi

    local task_id="$1"

    # Handle non-existent or empty file
    if [[ ! -f "$STATUS_LOG" ]]; then
        echo "No status log found at: $STATUS_LOG"
        return 0
    fi

    if [[ ! -s "$STATUS_LOG" ]]; then
        echo "Status log is empty"
        return 0
    fi

    # Grep for lines containing task_id
    local found=0
    while IFS= read -r line; do
        echo "$line"
        found=1
    done < <(grep "$task_id" "$STATUS_LOG" 2>/dev/null || true)

    if [[ $found -eq 0 ]]; then
        echo "No records found for task_id: $task_id"
    fi
}

# Main entry point
main() {
    if [[ $# -lt 1 ]]; then
        usage
        exit 1
    fi

    local command="$1"
    shift

    case "$command" in
        append)
            cmd_append "$@"
            ;;
        tail)
            cmd_tail "$@"
            ;;
        query)
            cmd_query "$@"
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            echo "Error: Unknown command '$command'" >&2
            usage >&2
            exit 1
            ;;
    esac
}

main "$@"
