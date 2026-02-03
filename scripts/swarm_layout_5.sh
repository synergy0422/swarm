#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# AI Swarm - 5-Pane Layout Script
# Creates a single tmux window with 5 panes:
#   Left: master (top) + codex (bottom) with configurable vertical split
#   Right: worker-0 + worker-1 + worker-2 equal horizontal split
#
# Usage:
#   ./scripts/swarm_layout_5.sh              # Create session and attach
#   ./scripts/swarm_layout_5.sh --no-attach  # Create only, don't attach
#   ./scripts/swarm_layout_5.sh --attach     # Explicitly attach
#   ./scripts/swarm_layout_5.sh -d /path     # Override working directory
#   ./scripts/swarm_layout_5.sh -s my-session # Use custom session name
#
# Environment variables:
#   CLAUDE_SESSION    - Session name override
#   SWARM_WORKDIR     - Default working directory (default: current directory)
#   CODEX_CMD         - Codex command override (default: "codex --yolo")
# =============================================================================

# Source configuration and common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_config.sh"
source "${SCRIPT_DIR}/_common.sh"

# Default values (can be overridden by parameters or environment variables)
SESSION="${CLAUDE_SESSION:-${SESSION_NAME:-swarm-claude-default}}"
WORKDIR="${SWARM_WORKDIR:-$PWD}"
LEFT_RATIO="${LEFT_RATIO:-50}"
CODEX_CMD="${CODEX_CMD:-codex --yolo}"
ATTACH=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --session|-s)
            if [[ -z "${2:-}" ]]; then
                log_error "--session requires a session name argument"
                exit 1
            fi
            SESSION="$2"
            shift 2
            ;;
        --workdir|-d)
            if [[ -z "${2:-}" ]]; then
                log_error "--workdir requires a directory argument"
                exit 1
            fi
            WORKDIR="$2"
            shift 2
            ;;
        --left-ratio|-l)
            if [[ -z "${2:-}" ]]; then
                log_error "--left-ratio requires a percentage argument (50-80)"
                exit 1
            fi
            LEFT_RATIO="$2"
            shift 2
            ;;
        --codex-cmd|-c)
            if [[ -z "${2:-}" ]]; then
                log_error "--codex-cmd requires a command argument"
                exit 1
            fi
            CODEX_CMD="$2"
            shift 2
            ;;
        --attach|-a)
            ATTACH=true
            shift
            ;;
        --no-attach)
            ATTACH=false
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Dependency check
log_info "Checking dependencies..."
if ! command -v tmux >/dev/null 2>&1; then
    log_error "tmux not found. Please install tmux."
    exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
    log_warn "codex command not found. Install OpenAI Codex or ensure it's in PATH."
fi

# Validate working directory
if [[ ! -d "$WORKDIR" ]]; then
    log_error "Working directory does not exist: $WORKDIR"
    exit 1
fi

# Validate left ratio
if [[ "$LEFT_RATIO" -lt 50 ]] || [[ "$LEFT_RATIO" -gt 80 ]]; then
    log_error "LEFT_RATIO must be between 50 and 80"
    exit 1
fi

# Check if session already exists
if tmux has-session -t "$SESSION" 2>/dev/null; then
    log_warn "Session '$SESSION' already exists."
    log_info "Use 'tmux attach -t $SESSION' to connect, or"
    log_info "Run 'tmux kill-session -t $SESSION' to remove it first."
    exit 1
fi

log_info "Creating 5-pane tmux session '$SESSION'..."
log_info "Working directory: $WORKDIR"
log_info "Left pane ratio: ${LEFT_RATIO}% master, $((100 - LEFT_RATIO))% codex"

# Create new detached session with window name "layout"
# Layout: master/codex on left, 3 workers on right
# Use pane_id capture to ensure correct pane assignment
MASTER_PANE=$(tmux new-session -d -P -F '#{pane_id}' -s "$SESSION" -n layout -x 200 -y 60)

# Create panes using split-window commands with pane_id capture
# This ensures stable pane assignment regardless of split order

# Split horizontally to create right side (worker area)
# Capture the new pane's ID for worker-0
RIGHT_PANE=$(tmux split-window -h -P -F '#{pane_id}' -t "$MASTER_PANE")

# Split right pane vertically twice for 3 workers (without -p to let select-layout handle)
WORKER1_PANE=$(tmux split-window -v -P -F '#{pane_id}' -t "$RIGHT_PANE")
WORKER2_PANE=$(tmux split-window -v -P -F '#{pane_id}' -t "$RIGHT_PANE")

# Ensure right pane workers are equal height using select-layout
tmux select-layout -t "$RIGHT_PANE" even-vertical

# Now split left pane vertically to create codex pane
CODEX_PANE=$(tmux split-window -v -p "$LEFT_RATIO" -P -F '#{pane_id}' -t "$MASTER_PANE")

# Send startup commands to each pane
tmux send-keys -t "$MASTER_PANE" "cd \"$WORKDIR\" && claude" Enter
tmux send-keys -t "$CODEX_PANE" "cd \"$WORKDIR\" && $CODEX_CMD" Enter
tmux send-keys -t "$RIGHT_PANE" "cd \"$WORKDIR\" && claude" Enter
tmux send-keys -t "$WORKER1_PANE" "cd \"$WORKDIR\" && claude" Enter
tmux send-keys -t "$WORKER2_PANE" "cd \"$WORKDIR\" && claude" Enter

# Select master pane as starting point
tmux select-pane -t "$MASTER_PANE"

# Verify layout
PANE_COUNT=$(tmux list-panes -t "$SESSION:0" 2>/dev/null | wc -l)
if [[ "$PANE_COUNT" -eq 5 ]]; then
    log_info "Layout verified: 5 panes created successfully"
else
    log_warn "Expected 5 panes, but found $PANE_COUNT"
fi

log_info "Session created successfully!"
log_info "5 panes: master(codex) + 3 workers"
log_info ""
log_info "Commands:"
log_info "  Attach:   tmux attach -t $SESSION"
log_info "  Status:   tmux list-panes -t $SESSION:layout"
log_info "  Kill:     tmux kill-session -t $SESSION"
log_info ""

# Attach or exit
if [[ "$ATTACH" == true ]]; then
    log_info "Attaching to session..."
    tmux attach-session -t "$SESSION"
else
    log_info "Session ready. Run 'tmux attach -t $SESSION' to connect."
    exit 0
fi

# =============================================================================
# Help function
# =============================================================================
show_help() {
    cat << EOF
AI Swarm - 5-Pane Layout Script

Creates a single tmux window with 5 panes:
  - Left: master (top) + codex (bottom) with configurable split
  - Right: worker-0 + worker-1 + worker-2 equal horizontal split

Usage: $0 [OPTIONS]

Options:
  --session, -s NAME     tmux session name (default: swarm-claude-default)
  --workdir, -d DIR      working directory (default: current directory)
                         默认工作目录为当前目录，可用 --workdir 或 SWARM_WORKDIR 覆盖
  --left-ratio, -l PCT   left pane vertical split percentage 50-80 (default: 50)
  --codex-cmd, -c CMD    codex command to run in codex pane (default: "codex --yolo")
  --attach, -a           attach to tmux session after creation (default)
  --no-attach            create session but don't attach
  --help, -h             show this help message

Environment variables:
  CLAUDE_SESSION         session name override
  SWARM_WORKDIR          default working directory override
  CODEX_CMD              codex command override

Examples:
  # Basic usage (default workdir is current directory)
  $0

  # Create and attach
  $0 --attach

  # Custom session name
  $0 --session my-session

  # Custom working directory
  $0 --workdir /path/to/project

  # Custom codex command
  $0 --codex-cmd "codex --yolo --model o1"

  # Adjust left pane ratio (60% master, 40% codex)
  $0 --left-ratio 60

  # Using environment variables
  SWARM_WORKDIR=/my/project $0
  CODEX_CMD="codex --yolo" $0

Pane layout:
  ┌─────────────────┬────────────────────┐
  │      master     │      worker-0      │
  │                 ├────────────────────┤
  │      codex      │      worker-1      │
  │                 ├────────────────────┤
  │                 │      worker-2      │
  └─────────────────┴────────────────────┘
EOF
}
