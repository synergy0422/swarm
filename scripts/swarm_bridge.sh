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

# Parse a single JSON log entry into key=value pairs
_parse_json_entry() {
    local entry="$1"
    # Parse JSON directly from the input
    local ts=$(python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ts',''))" 2>/dev/null <<< "$entry" || echo "")
    local phase=$(python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('phase',''))" 2>/dev/null <<< "$entry" || echo "")
    local task_id=$(python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('bridge_task_id',''))" 2>/dev/null <<< "$entry" || echo "")
    local worker=$(python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('target_worker',''))" 2>/dev/null <<< "$entry" || echo "")
    local attempt=$(python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('attempt',''))" 2>/dev/null <<< "$entry" || echo "")
    local latency=$(python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('latency_ms',''))" 2>/dev/null <<< "$entry" || echo "")
    local task_preview=$(python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('task_preview','')[:40])" 2>/dev/null <<< "$entry" || echo "")
    echo "$ts|$phase|$task_id|$worker|$attempt|$latency|$task_preview"
}

# Convert legacy line format to parsed entry
_legacy_to_parsed() {
    local line="$1"
    # Legacy format: [2026-02-06 10:00:00] status_message
    local ts=$(echo "$line" | sed -n 's/^\[\([0-9-]* [0-9:]*\)\].*/\1/p')
    local status=$(echo "$line" | sed 's/.*\] *//')
    local phase="$status"
    local task_id=""
    local worker=""
    local attempt="1"
    local latency=""
    local task_preview=""
    echo "$ts|$phase|$task_id|$worker|$attempt|$latency|$task_preview"
}

# Parse a log line (JSON or legacy) into fields
_parse_log_line() {
    local line="$1"
    # Check if line starts with { (JSON format)
    if [[ "$line" == \{* ]]; then
        _parse_json_entry "$line" || echo "|| || ||||"
    else
        _legacy_to_parsed "$line" || echo "|| || ||||"
    fi
}

# bridge-status command: Analyze bridge.log for dispatch lifecycle
cmd_bridge_status() {
    local ai_swarm_dir
    ai_swarm_dir=$(get_ai_swarm_dir)
    local log_file="$ai_swarm_dir/bridge.log"

    # Default options
    local show_recent=10
    local show_failed=false
    local filter_task_id=""
    local filter_phase=""
    local output_json=false

    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --recent)
                show_recent="$2"
                shift 2
                ;;
            --failed)
                show_failed=true
                shift
                ;;
            --task)
                filter_task_id="$2"
                shift 2
                ;;
            --phase)
                filter_phase="$2"
                shift 2
                ;;
            --json)
                output_json=true
                shift
                ;;
            *)
                echo "Unknown option: $1" >&2
                return 1
                ;;
        esac
    done

    if [[ ! -f "$log_file" ]]; then
        echo "No bridge.log found at: $log_file"
        return 1
    fi

    # Read all entries
    local entries=()
    while IFS= read -r line; do
        [[ -n "$line" ]] && entries+=("$line")
    done < <(tac "$log_file" 2>/dev/null || cat "$log_file" | tail -r)

    # Filter entries
    local filtered=()
    for entry in "${entries[@]}"; do
        local parsed
        parsed=$(_parse_log_line "$entry")

        # Extract fields
        local ts phase task_id worker attempt latency task_preview
        IFS='|' read -r ts phase task_id worker attempt latency task_preview <<< "$parsed"

        # Apply filters
        if [[ -n "$filter_task_id" ]] && [[ "$task_id" != *"$filter_task_id"* ]]; then
            continue
        fi
        if [[ -n "$filter_phase" ]] && [[ "$phase" != *"$filter_phase"* ]]; then
            continue
        fi
        if [[ "$show_failed" == true ]] && [[ "$phase" != "FAILED" ]] && [[ "$phase" != "RETRY" ]]; then
            continue
        fi

        # Store as JSON entry (for JSON output) and parsed fields (for display)
        # For display, use parsed fields only; for JSON, store the original entry
        if [[ "$output_json" == true ]]; then
            filtered+=("$entry|$ts|$phase|$task_id|$worker|$attempt|$latency|$task_preview")
        else
            # For display, store only parsed fields (no original entry)
            filtered+=("||$ts|$phase|$task_id|$worker|$attempt|$latency|$task_preview")
        fi
    done

    # Limit recent count (if not filtering by specific task)
    if [[ -z "$filter_task_id" ]] && [[ ${#filtered[@]} -gt $show_recent ]]; then
        filtered=("${filtered[@]:0:$show_recent}")
    fi

    # Output
    if [[ "$output_json" == true ]]; then
        # JSON output for piping
        echo "{"
        echo "  \"entries\": ["
        local first=true
        for item in "${filtered[@]}"; do
            # Extract original entry (everything before the second |)
            local entry="${item%%|*}"
            if [[ "$first" == true ]]; then
                first=false
            else
                echo ","
            fi
            echo -n "    $entry"
        done
        echo ""
        echo "  ],"
        echo "  \"total\": ${#filtered[@]}"
        echo "}"
    else
        # Human-readable table
        printf "%-20s %-10s %-18s %-8s %-7s %-10s %s\n" \
            "TS" "PHASE" "BRIDGE_TASK_ID" "WORKER" "ATTEMPT" "LATENCY" "TASK"
        printf "%-20s %-10s %-18s %-8s %-7s %-10s %s\n" \
            "--------------------" "----------" "------------------" "--------" "-------" "----------" "----"

        for item in "${filtered[@]}"; do
            # Extract parsed fields (skip the empty first field)
            # Remove everything up to and including the first |
            local fields="${item#|}"
            fields="${fields#|}"
            local ts phase task_id worker attempt latency task_preview
            IFS='|' read -r ts phase task_id worker attempt latency task_preview <<< "$fields"

            # Handle empty fields
            [[ -z "$ts" ]] && ts="-"
            [[ -z "$phase" ]] && phase="-"
            [[ -z "$task_id" ]] && task_id="-"
            [[ -z "$worker" ]] && worker="-"
            [[ -z "$attempt" ]] && attempt="-"
            [[ -z "$latency" ]] && latency="-"
            [[ -z "$task_preview" ]] && task_preview="-"

            # Color coding for phases
            local phase_display="$phase"
            case "$phase" in
                FAILED)
                    phase_display=$(printf '\033[31m%s\033[0m' "$phase")  # Red
                    ;;
                RETRY)
                    phase_display=$(printf '\033[33m%s\033[0m' "$phase")  # Yellow
                    ;;
                ACKED)
                    phase_display=$(printf '\033[32m%s\033[0m' "$phase")  # Green
                    ;;
                DISPATCHED)
                    phase_display=$(printf '\033[36m%s\033[0m' "$phase")  # Cyan
                    ;;
            esac

            printf "%-20s %-10s %-18s %-8s %-7s %-10s %s\n" \
                "$ts" "$phase_display" "$task_id" "$worker" "$attempt" "$latency" "$task_preview"
        done

        echo ""
        echo "Total entries: ${#filtered[@]}"
    fi
}

# bridge-dashboard command: Real-time monitoring of bridge status
cmd_bridge_dashboard() {
    local ai_swarm_dir
    ai_swarm_dir=$(get_ai_swarm_dir)
    local log_file="$ai_swarm_dir/bridge.log"
    local pid_file="$ai_swarm_dir/bridge.pid"

    local watch_mode=false
    local refresh_interval=30

    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --watch)
                watch_mode=true
                shift
                ;;
            *)
                echo "Unknown option: $1" >&2
                return 1
                ;;
        esac
    done

    _render_dashboard() {
        echo "=============================================="
        echo "         BRIDGE DASHBOARD"
        echo "=============================================="
        echo ""

        # Bridge running status
        echo "=== BRIDGE STATUS ==="
        if [[ -f "$pid_file" ]]; then
            local pid
            pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                # Calculate uptime
                local start_time
                start_time=$(stat -c %Y "$pid_file" 2>/dev/null || stat -f %m "$pid_file" 2>/dev/null)
                local now
                now=$(date +%s)
                local uptime_seconds=$((now - start_time))
                local uptime_min=$((uptime_seconds / 60))
                local uptime_sec=$((uptime_seconds % 60))

                printf "  Status:     \033[32mRUNNING\033[0m\n"
                printf "  PID:        %s\n" "$pid"
                printf "  Uptime:     %d min %d sec\n" "$uptime_min" "$uptime_sec"
            else
                printf "  Status:     \033[31mNOT RUNNING\033[0m (stale PID file)\n"
            fi
        else
            printf "  Status:     \033[31mNOT RUNNING\033[0m (no PID file)\n"
        fi
        echo ""

        # Statistics from log
        echo "=== DISPATCH STATISTICS ==="
        if [[ -f "$log_file" ]]; then
            local total_entries=$(wc -l < "$log_file" | tr -d ' ')

            # Use proper operator precedence with subshell
            dispatched=$(grep -c '"phase":"DISPATCHED"' "$log_file" 2>/dev/null || true)
            [[ -z "$dispatched" ]] && dispatched=0
            dispatched=$(echo "$dispatched" | tr -d '\n\r')

            acked=$(grep -c '"phase":"ACKED"' "$log_file" 2>/dev/null || true)
            [[ -z "$acked" ]] && acked=0
            acked=$(echo "$acked" | tr -d '\n\r')

            failed=$(grep -c '"phase":"FAILED"' "$log_file" 2>/dev/null || true)
            [[ -z "$failed" ]] && failed=0
            failed=$(echo "$failed" | tr -d '\n\r')

            retry=$(grep -c '"phase":"RETRY"' "$log_file" 2>/dev/null || true)
            [[ -z "$retry" ]] && retry=0
            retry=$(echo "$retry" | tr -d '\n\r')

            # Legacy format fallback
            if [[ "$dispatched" == "0" ]] && [[ "$acked" == "0" ]]; then
                dispatched=$(grep -c 'DISPATCHED' "$log_file" 2>/dev/null || true)
                [[ -z "$dispatched" ]] && dispatched=0
                dispatched=$(echo "$dispatched" | tr -d '\n\r')

                acked=$(grep -c 'ACKED' "$log_file" 2>/dev/null || true)
                [[ -z "$acked" ]] && acked=0
                acked=$(echo "$acked" | tr -d '\n\r')

                failed=$(grep -c 'FAILED' "$log_file" 2>/dev/null || true)
                [[ -z "$failed" ]] && failed=0
                failed=$(echo "$failed" | tr -d '\n\r')

                retry=$(grep -c 'RETRY' "$log_file" 2>/dev/null || true)
                [[ -z "$retry" ]] && retry=0
                retry=$(echo "$retry" | tr -d '\n\r')
            fi

            local success_rate=0
            if [[ $((dispatched + acked)) -gt 0 ]]; then
                success_rate=$((acked * 100 / (dispatched + acked)))
            fi

            printf "  Total Log Entries:  %d\n" "$total_entries"
            printf "  Dispatched:         %d\n" "$dispatched"
            printf "  Acknowledged:       %d\n" "$acked"
            printf "  Retries:            %d\n" "$retry"
            printf "  Failed:             %d\n" "$failed"
            printf "  Success Rate:       %d%%\n" "$success_rate"
        else
            echo "  No log file found"
        fi
        echo ""

        # Last error
        echo "=== LAST ERROR ==="
        if [[ -f "$log_file" ]]; then
            local last_error=$(grep -E '"phase":"FAILED"|"phase":"RETRY"' "$log_file" | tail -1 2>/dev/null || echo "")
            if [[ -z "$last_error" ]]; then
                # Check legacy format
                last_error=$(grep -E 'FAILED|RETRY' "$log_file" | tail -1 2>/dev/null || echo "")
            fi

            if [[ -n "$last_error" ]]; then
                # Extract task_id and reason if available
                local error_task_id=$(echo "$last_error" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('bridge_task_id', 'N/A'))" 2>/dev/null || echo "N/A")
                local error_reason=$(echo "$last_error" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('reason', d.get('phase', 'Unknown')))" 2>/dev/null || echo "Unknown")

                printf "  Task ID:    %s\n" "$error_task_id"
                printf "  Error:      %s\n" "$error_reason"
                printf "  Log:        %s\n" "$last_error"
            else
                echo "  No recent errors"
            fi
        else
            echo "  No log file found"
        fi
        echo ""

        # Active dispatches (recent DISPATCHED without ACK)
        echo "=== POTENTIALLY STUCK DISPATCHES ==="
        if [[ -f "$log_file" ]]; then
            # Find DISPATCHED entries without matching ACKED
            local stuck=$(tail -50 "$log_file" 2>/dev/null | grep -B5 -A5 '"phase":"DISPATCHED"' | grep -v '"phase":"ACKED"' | grep -v "DISPATCHED.*DISPATCHED" | head -5 || echo "")

            if [[ -n "$stuck" ]]; then
                echo "$stuck" | head -3 | while read -r line; do
                    printf "  \033[33m%s\033[0m\n" "$line"
                done
            else
                echo "  No stuck dispatches detected"
            fi
        else
            echo "  No log file found"
        fi
        echo ""

        # Recent activity
        echo "=== RECENT ACTIVITY (Last 5) ==="
        if [[ -f "$log_file" ]]; then
            tail -5 "$log_file" 2>/dev/null | while read -r line; do
                # Color by phase
                if [[ "$line" == *'"phase":"FAILED"'* ]]; then
                    printf "  \033[31m%s\033[0m\n" "$line"
                elif [[ "$line" == *'"phase":"RETRY"'* ]]; then
                    printf "  \033[33m%s\033[0m\n" "$line"
                elif [[ "$line" == *'"phase":"ACKED"'* ]]; then
                    printf "  \033[32m%s\033[0m\n" "$line"
                elif [[ "$line" == *'"phase":"DISPATCHED"'* ]]; then
                    printf "  \033[36m%s\033[0m\n" "$line"
                else
                    echo "  $line"
                fi
            done
        else
            echo "  No log file found"
        fi
        echo ""
        echo "=============================================="
    }

    if [[ "$watch_mode" == true ]]; then
        echo "Press Ctrl+C to exit"
        echo ""
        while true; do
            _render_dashboard
            sleep "$refresh_interval"
            clear 2>/dev/null || printf "\033[H\033[J"
        done
    else
        _render_dashboard
    fi
}

usage() {
    cat << EOF
Usage: $(basename "$0") <command>

Claude Master Window Bridge - Monitor master window and dispatch tasks.

Commands:
  start           Start bridge process
  stop            Stop bridge process
  status          Check bridge running status
  bridge-status   Analyze bridge.log for dispatch lifecycle
  bridge-dashboard  Real-time monitoring dashboard

Observability Commands:
  bridge-status:
    --recent N    Show last N bridge events (default: 10)
    --failed      Show only FAILED/RETRY events
    --task ID     Show lifecycle of specific bridge_task_id
    --phase PHASE Filter by phase (CAPTURED|PARSED|DISPATCHED|ACKED|RETRY|FAILED)
    --json        Output as JSON for piping

  bridge-dashboard:
    --watch       Refresh every 30 seconds (default: single view)

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

  # Check recent bridge events
  ./scripts/swarm_bridge.sh bridge-status --recent 20

  # Monitor failures only
  ./scripts/swarm_bridge.sh bridge-status --failed

  # Track specific task lifecycle
  ./scripts/swarm_bridge.sh bridge-status --task br-123456

  # Filter by phase
  ./scripts/swarm_bridge.sh bridge-status --phase DISPATCHED

  # JSON output for automation
  ./scripts/swarm_bridge.sh bridge-status --json > /tmp/bridge_events.json

  # Real-time dashboard
  ./scripts/swarm_bridge.sh bridge-dashboard --watch

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
    local session="${AI_SWARM_BRIDGE_SESSION:-swarm-claude-default}"
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
    bridge-status)
        shift
        cmd_bridge_status "$@"
        ;;
    bridge-dashboard)
        shift
        cmd_bridge_dashboard "$@"
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
