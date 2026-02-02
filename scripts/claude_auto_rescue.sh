#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# Backward compatibility: SESSION variable for scripts expecting it
SESSION="${SESSION_NAME}"

# Worker windows only (master excluded)
WORKER_WINDOWS="worker-0 worker-1 worker-2"
COOLDOWN_SECONDS=30
LAST_ACTION_FILE="${SWARM_STATE_DIR}/.auto_rescue_last_action"

# Pattern categories (in order of priority)
# Note: done/ready/ok removed - too broad, causes false positives
PATTERNS=(
    "[y/n]"                    # Standard yes/no prompt
    "[Y/n]"                    # Yes/No with capital Y
    "[y/N]"                    # Yes/No with capital N
    "press enter"              # Press Enter variants
    "press return"
    "hit enter"
    "回车继续"                 # Chinese: press enter to continue
    "按回车"                   # Chinese: press enter
    "confirm"                  # Confirmation words (require word boundary)
    "continue"
    "proceed"
    "yes"                      # Standalone yes (with space/punctuation)
)

# Dangerous commands (block auto-rescue)
DANGEROUS_PATTERNS=(
    "rm -rf"
    "rm -r"
    "rm -f"
    "del"
    "delete"
    "drop"
    "DROP"
    "truncate"
    "sudo"
    "password"
    "passwd"
)

# Usage function
usage() {
    cat <<EOF
Usage: $(basename "$0") <window> [--session <name>]

Automatically detect and confirm prompts in a tmux window.

Commands:
    check <window>     Check if prompt detected and auto-confirm
    run <window>       Run continuous monitoring loop
    status             Show last action timestamp per window

Options:
    --session <name>   tmux session name (default: swarm-claude-default)

Examples:
    $(basename "$0") check worker-0
    $(basename "$0") run worker-0
    $(basename "$0") status

Environment:
    SWARM_STATE_DIR    State directory (default: /tmp/ai_swarm)
EOF
}

# Check if a window name is a worker window
is_worker_window() {
    local window="$1"
    for worker in $WORKER_WINDOWS; do
        if [[ "$window" == "$worker" ]]; then
            return 0
        fi
    done
    return 1
}

# Get last action timestamp for a window
get_last_action() {
    local window="$1"
    local file="${LAST_ACTION_FILE}_${window}"
    if [[ -f "$file" ]]; then
        cat "$file"
    else
        echo "0"
    fi
}

# Record action timestamp for a window
record_action() {
    local window="$1"
    local file="${LAST_ACTION_FILE}_${window}"
    mkdir -p "$(dirname "$file")"
    echo "$(date +%s)" > "$file"
}

# Check if cooldown has passed
check_cooldown() {
    local window="$1"
    local last_action=$(get_last_action "$window")
    local now=$(date +%s)
    local elapsed=$((now - last_action))

    if [[ $elapsed -ge $COOLDOWN_SECONDS ]]; then
        return 0  # Cooldown passed
    else
        log_info "Cooldown active for $window: ${COOLDOWN_SECONDS}s - ${elapsed}s elapsed"
        return 1  # Still in cooldown
    fi
}

# Detect dangerous patterns in pane content
# Returns: 0 = dangerous pattern found (block auto-rescue), 1 = safe
detect_dangerous() {
    local pane_content="$1"

    for pattern in "${DANGEROUS_PATTERNS[@]}"; do
        if echo "$pane_content" | grep -qiF "$pattern"; then
            echo "DANGEROUS: $pattern"
            return 0  # Dangerous pattern found → block
        fi
    done
    return 1  # No dangerous patterns → safe to proceed
}

# Detect confirmation prompts in pane content
detect_prompt() {
    local pane_content="$1"

    for pattern in "${PATTERNS[@]}"; do
        if echo "$pane_content" | grep -qiF "$pattern"; then
            echo "$pattern"
            return 0  # Pattern found
        fi
    done
    return 1  # No pattern found
}

# Check a window and auto-confirm if needed
cmd_check() {
    if [[ $# -lt 1 ]]; then
        log_error "Usage: $0 check <window>"
        exit 1
    fi

    local window="$1"

    # Only worker windows
    if ! is_worker_window "$window"; then
        log_info "Skipping $window: not a worker window (worker-0/1/2 only)"
        return 0
    fi

    # Check cooldown
    if ! check_cooldown "$window"; then
        return 0
    fi

    # Capture pane content
    local pane_content
    pane_content=$(tmux capture-pane -t "$SESSION:$window" -p | tail -50)

    # Check for dangerous patterns first (block auto-rescue)
    # detect_dangerous: 0 = dangerous found (block), 1 = safe (proceed)
    local danger_result
    danger_result=$(detect_dangerous "$pane_content")
    if [[ $? -eq 0 ]]; then
        log_warn "Dangerous pattern detected in $window: $danger_result"
        log_warn "Manual confirmation required - blocking auto-rescue"
        return 0
    fi

    # Check for confirmation prompts
    local pattern
    pattern=$(detect_prompt "$pane_content")
    if [[ $? -eq 0 ]]; then
        log_info "Detected prompt in $window: '$pattern'"

        # Send Enter to confirm
        tmux send-keys -t "$SESSION:$window" "Enter"
        record_action "$window"

        log_info "Auto-confirmed: sent Enter to $window"
        return 0
    fi

    log_info "No confirmation prompt detected in $window"
    return 0
}

# Run continuous monitoring loop
cmd_run() {
    if [[ $# -lt 1 ]]; then
        log_error "Usage: $0 run <window>"
        exit 1
    fi

    local window="$1"

    # Only worker windows
    if ! is_worker_window "$window"; then
        log_info "Skipping $window: not a worker window (worker-0/1/2 only)"
        return 0
    fi

    log_info "Starting auto-rescue monitoring for $window..."
    log_info "Press Ctrl+C to stop"

    # Cleanup handler
    trap 'log_info "Stopping auto-rescue monitoring..."; exit 0' INT

    while true; do
        # Check and auto-confirm
        cmd_check "$window"

        sleep 2
    done
}

# Show status of last action per window
cmd_status() {
    log_info "Auto-rescue status:"

    for worker in $WORKER_WINDOWS; do
        local last_action=$(get_last_action "$worker")
        if [[ "$last_action" == "0" ]]; then
            log_info "  $worker: never triggered"
        else
            local now=$(date +%s)
            local elapsed=$((now - last_action))
            log_info "  $worker: last action ${elapsed}s ago"
        fi
    done
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
        check)
            cmd_check "$@"
            ;;
        run|monitor)
            cmd_run "$@"
            ;;
        status|state)
            cmd_status
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
