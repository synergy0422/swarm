#!/usr/bin/env bash
# Task bridge script for AI Swarm - CLAUDE_CODE_TASK_LIST_ID integration
# Bridges tasks with swarm lock/state system for automatic claim->lock->work->done/fail闭环

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# =============================================================================
# Dependency Validation
# =============================================================================
check_dependencies() {
    local missing=0

    if [[ ! -f "$SCRIPT_DIR/swarm_lock.sh" ]]; then
        echo "Error: Missing dependency: scripts/swarm_lock.sh" >&2
        missing=1
    fi

    if [[ ! -f "$SCRIPT_DIR/swarm_status_log.sh" ]]; then
        echo "Error: Missing dependency: scripts/swarm_status_log.sh" >&2
        missing=1
    fi

    if [[ $missing -eq 1 ]]; then
        exit 1
    fi
}

# Run dependency check immediately
check_dependencies

# =============================================================================
# Usage function
# =============================================================================
usage() {
    cat <<EOF
Usage: $(basename "$0") <command> [arguments]

Commands:
    claim <task_id> <worker> [lock_key]
        Acquire task lock and log START status
        lock_key defaults to task_id if not provided

    done <task_id> <worker> [lock_key]
        Release task lock and log DONE status
        lock_key defaults to task_id if not provided

    fail <task_id> <worker> <reason> [lock_key]
        Release task lock and log ERROR status with reason
        lock_key defaults to task_id if not provided

Options:
    -h, --help    Show this help message

Environment:
    SWARM_STATE_DIR    Override default state directory (default: /tmp/ai_swarm)

Exit codes:
    claim:  0=success, 2=lock occupied, 1=other failure
    done:   0=success, 1=failure
    fail:   0=success, 1=failure

Examples:
    $(basename "$0") claim task-001 worker-0
    $(basename "$0") claim task-002 worker-1 custom-lock-key
    $(basename "$0") done task-001 worker-0
    $(basename "$0") fail task-003 worker-2 "Validation failed"
EOF
}

# =============================================================================
# Helper functions
# =============================================================================
validate_worker() {
    local worker="$1"
    if [[ ! "$worker" =~ ^worker-[0-9]+$ ]]; then
        echo "Error: Invalid worker '$worker'. Must match pattern worker-0, worker-1, etc." >&2
        return 1
    fi
    return 0
}

validate_lock_key() {
    local lock_key="$1"
    if [[ "$lock_key" =~ [[:space:]] ]]; then
        echo "Error: lock_key must not contain spaces" >&2
        return 1
    fi
    return 0
}

# =============================================================================
# Command: claim - Acquire lock and log START
# =============================================================================
cmd_claim() {
    if [[ $# -lt 2 ]]; then
        echo "Error: 'claim' requires <task_id> and <worker>" >&2
        echo "Usage: $0 claim <task_id> <worker> [lock_key]" >&2
        exit 1
    fi

    local task_id="$1"
    local worker="$2"
    local lock_key="${3:-$task_id}"

    # Validate worker
    if ! validate_worker "$worker"; then
        exit 1
    fi

    # Validate lock_key
    if ! validate_lock_key "$lock_key"; then
        exit 1
    fi

    # Acquire lock
    if ! "$SCRIPT_DIR/swarm_lock.sh" acquire "$lock_key" "$worker" 2>&1; then
        # Check if it's a lock conflict (exit 1 from swarm_lock.sh)
        # Extract holder information from the check output
        local lock_holder
        lock_holder=$("$SCRIPT_DIR/swarm_lock.sh" check "$lock_key" 2>/dev/null | grep -oP "Worker: \K[^ ]+" || echo "unknown")
        echo "Error: Lock held by '$lock_holder' for '$lock_key' (exit 2)" >&2
        exit 2
    fi

    # Log START status
    "$SCRIPT_DIR/swarm_status_log.sh" append START "$worker" "$task_id" "" >/dev/null 2>&1

    echo "Claimed task '$task_id' (lock: '$lock_key')"
}

# =============================================================================
# Command: done - Release lock and log DONE
# =============================================================================
cmd_done() {
    if [[ $# -lt 2 ]]; then
        echo "Error: 'done' requires <task_id> and <worker>" >&2
        echo "Usage: $0 done <task_id> <worker> [lock_key]" >&2
        exit 1
    fi

    local task_id="$1"
    local worker="$2"
    local lock_key="${3:-$task_id}"

    # Validate worker
    if ! validate_worker "$worker"; then
        exit 1
    fi

    # Validate lock_key
    if ! validate_lock_key "$lock_key"; then
        exit 1
    fi

    # Release lock
    if ! "$SCRIPT_DIR/swarm_lock.sh" release "$lock_key" "$worker" 2>&1; then
        echo "Error: Failed to release lock for '$lock_key'" >&2
        exit 1
    fi

    # Log DONE status
    "$SCRIPT_DIR/swarm_status_log.sh" append DONE "$worker" "$task_id" "Completed" >/dev/null 2>&1

    echo "Completed task '$task_id' (lock: '$lock_key')"
}

# =============================================================================
# Command: fail - Release lock and log ERROR
# =============================================================================
cmd_fail() {
    if [[ $# -lt 3 ]]; then
        echo "Error: 'fail' requires <task_id>, <worker>, and <reason>" >&2
        echo "Usage: $0 fail <task_id> <worker> <reason> [lock_key]" >&2
        exit 1
    fi

    local task_id="$1"
    local worker="$2"
    local reason="$3"
    local lock_key="${4:-$task_id}"

    # Validate worker
    if ! validate_worker "$worker"; then
        exit 1
    fi

    # Validate lock_key
    if ! validate_lock_key "$lock_key"; then
        exit 1
    fi

    # Validate reason is non-empty
    if [[ -z "$reason" ]]; then
        echo "Error: reason cannot be empty" >&2
        exit 1
    fi

    # Release lock
    if ! "$SCRIPT_DIR/swarm_lock.sh" release "$lock_key" "$worker" 2>&1; then
        echo "Error: Failed to release lock for '$lock_key'" >&2
        exit 1
    fi

    # Log ERROR status with reason
    "$SCRIPT_DIR/swarm_status_log.sh" append ERROR "$worker" "$task_id" "$reason" >/dev/null 2>&1

    echo "Failed task '$task_id' (lock: '$lock_key'): $reason"
}

# =============================================================================
# Main entry point
# =============================================================================
main() {
    if [[ $# -lt 1 ]]; then
        usage
        exit 1
    fi

    local cmd="$1"
    shift

    case "$cmd" in
        help|--help|-h)
            usage
            ;;
        claim)
            cmd_claim "$@"
            ;;
        done)
            cmd_done "$@"
            ;;
        fail)
            cmd_fail "$@"
            ;;
        *)
            echo "Error: Unknown command '$cmd'" >&2
            usage >&2
            exit 1
            ;;
    esac
}

main "$@"
