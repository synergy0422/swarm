#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# AI Swarm - 2-Window Layout Script (V1.92)
# Creates 2 tmux windows:
#   Window 1 (codex-master): codex (50%) + master (50%) - horizontal split
#   Window 2 (workers): worker-0 + worker-1 + worker-2 - equal horizontal split
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
# NOTE: This script has been upgraded to 2-window layout (V1.92).
# The original 5-pane single-window layout is available in git history.
# =============================================================================

# Source configuration and common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_config.sh"
source "${SCRIPT_DIR}/_common.sh"

# Default values
SESSION="${CLAUDE_SESSION:-${SESSION_NAME:-swarm-claude-default}}"
WORKDIR="${SWARM_WORKDIR:-$PWD}"
CODEX_CMD="${CODEX_CMD:-codex --yolo}"
AI_SWARM_DIR="${AI_SWARM_DIR:-/tmp/ai_swarm}"
AI_SWARM_INTERACTIVE="${AI_SWARM_INTERACTIVE:-}"
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

# =============================================================================
# Validate session name (must start with 'swarm-' for tmux collaboration)
# =============================================================================
if [[ ! "$SESSION" =~ ^swarm- ]]; then
    log_error "Session name must start with 'swarm-' for tmux collaboration."
    log_error "Current: $SESSION"
    log_error "Example: --session swarm-my-session"
    exit 1
fi

# Check if session already exists
if tmux has-session -t "$SESSION" 2>/dev/null; then
    log_warn "Session '$SESSION' already exists."
    log_info "Use 'tmux attach -t $SESSION' to connect, or"
    log_info "Run 'tmux kill-session -t $SESSION' to remove it first."
    exit 1
fi

log_info "Creating 2-window tmux session '$SESSION' (V1.92)..."
log_info "Working directory: $WORKDIR"
log_info "AI_SWARM_DIR: $AI_SWARM_DIR"

# Extract cluster_id from session name (format: swarm-{cluster_id})
CLUSTER_ID="${SESSION#swarm-}"

# =============================================================================
# Window 1: codex-master (horizontal split, 50% each)
# =============================================================================
# Create session with first window named "codex-master"
CODEX_PANE=$(tmux new-session -d -P -F '#{pane_id}' -s "$SESSION" -n codex-master -x 200 -y 60)

# =============================================================================
# Environment setup (session-level, after creating session)
# =============================================================================
# Set environment at session level (will be inherited by all windows)
tmux set-environment -t "$SESSION" AI_SWARM_DIR "$AI_SWARM_DIR"
if [[ -n "${AI_SWARM_INTERACTIVE:-}" ]]; then
    tmux set-environment -t "$SESSION" AI_SWARM_INTERACTIVE "$AI_SWARM_INTERACTIVE"
fi
if [[ -n "${LLM_BASE_URL:-}" ]]; then
    tmux set-environment -t "$SESSION" LLM_BASE_URL "$LLM_BASE_URL"
fi
if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    tmux set-environment -t "$SESSION" ANTHROPIC_API_KEY "$ANTHROPIC_API_KEY"
fi

# Split horizontally to create master pane (50% width each)
MASTER_PANE=$(tmux split-window -h -P -F '#{pane_id}' -t "$CODEX_PANE")

# Send startup commands (use --cluster-id for consistency with CLI)
tmux send-keys -t "$CODEX_PANE" "cd \"$WORKDIR\" && export AI_SWARM_DIR=\"$AI_SWARM_DIR\"${AI_SWARM_INTERACTIVE:+ && export AI_SWARM_INTERACTIVE=\"$AI_SWARM_INTERACTIVE\"} && $CODEX_CMD" Enter
tmux send-keys -t "$MASTER_PANE" "cd \"$WORKDIR\" && export AI_SWARM_DIR=\"$AI_SWARM_DIR\"${AI_SWARM_INTERACTIVE:+ && export AI_SWARM_INTERACTIVE=\"$AI_SWARM_INTERACTIVE\"} && python3 -m swarm.cli --cluster-id $CLUSTER_ID master" Enter

# =============================================================================
# Window 2: workers (3 equal horizontal panes)
# =============================================================================
WORKER0_PANE=$(tmux new-window -P -F '#{pane_id}' -t "$SESSION" -n workers -x 200 -y 60)

# Split for worker-1 and worker-2 (equal 33% each)
WORKER1_PANE=$(tmux split-window -h -P -F '#{pane_id}' -t "$WORKER0_PANE")
WORKER2_PANE=$(tmux split-window -h -P -F '#{pane_id}' -t "$WORKER1_PANE")

# Apply even-horizontal layout to ensure equal distribution
tmux select-layout -t "$SESSION:workers" even-horizontal

# Send startup commands (use --cluster-id and --id for consistency with CLI)
tmux send-keys -t "$WORKER0_PANE" "cd \"$WORKDIR\" && export AI_SWARM_DIR=\"$AI_SWARM_DIR\"${AI_SWARM_INTERACTIVE:+ && export AI_SWARM_INTERACTIVE=\"$AI_SWARM_INTERACTIVE\"} && python3 -m swarm.cli --cluster-id $CLUSTER_ID worker --id 0" Enter
tmux send-keys -t "$WORKER1_PANE" "cd \"$WORKDIR\" && export AI_SWARM_DIR=\"$AI_SWARM_DIR\"${AI_SWARM_INTERACTIVE:+ && export AI_SWARM_INTERACTIVE=\"$AI_SWARM_INTERACTIVE\"} && python3 -m swarm.cli --cluster-id $CLUSTER_ID worker --id 1" Enter
tmux send-keys -t "$WORKER2_PANE" "cd \"$WORKDIR\" && export AI_SWARM_DIR=\"$AI_SWARM_DIR\"${AI_SWARM_INTERACTIVE:+ && export AI_SWARM_INTERACTIVE=\"$AI_SWARM_INTERACTIVE\"} && python3 -m swarm.cli --cluster-id $CLUSTER_ID worker --id 2" Enter

# Select codex pane as starting point
tmux select-pane -t "$CODEX_PANE"

# =============================================================================
# Layout verification
# =============================================================================
log_info "Verifying layout..."

# Check window 1 (codex-master) has 2 panes
WINDOW1_PANES=$(tmux list-panes -t "$SESSION:codex-master" 2>/dev/null | wc -l)
if [[ "$WINDOW1_PANES" -eq 2 ]]; then
    log_info "Window 1 (codex-master): 2 panes verified"
else
    log_warn "Window 1 expected 2 panes, found $WINDOW1_PANES"
fi

# Check window 2 (workers) has 3 panes
WINDOW2_PANES=$(tmux list-panes -t "$SESSION:workers" 2>/dev/null | wc -l)
if [[ "$WINDOW2_PANES" -eq 3 ]]; then
    log_info "Window 2 (workers): 3 panes verified"
else
    log_warn "Window 2 expected 3 panes, found $WINDOW2_PANES"
fi

# =============================================================================
# Output for Bridge configuration
# =============================================================================
log_info ""
log_info "=============================================="
log_info "Bridge Configuration (IMPORTANT):"
log_info "=============================================="
log_info "Codex pane ID: $CODEX_PANE"
log_info ""
log_info "To run Bridge, set the environment variable:"
log_info "  export AI_SWARM_BRIDGE_PANE=$CODEX_PANE"
log_info ""
log_info "Then start Bridge:"
log_info "  AI_SWARM_INTERACTIVE=1 ./scripts/swarm_bridge.sh start"
log_info "=============================================="
log_info ""

log_info "Session created successfully!"
log_info "2 windows: codex-master (2 panes) + workers (3 panes)"
log_info ""
log_info "Commands:"
log_info "  Attach:   tmux attach -t $SESSION"
log_info "  Status:   tmux list-panes -t $SESSION:codex-master"
log_info "  Kill:     tmux kill-session -t $SESSION"

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
AI Swarm - 2-Window Layout Script (V1.92)

Creates 2 tmux windows:
  - Window 1 (codex-master): codex (50%) + master (50%) - horizontal split
  - Window 2 (workers): worker-0 + worker-1 + worker-2 - equal horizontal split

Usage: $0 [OPTIONS]

Options:
  --session, -s NAME     tmux session name (default: swarm-claude-default)
  --workdir, -d DIR      working directory (default: current directory)
  --codex-cmd, -c CMD    codex command to run in codex pane (default: "codex --yolo")
  --attach, -a           attach to tmux session after creation (default)
  --no-attach            create session but don't attach
  --help, -h             show this help message

Environment variables:
  CLAUDE_SESSION         session name override
  SWARM_WORKDIR          default working directory override
  CODEX_CMD              codex command override

Examples:
  # Basic usage
  $0

  # Create and attach
  $0 --attach

  # Custom session name
  $0 --session my-session

  # Custom working directory
  $0 --workdir /path/to/project

Window layout:
  Window 1 (codex-master):
    ┌─────────────────────┬────────────────────────────┐
    │                     │                            │
    │        codex        │          master            │
    │                     │                            │
    └─────────────────────┴────────────────────────────┘

  Window 2 (workers):
    ┌───────────────┬───────────────┬───────────────┐
    │               │               │               │
    │    worker-0   │    worker-1   │    worker-2   │
    │               │               │               │
    └───────────────┴───────────────┴───────────────┘

Bridge Setup:
  After running this script, set AI_SWARM_BRIDGE_PANE to the codex pane ID
  (output at the end of script execution), then start Bridge.
EOF
}
