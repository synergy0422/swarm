#!/usr/bin/env bash
set -euo pipefail

# Claude Bridge Launch Script
# Environment variables:
#   AI_SWARM_BRIDGE_SESSION    tmux session name (default: swarm-claude-default)
#   AI_SWARM_BRIDGE_WINDOW      tmux window name (default: codex-master)
#   AI_SWARM_BRIDGE_PANE        tmux pane_id (highest priority)
#   AI_SWARM_BRIDGE_POLL_INTERVAL   poll interval in seconds
#   AI_SWARM_BRIDGE_LINES      capture-pane lines
#   AI_SWARM_DIR               swarm state directory
#   AI_SWARM_INTERACTIVE        must be "1"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log_info() { echo "[$(date +%H:%M:%S)][Bridge] $*"; }
log_error() { echo "[$(date +%H:%M:%S)][Bridge][ERROR] $*" >&2; }

usage() {
    cat << EOF
Usage: $(basename "$0") <command>

Claude Master Window Bridge - Monitor master window and dispatch tasks.

Commands:
  start    Start bridge process
  stop     Stop bridge process
  status   Check bridge running status

Environment:
  AI_SWARM_DIR                   swarm state directory (default: /tmp/ai_swarm)
  AI_SWARM_BRIDGE_SESSION       tmux session (default: swarm-claude-default)
  AI_SWARM_BRIDGE_WINDOW        tmux window running Claude Code (default: codex-master)
  AI_SWARM_BRIDGE_PANE         tmux pane_id (highest priority, recommended)
  AI_SWARM_BRIDGE_LINES        capture-pane lines (default: 200)
  AI_SWARM_BRIDGE_POLL_INTERVAL   poll interval seconds (default: 1.0)
  AI_SWARM_INTERACTIVE         must be "1"

Important: AI_SWARM_BRIDGE_WINDOW or AI_SWARM_BRIDGE_PANE must point to the
window/pane running Claude Code (where you type /task commands). Do NOT point
to the window running "python3 -m swarm.cli master" - that would inject
keystrokes into the master process input.

Examples:
  # Start with default config (assumes 'codex-master' window runs Claude Code)
  AI_SWARM_INTERACTIVE=1 ./scripts/swarm_bridge.sh start

  # Specify session and Claude Code window
  AI_SWARM_BRIDGE_SESSION=my-swarm AI_SWARM_BRIDGE_WINDOW=main \\
    AI_SWARM_INTERACTIVE=1 ./scripts/swarm_bridge.sh start

  # Use specific pane ID (recommended - most reliable)
  AI_SWARM_BRIDGE_PANE=$TMUX_PANE AI_SWARM_INTERACTIVE=1 ./scripts/swarm_bridge.sh start

EOF
}

# Get AI_SWARM_DIR (create if not exists)
get_ai_swarm_dir() {
    echo "${AI_SWARM_DIR:-/tmp/ai_swarm}"
}

cmd_start() {
    local ai_swarm_dir
    ai_swarm_dir=$(get_ai_swarm_dir)

    # Ensure directory exists
    mkdir -p "$ai_swarm_dir"

    local pid_file="$ai_swarm_dir/bridge.pid"

    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_error "Bridge already running (PID: $pid)"
            exit 1
        fi
        rm -f "$pid_file"
    fi

    # Check AI_SWARM_INTERACTIVE is set
    if [[ "${AI_SWARM_INTERACTIVE:-}" != "1" ]]; then
        log_error "AI_SWARM_INTERACTIVE=1 required"
        log_error "Set environment variable: export AI_SWARM_INTERACTIVE=1"
        exit 1
    fi

    # Check tmux session exists
    local session="${AI_SWARM_BRIDGE_SESSION:-swarm-default}"
    if ! tmux has-session -t "$session" 2>/dev/null; then
        log_error "tmux session not found: $session"
        log_error "Create session first or set AI_SWARM_BRIDGE_SESSION"
        exit 1
    fi

    log_info "Starting bridge (session=$session, lines=${AI_SWARM_BRIDGE_LINES:-200})..."

    python3 -m swarm.claude_bridge &
    local bridge_pid=$!

    # Brief wait and verify process is alive (avoid zombie PID file)
    sleep 0.5
    if ! kill -0 "$bridge_pid" 2>/dev/null; then
        rm -f "$pid_file"
        log_error "Bridge failed to start (check AI_SWARM_INTERACTIVE=1 and FIFO exists)"
        exit 1
    fi

    echo "$bridge_pid" > "$pid_file"
    log_info "Bridge started (PID: $bridge_pid, PID_FILE: $pid_file)"
}

cmd_stop() {
    local ai_swarm_dir
    ai_swarm_dir=$(get_ai_swarm_dir)
    local pid_file="$ai_swarm_dir/bridge.pid"

    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping bridge (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            rm -f "$pid_file"
            log_info "Bridge stopped"
        else
            log_info "Bridge not running (stale PID file)"
            rm -f "$pid_file"
        fi
    else
        log_info "Bridge not running (no PID file)"
    fi
}

cmd_status() {
    local ai_swarm_dir
    ai_swarm_dir=$(get_ai_swarm_dir)
    local pid_file="$ai_swarm_dir/bridge.pid"

    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Bridge running (PID: $pid)"
            return 0
        else
            echo "Bridge not running (stale PID file)"
            return 1
        fi
    else
        echo "Bridge not running"
        return 1
    fi
}

# Main
case "${1:-}" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    status)
        cmd_status
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        if [[ -n "${1:-}" ]]; then
            log_error "Unknown command: $1"
        fi
        usage
        exit 1
        ;;
esac
