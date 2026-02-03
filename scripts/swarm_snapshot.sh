#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Snapshot Script - Diagnostic snapshot collection for AI Swarm
# =============================================================================
# A read-only script that captures tmux swarm runtime state to a timestamped
# directory. Never writes to SWARM_STATE_DIR.
# =============================================================================

# Determine script directory (handles symlinks and bash -c)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# Source _common.sh for configuration
# shellcheck source=scripts/_common.sh
if [[ -f "$SCRIPT_DIR/_common.sh" ]]; then
    source "$SCRIPT_DIR/_common.sh"
else
    echo "[ERROR] Failed to source _common.sh from $SCRIPT_DIR" >&2
    exit 1
fi

# =============================================================================
# Configuration Variables (with defaults)
# =============================================================================
# These can be overridden by command-line arguments or environment variables
SNAPSHOT_LINES="${SNAPSHOT_LINES:-50}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-/tmp/ai_swarm_snapshot_$(date +%Y%m%d_%H%M%S)}"

# Error collection array
declare -a ERRORS=()

# =============================================================================
# Usage Information
# =============================================================================
usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Capture a diagnostic snapshot of the AI Swarm tmux session.

Options:
    -s, --session NAME   tmux session name (default: $SESSION_NAME)
    -n, --lines N        Number of lines per pane to capture (default: 50)
    -o, --out DIR        Output directory (default: /tmp/ai_swarm_snapshot_<timestamp>)
    -h, --help           Show this help message

Examples:
    $(basename "$0")                                    # Default snapshot
    $(basename "$0") --session my-session               # Custom session
    $(basename "$0") --lines 100                        # More lines per pane
    $(basename "$0") --out /path/to/snapshot           # Custom output

Output Directory Structure:
    <snapshot_dir>/
      tmux/           # tmux structure information
        structure.txt # session, window, and pane info
      panes/          # pane outputs with session:window.pane prefix
        <session>.<window>.<pane>.txt
      state/          # state files (read-only copy)
        status.log     # (if exists in SWARM_STATE_DIR)
      locks/          # lock directory listing (read-only)
        list.txt       # (if locks/ exists in SWARM_STATE_DIR)
      meta/           # metadata
        git.txt        # git status and branch info
        summary.txt    # snapshot overview and error summary

Note: This script performs read-only operations only. It never modifies
      SWARM_STATE_DIR or any state files.

EOF
}

# =============================================================================
# Helper Functions
# =============================================================================

# Add error to errors array
add_error() {
    local error_msg="$1"
    ERRORS+=("[$(date +%H:%M:%S)] $error_msg")
}

# =============================================================================
# Snapshot Functions
# =============================================================================

# Check if tmux session exists (read-only)
check_tmux_session() {
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        add_error "tmux: session '$SESSION_NAME' not found"
        return 1
    fi
    return 0
}

# Dump tmux structure for specified session only (read-only)
dump_tmux_structure() {
    local structure_file="$SNAPSHOT_DIR/tmux/structure.txt"

    {
        echo "Session: $SESSION_NAME"
        echo "Time: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        echo ""
        echo "=== Windows ==="

        # List windows for specified session
        tmux list-windows -t "$SESSION_NAME" -F '#{window_index}: #{window_name}' 2>/dev/null | while read -r win_info; do
            local win_index
            win_index=$(echo "$win_info" | cut -d':' -f1)
            echo "Window: $win_info"
            echo "  Panes:"

            # List panes for this window
            tmux list-panes -t "$SESSION_NAME:$win_index" -F '    #{pane_index}: #{pane_title}' 2>/dev/null | while read -r pane_info; do
                echo "  $pane_info"
            done
        done

        echo ""
        echo "=== Raw Structure ==="
        tmux list-windows -t "$SESSION_NAME" -F '#{window_index} #{window_name} #{window_layout}'
    } > "$structure_file" 2>/dev/null

    if [[ ! -s "$structure_file" ]]; then
        add_error "tmux structure: failed to capture"
    fi
}

# Dump pane output with prefix (read-only)
dump_pane_output() {
    local pane_count=0

    # Get all panes in the session
    mapfile -t panes < <(tmux list-panes -t "$SESSION_NAME" -F '#{window_index}.#{pane_index}' 2>/dev/null)

    for pane in "${panes[@]}"; do
        local win_idx pane_idx
        win_idx=$(echo "$pane" | cut -d'.' -f1)
        pane_idx=$(echo "$pane" | cut -d'.' -f2)

        local pane_file="$SNAPSHOT_DIR/panes/${SESSION_NAME}.${win_idx}.${pane_idx}.txt"

        {
            echo "[${SESSION_NAME}:${win_idx}.${pane_idx}] === PANE CAPTURE START ==="
            tmux capture-pane -p -t "$SESSION_NAME:$win_idx.$pane_idx" 2>/dev/null | \
                tail -n "$SNAPSHOT_LINES" | \
                sed "s/^/[${SESSION_NAME}:${win_idx}.${pane_idx}] /"
            echo "[${SESSION_NAME}:${win_idx}.${pane_idx}] === PANE CAPTURE END ==="
        } > "$pane_file"

        pane_count=$((pane_count + 1))
    done

    if [[ $pane_count -eq 0 ]]; then
        add_error "panes: no panes found in session '$SESSION_NAME'"
    fi
}

# Read-only copy of state files
dump_state_files() {
    local status_log="$SWARM_STATE_DIR/status.log"
    local output_file="$SNAPSHOT_DIR/state/status.log"

    if [[ -f "$status_log" ]]; then
        if cp "$status_log" "$output_file" 2>/dev/null; then
            echo "Copied: $status_log -> $output_file"
        else
            add_error "state: failed to copy status.log"
        fi
    else
        # status.log is optional - just note it doesn't exist
        {
            echo "NOT FOUND: $status_log"
            echo "Reason: File does not exist in SWARM_STATE_DIR"
        } > "$output_file"
        # Do NOT add error - this file is optional
    fi
}

# Read-only listing of locks directory
dump_locks() {
    local locks_dir="$SWARM_STATE_DIR/locks"
    local output_file="$SNAPSHOT_DIR/locks/list.txt"

    if [[ -d "$locks_dir" ]]; then
        if ls -la "$locks_dir" > "$output_file" 2>/dev/null; then
            echo "Copied: $locks_dir -> $output_file"
        else
            add_error "locks: failed to list locks directory"
        fi
    else
        # locks directory is optional - just note it doesn't exist
        {
            echo "NOT FOUND: $locks_dir"
            echo "Reason: Directory does not exist in SWARM_STATE_DIR"
        } > "$output_file"
        # Do NOT add error - this directory is optional
    fi
}

# Dump git information (read-only)
dump_git_info() {
    local git_file="$SNAPSHOT_DIR/meta/git.txt"

    {
        echo "Git Information"
        echo "==============="
        echo "Captured: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        echo ""
        echo "Commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
        echo "Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
        echo ""
        echo "Status (--porcelain):"
        git status --porcelain 2>/dev/null || echo "Not a git repository or git error"
        echo ""
        echo "Last 3 commits:"
        git log --oneline -3 2>/dev/null || echo "Unable to get commit history"
    } > "$git_file"
}

# Generate summary file
generate_summary() {
    local summary_file="$SNAPSHOT_DIR/meta/summary.txt"
    local pane_count
    pane_count=$(find "$SNAPSHOT_DIR/panes" -name "*.txt" 2>/dev/null | wc -l)

    {
        echo "Snapshot Summary"
        echo "================"
        echo "Snapshot: $SNAPSHOT_DIR"
        echo "Session: $SESSION_NAME"
        echo "Panes: $pane_count"
        echo "Time: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        echo ""
        echo "Files:"
        echo "  - tmux/structure.txt"
        echo "  - panes/*.txt ($pane_count files)"
        [[ -f "$SNAPSHOT_DIR/state/status.log" ]] && echo "  - state/status.log"
        [[ -f "$SNAPSHOT_DIR/locks/list.txt" ]] && echo "  - locks/list.txt"
        echo "  - meta/git.txt"
        echo "  - meta/summary.txt"
        echo ""

        # Error section
        if [[ ${#ERRORS[@]} -gt 0 ]]; then
            echo "Errors: ${#ERRORS[@]}"
            for error in "${ERRORS[@]}"; do
                echo "  - $error"
            done
        else
            echo "Errors: none"
        fi
    } > "$summary_file"
}

# =============================================================================
# Main Function
# =============================================================================
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -s|--session)
                SESSION_NAME="${2:-}"
                if [[ -z "$SESSION_NAME" ]]; then
                    echo "Error: --session requires a value" >&2
                    exit 1
                fi
                shift 2
                ;;
            -n|--lines)
                SNAPSHOT_LINES="${2:-}"
                if [[ -z "$SNAPSHOT_LINES" ]]; then
                    echo "Error: --lines requires a value" >&2
                    exit 1
                fi
                # Validate it's a number
                if ! [[ "$SNAPSHOT_LINES" =~ ^[0-9]+$ ]]; then
                    echo "Error: --lines must be a number" >&2
                    exit 1
                fi
                shift 2
                ;;
            -o|--out)
                local user_dir="${2:-}"
                if [[ -z "$user_dir" ]]; then
                    echo "Error: --out requires a value" >&2
                    exit 1
                fi
                # If directory exists, append timestamp
                if [[ -d "$user_dir" ]]; then
                    SNAPSHOT_DIR="${user_dir}_$(date +%Y%m%d_%H%M%S)"
                else
                    SNAPSHOT_DIR="$user_dir"
                fi
                shift 2
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

    echo "Creating snapshot for session: $SESSION_NAME"
    echo "Output directory: $SNAPSHOT_DIR"
    echo ""

    # Create output directory structure
    mkdir -p "$SNAPSHOT_DIR/tmux" "$SNAPSHOT_DIR/panes" "$SNAPSHOT_DIR/state" "$SNAPSHOT_DIR/locks" "$SNAPSHOT_DIR/meta"

    # Check tmux session - fail fast if session doesn't exist
    if ! check_tmux_session; then
        echo "Error: Session '$SESSION_NAME' not found. Cannot create snapshot." >&2
        generate_summary
        exit 1
    fi

    # Run all dump functions (collect errors, don't fail)
    dump_tmux_structure || true
    dump_pane_output || true
    dump_state_files || true
    dump_locks || true
    dump_git_info || true

    # Generate summary
    generate_summary

    # Print final output
    echo ""
    echo "Snapshot complete: $SNAPSHOT_DIR"
    echo "Errors: ${#ERRORS[@]}"

    if [[ ${#ERRORS[@]} -gt 0 ]]; then
        echo ""
        echo "Errors encountered:"
        for error in "${ERRORS[@]}"; do
            echo "  $error"
        done
    fi

    # Return exit code - always 0 since errors are reported in summary
    # Critical errors (session not found) exit earlier at line 320
    exit 0
}

# Execute main with all arguments
main "$@"
