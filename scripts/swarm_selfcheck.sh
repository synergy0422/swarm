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

# Check tmux availability and version
check_tmux() {
    print_info "Checking tmux availability..."

    if command -v tmux &>/dev/null; then
        local version
        version=$(tmux -V 2>/dev/null || echo "unknown")
        print_pass "tmux is installed ($version)"
        return 0
    else
        print_fail "tmux not found"
        print_info "Install tmux: apt install tmux | brew install tmux"
        return 1
    fi
}

# Check script executability
check_scripts() {
    print_info "Checking script executability..."

    local failed_scripts=()
    local script_count=0

    for script in "${CORE_SCRIPTS[@]}"; do
        # Skip this script itself
        [[ "$script" == "${BASH_SOURCE[0]}" ]] && continue

        if [[ -f "$script" ]]; then
            script_count=$((script_count + 1))
            if [[ ! -x "$script" ]]; then
                failed_scripts+=("$script")
            fi
        fi
    done

    if [[ ${#failed_scripts[@]} -eq 0 ]]; then
        print_pass "All $script_count scripts are executable"
        return 0
    else
        print_fail "The following scripts are not executable:"
        for script in "${failed_scripts[@]}"; do
            echo "  - $script" >&2
        done
        print_info "Run: chmod +x scripts/<script_name>"
        return 1
    fi
}

# Check configuration files
check_config() {
    print_info "Checking configuration files..."

    local failed=0

    # Check _config.sh
    if [[ -r "$SCRIPT_DIR/_config.sh" ]]; then
        print_pass "_config.sh is readable"
    else
        print_fail "_config.sh not found or not readable"
        failed=1
    fi

    # Check _common.sh
    if [[ -r "$SCRIPT_DIR/_common.sh" ]]; then
        print_pass "_common.sh is readable"
    else
        print_fail "_common.sh not found or not readable"
        failed=1
    fi

    # Check SWARM_STATE_DIR is set
    if [[ -n "${SWARM_STATE_DIR:-}" ]]; then
        print_pass "SWARM_STATE_DIR is set ($SWARM_STATE_DIR)"
    else
        print_fail "SWARM_STATE_DIR is not set"
        print_info "Check _config.sh for SWARM_STATE_DIR configuration"
        failed=1
    fi

    # Check SWARM_STATE_DIR exists and is writable
    if [[ -n "${SWARM_STATE_DIR:-}" ]]; then
        if [[ -d "$SWARM_STATE_DIR" ]]; then
            if [[ -w "$SWARM_STATE_DIR" ]]; then
                print_pass "State directory is writable"
            else
                print_fail "State directory exists but is not writable: $SWARM_STATE_DIR"
                print_info "Fix permissions: chmod u+w $SWARM_STATE_DIR"
                failed=1
            fi
        else
            print_fail "State directory does not exist: $SWARM_STATE_DIR"
            print_info "Create directory: mkdir -p $SWARM_STATE_DIR"
            failed=1
        fi
    fi

    return $failed
}

# Check state directory structure
check_state_dir() {
    print_info "Checking state directory structure..."

    if [[ -z "${SWARM_STATE_DIR:-}" ]]; then
        print_fail "SWARM_STATE_DIR not set, cannot check state directory structure"
        return 1
    fi

    local failed=0

    # Check if we can create locks directory
    local lock_dir="$SWARM_STATE_DIR/locks"
    if [[ -d "$lock_dir" ]]; then
        if [[ -w "$lock_dir" ]]; then
            print_pass "Locks directory is writable ($lock_dir)"
        else
            print_fail "Locks directory exists but is not writable: $lock_dir"
            print_info "Fix permissions: chmod u+w $lock_dir"
            failed=1
        fi
    else
        # Try to create it
        if mkdir -p "$lock_dir" 2>/dev/null; then
            print_pass "Locks directory created ($lock_dir)"
        else
            print_fail "Cannot create locks directory: $lock_dir"
            print_info "Check parent directory permissions"
            failed=1
        fi
    fi

    # Check if we can write to status.log
    local status_file="$SWARM_STATE_DIR/status.log"
    if [[ -f "$status_file" ]]; then
        if [[ -w "$status_file" ]]; then
            print_pass "Status log is writable ($status_file)"
        else
            print_fail "Status log exists but is not writable: $status_file"
            print_info "Fix permissions: chmod u+w $status_file"
            failed=1
        fi
    else
        # Try to create it
        if touch "$status_file" 2>/dev/null; then
            print_pass "Status log created ($status_file)"
            # Clean up the empty file we just created
            rm -f "$status_file" 2>/dev/null || true
        else
            print_fail "Cannot create status log: $status_file"
            print_info "Check directory permissions"
            failed=1
        fi
    fi

    return $failed
}
