#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# Use SWARM_STATE_DIR from _common.sh
STATUS_LOG="$SWARM_STATE_DIR/status.log"

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
    log_error "Invalid type '$type'. Valid types: ${VALID_TYPES[*]}"
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

    # Ensure state directory and locks subdirectory exist
    mkdir -p "$SWARM_STATE_DIR/locks"

    # Build JSON object
    local json
    if [[ -n "$reason" ]]; then
        # Escape backslashes first, then newlines, then quotes for valid JSON
        local reason_escaped
        reason_escaped="${reason//\\/\\\\}"
        reason_escaped="${reason_escaped//$'\n'/\\n}"
        reason_escaped="${reason_escaped//\"/\\\"}"
        json="{\"timestamp\":\"$timestamp\",\"type\":\"$type\",\"worker\":\"$worker\",\"task_id\":\"$task_id\",\"reason\":\"$reason_escaped\"}"
    else
        json="{\"timestamp\":\"$timestamp\",\"type\":\"$type\",\"worker\":\"$worker\",\"task_id\":\"$task_id\"}"
    fi

    # Append to log file
    echo "$json" >> "$STATUS_LOG"

    # Print success message (data output)
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

    # Grep for lines containing exact task_id field match
    local found=0
    while IFS= read -r line; do
        echo "$line"
        found=1
    done < <(grep -E "\"task_id\":\"${task_id}\"" "$STATUS_LOG" 2>/dev/null || true)

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
