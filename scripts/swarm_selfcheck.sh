#!/bin/bash
set -euo pipefail

# Determine script directory (handles symlinks and bash -c)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# Source _common.sh for SWARM_STATE_DIR configuration
# shellcheck source=scripts/_common.sh
if [[ -f "$SCRIPT_DIR/_common.sh" ]]; then
    source "$SCRIPT_DIR/_common.sh"
else
    echo "[ERROR] Failed to source _common.sh from $SCRIPT_DIR" >&2
    exit 1
fi

# Print pass message (suppressed in quiet mode)
print_pass() {
    [[ "${QUIET_MODE:-0}" == "1" ]] && return 0
    echo "[PASS] $*" >&2
}

# Print fail message (always shown, even in quiet mode)
print_fail() {
    echo "[FAIL] $*" >&2
}

# Print info message (only in verbose mode)
print_info() {
    [[ "${VERBOSE_MODE:-0}" == "1" ]] && echo "[INFO] $*" >&2
}

# Usage information
usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Run system health checks for AI Swarm environment.

Options:
    -v, --verbose    Show detailed check output
    -q, --quiet      Only report failures
    -h, --help       Show this help message

Checks performed:
    1. tmux availability and version
    2. Core scripts executability
    3. Configuration files readability
    4. State directory accessibility

Exit codes:
    0 - All checks passed
    1 - One or more checks failed

Examples:
    $(basename "$0")              # Run all checks
    $(basename "$0") -v           # Verbose output
    $(basename "$0") -q           # Quiet mode (failures only)
EOF
}

# Parse command-line arguments
VERBOSE_MODE=0
QUIET_MODE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--verbose)
            VERBOSE_MODE=1
            shift
            ;;
        -q|--quiet)
            QUIET_MODE=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

# Define script lists
CORE_SCRIPTS=(
    "$SCRIPT_DIR/swarm_lock.sh"
    "$SCRIPT_DIR/swarm_status_log.sh"
    "$SCRIPT_DIR/swarm_task_wrap.sh"
    "$SCRIPT_DIR/sworm-start.sh"
    "$SCRIPT_DIR/sworm-stop.sh"
    "$SCRIPT_DIR/worker.sh"
)

CONFIG_FILES=(
    "$SCRIPT_DIR/_config.sh"
    "$SCRIPT_DIR/_common.sh"
)
