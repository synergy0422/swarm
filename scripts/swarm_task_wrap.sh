#!/usr/bin/env bash
# Task lifecycle wrapper with lock/state integration for AI Swarm
# Provides standardized task execution with proper lock acquisition, status broadcasting, and cleanup

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# =============================================================================
# Global state for lifecycle management (declared before functions for trap access)
# =============================================================================
LOCK_ACQUIRED=0
LOCK_TASK_ID=""
LOCK_WORKER=""
SKIP_STATUS=0
TTL_SECONDS=""

# =============================================================================
# Usage function
# =============================================================================
usage() {
    cat <<EOF
Usage: $(basename "$0") <command> [arguments]

Commands:
    run <task_id> <worker> <command> [args...]
        Execute a command with full task lifecycle (lock + status)

    acquire-only <task_id> [worker]
        Acquire lock and write START status (for manual execution)
        Worker defaults to auto-detection if not provided

    release-only <task_id> [worker]
        Release lock and write DONE status (for completed tasks)
        Worker defaults to auto-detection if not provided

    skip <task_id> [worker] <reason>
        Write SKIP status (no lock operation - for tasks not yet started)

    wait <task_id> [worker] <reason>
        Write WAIT status (no lock operation - for blocked tasks)

Options:
    --ttl SECONDS    Lock TTL in seconds (default: no expiry)
    --no-status      Skip status logging (for testing)

Environment:
    SWARM_STATE_DIR  Override state directory (default: from _config.sh)
    WORKER           Worker name for auto-detection

Examples:
    $(basename "$0") run task-001 worker-0 echo hello
    $(basename "$0") run --ttl 3600 task-002 worker-1 python process.py arg1
    $(basename "$0") skip task-003 "Dependency not ready"
    $(basename "$0") wait task-004 "Waiting for upstream"
EOF
}

# =============================================================================
# Helper function to detect/resolve worker
# =============================================================================
detect_worker() {
    if [[ -n "$WORKER" ]]; then
        echo "$WORKER"
        return 0
    fi
    # Fallback to default from config
    echo "${WORKER:-worker-0}"
}

# =============================================================================
# Command: acquire-only - Acquire lock and write START status
# =============================================================================
cmd_acquire_only() {
    local task_id="$1"
    local worker="${2:-$(detect_worker)}"

    if ! "$SCRIPT_DIR/swarm_lock.sh" acquire "$task_id" "$worker" "${TTL_SECONDS:-}"; then
        log_error "Failed to acquire lock for $task_id"
        [[ "$SKIP_STATUS" -eq 0 ]] && "$SCRIPT_DIR/swarm_status_log.sh" append WAIT "$worker" "$task_id" "Lock not acquired"
        exit 1
    fi
    [[ "$SKIP_STATUS" -eq 0 ]] && "$SCRIPT_DIR/swarm_status_log.sh" append START "$worker" "$task_id" ""
    log_info "Acquired lock and started $task_id"
}

# =============================================================================
# Command: release-only - Release lock and write DONE status
# =============================================================================
cmd_release_only() {
    local task_id="$1"
    local worker="${2:-$(detect_worker)}"

    "$SCRIPT_DIR/swarm_lock.sh" release "$task_id" "$worker"
    [[ "$SKIP_STATUS" -eq 0 ]] && "$SCRIPT_DIR/swarm_status_log.sh" append DONE "$worker" "$task_id" "Completed"
    log_info "Released lock for $task_id"
}

# =============================================================================
# Command: skip - Write SKIP status (no lock operation)
# =============================================================================
cmd_skip() {
    local task_id="$1"
    # Parse: second arg is either worker (if matches worker-*) or reason
    local arg2="${2:-}"
    if [[ "$arg2" =~ ^worker-[0-9]+$ ]]; then
        local worker="$arg2"
        local reason="${3:-}"
    else
        local worker=$(detect_worker)
        local reason="$arg2"
    fi

    # skip does NOT acquire/release lock - just write status
    [[ "$SKIP_STATUS" -eq 0 ]] && "$SCRIPT_DIR/swarm_status_log.sh" append SKIP "$worker" "$task_id" "$reason"
    log_info "Skipped $task_id: $reason"
}

# =============================================================================
# Command: wait - Write WAIT status (no lock operation)
# =============================================================================
cmd_wait() {
    local task_id="$1"
    # Parse: second arg is either worker (if matches worker-*) or reason
    local arg2="${2:-}"
    if [[ "$arg2" =~ ^worker-[0-9]+$ ]]; then
        local worker="$arg2"
        local reason="${3:-}"
    else
        local worker=$(detect_worker)
        local reason="$arg2"
    fi

    # wait does NOT acquire/release lock - just write status
    [[ "$SKIP_STATUS" -eq 0 ]] && "$SCRIPT_DIR/swarm_status_log.sh" append WAIT "$worker" "$task_id" "$reason"
    log_info "Set $task_id to wait: $reason"
}

# =============================================================================
# Command: run - Full task lifecycle (acquire -> START -> execute -> DONE/ERROR -> release)
# =============================================================================
cmd_run() {
    # Options already parsed by main(), remaining args are: task_id worker command [args...]

    # Now parse positional arguments
    if [[ $# -lt 3 ]]; then
        log_error "run requires: <task_id> <worker> <command> [args...]"
        log_error "Example: $0 run task-001 worker-0 echo hello"
        exit 1
    fi

    local task_id="$1"
    local worker="$2"
    shift 2

    # Remaining args are the command and its arguments (NO quotes around command)
    # Usage: ./wrap.sh run task-001 worker-0 echo hello
    # NOT:   ./wrap.sh run task-001 worker-0 "echo hello"

    # Set global state for trap callbacks
    LOCK_ACQUIRED=0
    LOCK_TASK_ID="$task_id"
    LOCK_WORKER="$worker"

    # Step 1: Acquire lock
    if ! "$SCRIPT_DIR/swarm_lock.sh" acquire "$task_id" "$worker" "${TTL_SECONDS:-}"; then
        log_warn "Failed to acquire lock for $task_id"
        # Step 1a: Write WAIT status (lock held by another)
        [[ "$SKIP_STATUS" -eq 0 ]] && "$SCRIPT_DIR/swarm_status_log.sh" append WAIT "$worker" "$task_id" "Lock not acquired"
        exit 1
    fi
    LOCK_ACQUIRED=1

    # Step 2: Write START status
    [[ "$SKIP_STATUS" -eq 0 ]] && "$SCRIPT_DIR/swarm_status_log.sh" append START "$worker" "$task_id" ""
    log_info "Started task $task_id on $worker"

    # Step 3: Execute command (NO eval!)
    # Run command in subshell with set +e to capture exit code without exiting
    # The subshell prevents command failure from affecting the main script
    set +e
    (
        "$@"  # Execute command directly - args are already an array
    )
    local exit_code=$?
    set -e

    # Step 4: Write DONE or ERROR based on exit code, then release lock
    if [[ $exit_code -eq 0 ]]; then
        [[ "$SKIP_STATUS" -eq 0 ]] && "$SCRIPT_DIR/swarm_status_log.sh" append DONE "$worker" "$task_id" "Completed successfully"
        log_info "Task $task_id completed"
    else
        [[ "$SKIP_STATUS" -eq 0 ]] && "$SCRIPT_DIR/swarm_status_log.sh" append ERROR "$worker" "$task_id" "Exit code: $exit_code"
        log_error "Task $task_id failed with exit code $exit_code"
    fi

    # Release lock (only if we acquired it)
    if [[ "$LOCK_ACQUIRED" -eq 1 ]]; then
        "$SCRIPT_DIR/swarm_lock.sh" release "$task_id" "$worker" 2>/dev/null || true
        LOCK_ACQUIRED=0
    fi

    # Exit with appropriate code
    exit $exit_code
}

# =============================================================================
# Main entry point
# =============================================================================
main() {
    # Parse global options first (--ttl, --no-status)
    TTL_SECONDS=""
    SKIP_STATUS=0

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --ttl)
                if [[ -z "${2:-}" ]]; then
                    log_error "--ttl requires a value (e.g., --ttl 3600)"
                    exit 1
                fi
                if ! [[ "$2" =~ ^[0-9]+$ ]]; then
                    log_error "--ttl value must be a positive number (got: $2)"
                    exit 1
                fi
                TTL_SECONDS="$2"
                shift 2
                ;;
            --no-status)
                SKIP_STATUS=1
                shift
                ;;
            *)
                # Not a global option, stop parsing
                break
                ;;
        esac
    done

    if [[ $# -lt 1 ]]; then
        usage
        exit 1
    fi

    local cmd="$1"
    shift

    case "$cmd" in
        help|h|--help|-h)
            usage
            ;;
        run)
            cmd_run "$@"
            ;;
        acquire-only|acquire)
            cmd_acquire_only "$@"
            ;;
        release-only|release)
            cmd_release_only "$@"
            ;;
        skip)
            cmd_skip "$@"
            ;;
        wait)
            cmd_wait "$@"
            ;;
        *)
            log_error "Unknown command: $cmd"
            usage
            exit 1
            ;;
    esac
}

main "$@"
