#!/usr/bin/env bash
# =============================================================================
# AI Swarm v1.93 - Bridge Debug Evidence Gathering Script
# =============================================================================
# Purpose: Gather deterministic evidence of where the dispatch chain breaks
# Phase: v1.93 Phase 1 - Root Cause Debug (Evidence Gathering)
#
# This script:
# 1. Creates tmux session with V1.92 layout (2 windows)
# 2. Launches Bridge with verbose logging
# 3. Captures master and worker pane outputs
# 4. Tests send-keys reachability for each worker
# 5. Tests worker ACK response capability
# 6. Generates comprehensive evidence bundle
#
# Usage:
#   ./scripts/swarm_bridge_debug.sh                    # Run full debug suite
#   ./scripts/swarm_bridge_debug.sh --setup-only      # Setup tmux session only
#   ./scripts/swarm_bridge_debug.sh --send-keys-test  # Send-keys reachability only
#   ./scripts/swarm_bridge_debug.sh --ack-test        # ACK response test only
#   ./scripts/swarm_bridge_debug.sh --cleanup         # Cleanup and exit
#
# Output:
#   /tmp/ai_swarm_debug/evidence_bundle_*.tar.gz
#   /tmp/ai_swarm_debug/evidence/ (unpacked evidence)
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_SWARM_DIR="${AI_SWARM_DIR:-/tmp/ai_swarm}"
DEBUG_DIR="${AI_SWARM_DIR}/debug_$(date +%Y%m%d_%H%M%S)"
SESSION_NAME="swarm-debug-$(date +%s | cut -c8-)"  # Unique session per run
SESSION_PREFIX="swarm-debug"  # Prefix for finding/cleaning up

# Timing configuration
CAPTURE_DURATION=60           # seconds to capture after task injection
SEND_KEYS_TIMEOUT=5            # seconds to wait for send-keys verification
ACK_TEST_DURATION=30          # seconds to wait for ACK response
POLL_INTERVAL=0.5              # polling interval for captures

# Logging with millisecond precision
log_info() { echo "[$(date +%Y-%m-%dT%H:%M:%S.%3N)][INFO] $*"; }
log_error() { echo "[$(date +%Y-%m-%dT%H:%M:%S.%3N)][ERROR] $*" >&2; }
log_debug() { [[ "${DEBUG_MODE:-0}" == "1" ]] && echo "[$(date +%Y-%m-%dT%H:%M:%S.%3N)][DEBUG] $*" || true; }

# =============================================================================
# Cleanup Functions
# =============================================================================

cleanup_session() {
    local session="$1"
    log_info "Cleaning up session: $session"
    tmux kill-session -t "$session" 2>/dev/null || true
}

cleanup_all_debug_sessions() {
    log_info "Cleaning up all debug sessions with prefix: $SESSION_PREFIX"
    for session in $(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep "^${SESSION_PREFIX}" || true); do
        log_info "  Killing: $session"
        tmux kill-session -t "$session" 2>/dev/null || true
    done
}

# =============================================================================
# Setup Functions
# =============================================================================

show_help() {
    cat << EOF
AI Swarm v1.93 - Bridge Debug Evidence Gathering Script

Usage: $0 [OPTIONS]

Options:
  --help, -h              Show this help message
  --setup-only            Only setup tmux session, don't run diagnostics
  --send-keys-test        Only run send-keys reachability test
  --ack-test              Only run ACK response test
  --cleanup               Clean up all debug sessions and exit
  --no-cleanup            Don't clean up session after completion
  --debug                 Enable debug logging
  --session NAME          Use custom session name (default: auto-generated)

Environment:
  AI_SWARM_DIR            Swarm state directory (default: /tmp/ai_swarm)
  AI_SWARM_INTERACTIVE    Must be "1" for bridge

Output:
  Evidence bundle at: /tmp/ai_swarm_debug/evidence_*.tar.gz

Examples:
  # Run full debug suite
  $0

  # Setup and leave session running for manual inspection
  $0 --setup-only --no-cleanup

  # Quick send-keys test
  $0 --send-keys-test

  # Cleanup all debug sessions
  $0 --cleanup
EOF
}

# =============================================================================
# Tmux Layout Creation
# =============================================================================

create_tmux_session() {
    local session="$1"
    local workdir="${2:-$PWD}"

    log_info "Creating tmux session: $session"
    log_info "Working directory: $workdir"

    # Kill existing session with same name if exists
    if tmux has-session -t "$session" 2>/dev/null; then
        log_warn "Session $session exists, killing it"
        tmux kill-session -t "$session" 2>/dev/null || true
    fi

    # Create session with codex-master window
    local codex_pane
    codex_pane=$(tmux new-session -d -P -F '#{pane_id}' -s "$session" -n codex-master)
    log_info "Created codex-master window, pane: $codex_pane"

    # Set environment variables at session level
    tmux set-environment -t "$session" AI_SWARM_DIR "$AI_SWARM_DIR"
    tmux set-environment -t "$session" AI_SWARM_INTERACTIVE "1"

    # Split horizontally for master pane
    local master_pane
    master_pane=$(tmux split-window -h -P -F '#{pane_id}' -t "$codex_pane")
    log_info "Created master pane: $master_pane"

    # Send startup commands (using sleep as placeholder for actual Claude Code)
    # Note: In real scenario, these would be 'claude' commands
    tmux send-keys -t "$codex_pane" "cd \"$workdir\" && sleep 2 && echo 'Codex pane ready'" C-m
    tmux send-keys -t "$master_pane" "cd \"$workdir\" && sleep 2 && echo 'Master pane ready'" C-m

    # Create workers window with 3 panes
    local worker0_pane
    worker0_pane=$(tmux new-window -P -F '#{pane_id}' -t "$session" -n workers)
    log_info "Created workers window, pane: $worker0_pane"

    # Split for worker-1 and worker-2
    local worker1_pane worker2_pane
    worker1_pane=$(tmux split-window -h -P -F '#{pane_id}' -t "$worker0_pane")
    worker2_pane=$(tmux split-window -h -P -F '#{pane_id}' -t "$worker1_pane")

    # Apply even layout
    tmux select-layout -t "$session:workers" even-horizontal

    # Send startup commands to workers
    tmux send-keys -t "$worker0_pane" "cd \"$workdir\" && sleep 2 && echo 'Worker-0 ready'" C-m
    tmux send-keys -t "$worker1_pane" "cd \"$workdir\" && sleep 2 && echo 'Worker-1 ready'" C-m
    tmux send-keys -t "$worker2_pane" "cd \"$workdir\" && sleep 2 && echo 'Worker-2 ready'" C-m

    # Wait for panes to initialize
    sleep 3

    # Get pane IDs for workers
    local worker_panes
    worker_panes=$(tmux list-panes -t "$session:workers" -F '#{pane_id}')
    log_info "Worker panes:"
    echo "$worker_panes" | nl -v 0

    log_info "Session created successfully"
    echo "$master_pane" > "$DEBUG_DIR/master_pane_id.txt"
    echo "$worker_panes" > "$DEBUG_DIR/worker_panes.txt"

    # Output for user
    log_info ""
    log_info "=============================================="
    log_info "Session Configuration:"
    log_info "=============================================="
    log_info "Session: $session"
    log_info "Master Pane: $master_pane"
    log_info "Worker Panes:"
    echo "$worker_panes" | nl -v 0
    log_info "=============================================="
    log_info "To capture output:"
    log_info "  tmux capture-pane -t $session:codex-master -p"
    log_info "  tmux capture-pane -t $session:workers.0 -p"
    log_info "=============================================="
}

# =============================================================================
# Bridge Startup
# =============================================================================

start_bridge() {
    local master_pane="$1"
    local session="$2"

    log_info "Starting Bridge..."

    # Set environment
    export AI_SWARM_DIR="$AI_SWARM_DIR"
    export AI_SWARM_INTERACTIVE="1"
    export AI_SWARM_BRIDGE_PANE="$master_pane"
    export AI_SWARM_BRIDGE_SESSION="$session"
    export AI_SWARM_BRIDGE_LINES="200"
    export AI_SWARM_BRIDGE_POLL_INTERVAL="0.5"

    # Start bridge in background with logging
    python3 -m swarm.claude_bridge > "$DEBUG_DIR/bridge_stdout.log" 2>&1 &
    local bridge_pid=$!

    log_info "Bridge started (PID: $bridge_pid)"

    # Brief wait and verify
    sleep 1

    if kill -0 "$bridge_pid" 2>/dev/null; then
        echo "$bridge_pid" > "$DEBUG_DIR/bridge.pid"
        log_info "Bridge verified running"
        return 0
    else
        log_error "Bridge failed to start"
        cat "$DEBUG_DIR/bridge_stdout.log" >&2
        return 1
    fi
}

# =============================================================================
# Capture Functions
# =============================================================================

capture_pane_continuous() {
    local pane="$1"
    local label="$2"
    local duration="$3"
    local output_file="$DEBUG_DIR/${label}_capture.log"

    log_info "Capturing pane $pane for ${duration}s -> $output_file"

    local start_time=$(date +%s)
    local end_time=$((start_time + duration))

    > "$output_file"

    while [[ $(date +%s) -lt $end_time ]]; do
        local timestamp
        timestamp=$(date +%Y-%m-%dT%H:%M:%S.%3N)
        {
            echo "=== CAPTURE $timestamp ==="
            tmux capture-pane -t "$pane" -p -S -100 2>/dev/null || echo "Capture failed"
            echo "=== END CAPTURE ==="
        } >> "$output_file" 2>&1
        sleep "$POLL_INTERVAL"
    done

    log_info "Capture complete: $output_file ($(wc -l < "$output_file") lines)"
}

# =============================================================================
# Send-Keys Reachability Test (Task 1.2)
# =============================================================================

test_send_keys_reachability() {
    local worker_panes_file="$1"
    local session="$2"

    log_info ""
    log_info "=============================================="
    log_info "TEST: Send-Keys Reachability"
    log_info "=============================================="

    local results_file="$DEBUG_DIR/send_keys_reachability.log"
    > "$results_file"

    local unique_marker="DEBUG_REACH_$(date +%s)_TEST"

    # Get pane list
    local panes
    panes=$(cat "$worker_panes_file")

    local pane_index=0
    while IFS= read -r pane_id; do
        [[ -z "$pane_id" ]] && continue

        log_info "Testing worker-$pane_index: $pane_id"

        # Capture baseline
        local before_capture
        before_capture=$(tmux capture-pane -t "$pane_id" -p -S -5 2>/dev/null || echo "ERROR")

        # Send unique marker
        log_debug "Sending marker to $pane_id: $unique_marker"
        tmux send-keys -l -t "$pane_id" "$unique_marker" Enter 2>/dev/null

        # Wait for potential processing
        sleep "$SEND_KEYS_TIMEOUT"

        # Capture after
        local after_capture
        after_capture=$(tmux capture-pane -t "$pane_id" -p -S -50 2>/dev/null || echo "ERROR")

        # Check if marker appears in capture
        local found="NO"
        if echo "$after_capture" | grep -qF "$unique_marker"; then
            found="YES"
            log_info "  Result: FOUND in pane"
        else
            log_info "  Result: NOT FOUND in pane"
        fi

        # Record result
        {
            echo "=== Worker-$pane_index (Pane: $pane_id) ==="
            echo "Unique Marker: $unique_marker"
            echo "Found in Capture: $found"
            echo "Timestamp: $(date +%Y-%m-%dT%H:%M:%S.%3N)"
            echo ""
            echo "--- Capture After Injection ---"
            echo "$after_capture"
            echo ""
            echo "=========================================="
        } >> "$results_file"

        pane_index=$((pane_index + 1))
    done <<< "$panes"

    log_info ""
    log_info "Send-Keys Reachability Test Complete"
    log_info "Results: $results_file"

    # Summary
    log_info ""
    log_info "Summary:"
    grep -E "^(Worker-|Unique Marker|Found in)" "$results_file" | grep -v "^===$\|^---$\|^===\|^Timestamp" | head -20

    echo "$results_file"
}

# =============================================================================
# Worker ACK Response Test (Task 1.3)
# =============================================================================

test_worker_ack_response() {
    local worker_panes_file="$1"
    local session="$2"

    log_info ""
    log_info "=============================================="
    log_info "TEST: Worker ACK Response"
    log_info "=============================================="

    local results_file="$DEBUG_DIR/worker_ack_test.log"
    local start_time=$(date +%s)
    local unique_id="TESTACK$(date +%s | cut -c8-)"

    > "$results_file"

    # Task format that Bridge uses
    local test_task="TASK: ACK_TEST_PLEASE_REPLY [bridge-task-id:${unique_id}]"

    # Get pane list
    local panes
    panes=$(cat "$worker_panes_file")

    local pane_index=0
    while IFS= read -r pane_id; do
        [[ -z "$pane_id" ]] && continue

        log_info "Testing worker-$pane_index: $pane_id"

        local test_start=$(date +%s)
        local output_file="$DEBUG_DIR/worker_${pane_index}_ack_capture.log"

        # Capture baseline
        tmux capture-pane -t "$pane_id" -p > "$DEBUG_DIR/worker_${pane_index}_ack_baseline.log" 2>/dev/null || true

        # Send TASK format
        log_debug "Sending: $test_task"
        tmux send-keys -l -t "$pane_id" "$test_task" Enter 2>/dev/null

        # Capture for ACK_TEST_DURATION
        log_info "  Capturing response for ${ACK_TEST_DURATION}s..."
        capture_pane_single "$pane_id" "$output_file" "$ACK_TEST_DURATION"

        # Analyze capture for response
        local response_found="NO"
        local response_content=""
        if [[ -f "$output_file" ]]; then
            # Check for any response containing the unique ID
            if grep -q "$unique_id" "$output_file"; then
                response_found="YES"
                response_content=$(grep -A2 -B2 "$unique_id" "$output_file" | head -20 || echo "Content extraction failed")
                log_info "  Response: FOUND (contains $unique_id)"
            else
                # Check for any TASK: echo
                if grep -q "TASK:" "$output_file"; then
                    response_found="ECHO_ONLY"
                    log_info "  Response: TASK: echo detected (no reply)"
                else
                    log_info "  Response: NO response"
                fi
            fi
        fi

        local test_duration=$(($(date +%s) - test_start))

        # Record result
        {
            echo "=== Worker-$pane_index (Pane: $pane_id) ==="
            echo "Test Task: $test_task"
            echo "Unique ID: $unique_id"
            echo "Response Found: $response_found"
            echo "Test Duration: ${test_duration}s"
            echo "Timestamp: $(date +%Y-%m-%dT%H:%M:%S.%3N)"
            echo ""
            echo "--- Relevant Capture Lines ---"
            if [[ -f "$output_file" ]]; then
                grep -E "$unique_id|TASK:|ACK|Response" "$output_file" 2>/dev/null || echo "(No matching lines)"
            else
                echo "(Output file not found)"
            fi
            echo ""
            echo "=========================================="
        } >> "$results_file"

        pane_index=$((pane_index + 1))
    done <<< "$panes"

    log_info ""
    log_info "Worker ACK Test Complete"
    log_info "Results: $results_file"

    # Summary
    log_info ""
    log_info "Summary:"
    grep -E "^(Worker-|Test Task|Unique ID|Response Found|Test Duration)" "$results_file" | grep -v "^===$\|^---$\|^===\|^Timestamp" | head -30

    echo "$results_file"
}

capture_pane_single() {
    local pane="$1"
    local output_file="$2"
    local duration="$3"

    local start_time=$(date +%s)
    local end_time=$((start_time + duration))

    > "$output_file"

    while [[ $(date +%s) -lt $end_time ]]; do
        {
            echo "=== CAPTURE $(date +%Y-%m-%dT%H:%M:%S.%3N) ==="
            tmux capture-pane -t "$pane" -p -S -20 2>/dev/null || echo "Capture error"
            echo "=== END ==="
        } >> "$output_file" 2>&1
        sleep 0.5
    done
}

# =============================================================================
# Full Dispatch Test
# =============================================================================

test_full_dispatch() {
    local master_pane="$1"
    local worker_panes_file="$2"
    local session="$3"

    log_info ""
    log_info "=============================================="
    log_info "TEST: Full Dispatch Chain"
    log_info "=============================================="

    local results_file="$DEBUG_DIR/full_dispatch_test.log"
    local task_id="DISPATCH$(date +%s | cut -c8-)"
    local test_task="TASK: Full dispatch test task [id:$task_id]"

    > "$results_file"

    # Get worker panes
    local panes
    panes=$(cat "$worker_panes_file")

    # Prepare worker capture
    local pane_index=0
    while IFS= read -r pane_id; do
        [[ -z "$pane_id" ]] && continue
        tmux capture-pane -t "$pane_id" -p > "$DEBUG_DIR/worker_${pane_index}_dispatch_baseline.log" 2>/dev/null || true
        pane_index=$((pane_index + 1))
    done <<< "$panes"

    # Capture master baseline
    tmux capture-pane -t "$master_pane" -p > "$DEBUG_DIR/master_dispatch_baseline.log" 2>/dev/null || true

    # Inject task into master pane (simulating user input)
    log_info "Injecting task: $test_task"
    tmux send-keys -l -t "$master_pane" "$test_task" Enter

    # Capture for CAPTURE_DURATION
    log_info "Capturing for ${CAPTURE_DURATION}s..."

    # Start continuous capture for master
    capture_pane_continuous "$master_pane" "master_dispatch" "$CAPTURE_DURATION" &
    local master_capture_pid=$!

    # Capture each worker
    pane_index=0
    while IFS= read -r pane_id; do
        [[ -z "$pane_id" ]] && continue
        capture_pane_continuous "$pane_id" "worker_${pane_index}_dispatch" "$CAPTURE_DURATION" &
        pane_index=$((pane_index + 1))
    done <<< "$panes"

    # Wait for captures
    wait $master_capture_pid 2>/dev/null || true

    # Analyze results
    {
        echo "=== Full Dispatch Analysis ==="
        echo "Task: $test_task"
        echo "Task ID: $task_id"
        echo "Timestamp: $(date +%Y-%m-%dT%H:%M:%S.%3N)"
        echo ""
    } >> "$results_file"

    # Check if task was captured by bridge
    local bridge_log="$AI_SWARM_DIR/bridge.log"
    if [[ -f "$bridge_log" ]]; then
        if grep -q "$task_id" "$bridge_log" 2>/dev/null; then
            log_info "Task FOUND in bridge.log"
            {
                echo "Bridge Log Entry:"
                grep "$task_id" "$bridge_log" | tail -5
            } >> "$results_file"
        else
            log_warn "Task NOT FOUND in bridge.log"
            {
                echo "Bridge Log (last 10 lines):"
                tail -10 "$bridge_log" 2>/dev/null || echo "(empty)"
            } >> "$results_file"
        fi
    else
        log_warn "bridge.log not found: $bridge_log"
        echo "bridge.log not found at $bridge_log" >> "$results_file"
    fi

    # Check if dispatched to worker
    local dispatched="NO"
    for pane_idx in 0 1 2; do
        local capture_file="$DEBUG_DIR/worker_${pane_idx}_dispatch_capture.log"
        if [[ -f "$capture_file" ]] && grep -q "TASK:.*$task_id" "$capture_file" 2>/dev/null; then
            dispatched="YES"
            log_info "Task FOUND in worker-$pane_idx capture"
            {
                echo "Worker-$pane_idx received task:"
                grep "TASK:.*$task_id" "$capture_file" | head -5
            } >> "$results_file"
            break
        fi
    done

    if [[ "$dispatched" == "NO" ]]; then
        log_warn "Task NOT FOUND in any worker capture"
    fi

    echo "" >> "$results_file"
    echo "Dispatch Status: $dispatched" >> "$results_file"

    log_info ""
    log_info "Full Dispatch Test Complete"
    log_info "Results: $results_file"

    echo "$results_file"
}

# =============================================================================
# Evidence Bundle Creation
# =============================================================================

create_evidence_bundle() {
    local bundle_dir="$1"

    log_info ""
    log_info "=============================================="
    log_info "Creating Evidence Bundle"
    log_info "=============================================="

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local bundle_file="/tmp/ai_swarm_debug/evidence_bundle_${timestamp}.tar.gz"

    mkdir -p /tmp/ai_swarm_debug

    # Create tar.gz
    tar -czf "$bundle_file" -C "$(dirname "$bundle_dir")" "$(basename "$bundle_dir")" 2>/dev/null

    log_info "Evidence bundle created: $bundle_file"
    log_info "Bundle size: $(du -h "$bundle_file" | cut -f1)"

    echo "$bundle_file"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    local do_setup=false
    local do_send_keys_test=false
    local do_ack_test=false
    local do_cleanup=true
    local custom_session=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                show_help
                exit 0
                ;;
            --setup-only)
                do_setup=true
                shift
                ;;
            --send-keys-test)
                do_send_keys_test=true
                shift
                ;;
            --ack-test)
                do_ack_test=true
                shift
                ;;
            --cleanup)
                cleanup_all_debug_sessions
                exit 0
                ;;
            --no-cleanup)
                do_cleanup=false
                shift
                ;;
            --debug)
                DEBUG_MODE=1
                shift
                ;;
            --session)
                custom_session="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Determine mode
    local run_full=true
    if [[ "$do_setup" == true ]] || [[ "$do_send_keys_test" == true ]] || [[ "$do_ack_test" == true ]]; then
        run_full=false
    fi

    # Setup debug directory
    mkdir -p "$DEBUG_DIR"
    log_info "Debug directory: $DEBUG_DIR"
    log_info "Log prefix: $(date +%Y-%m-%dT%H:%M:%S.%3N)"

    # Use custom session or generate unique one
    if [[ -n "$custom_session" ]]; then
        SESSION_NAME="$custom_session"
    fi

    local master_pane=""
    local worker_panes_file="$DEBUG_DIR/worker_panes.txt"

    # Trap for cleanup
    trap 'log_info "Interrupted, cleaning up..."; [[ "$do_cleanup" == true ]] && cleanup_session "$SESSION_NAME"' INT TERM

    # Check tmux availability
    if ! command -v tmux >/dev/null 2>&1; then
        log_error "tmux not found. Please install tmux."
        exit 1
    fi

    # Run requested tests
    if [[ "$do_setup" == true ]]; then
        create_tmux_session "$SESSION_NAME" "$PWD"
        master_pane=$(cat "$DEBUG_DIR/master_pane_id.txt")
        log_info "Session ready. Attach with: tmux attach -t $SESSION_NAME"
        log_info "To cleanup later: $0 --cleanup"
        exit 0
    fi

    if [[ "$do_send_keys_test" == true ]]; then
        create_tmux_session "$SESSION_NAME" "$PWD"
        master_pane=$(cat "$DEBUG_DIR/master_pane_id.txt")
        test_send_keys_reachability "$worker_panes_file" "$SESSION_NAME"
        [[ "$do_cleanup" == true ]] && cleanup_session "$SESSION_NAME"
        exit 0
    fi

    if [[ "$do_ack_test" == true ]]; then
        create_tmux_session "$SESSION_NAME" "$PWD"
        master_pane=$(cat "$DEBUG_DIR/master_pane_id.txt")
        test_worker_ack_response "$worker_panes_file" "$SESSION_NAME"
        [[ "$do_cleanup" == true ]] && cleanup_session "$SESSION_NAME"
        exit 0
    fi

    # Full debug suite
    log_info ""
    log_info "=============================================="
    log_info "AI Swarm v1.93 - Bridge Debug Suite"
    log_info "=============================================="
    log_info "Session: $SESSION_NAME"
    log_info "Debug Dir: $DEBUG_DIR"
    log_info "=============================================="

    # Step 1: Create tmux session
    log_info ""
    log_info "STEP 1: Creating tmux session..."
    create_tmux_session "$SESSION_NAME" "$PWD"
    master_pane=$(cat "$DEBUG_DIR/master_pane_id.txt")

    # Step 2: Start bridge
    log_info ""
    log_info "STEP 2: Starting Bridge..."
    start_bridge "$master_pane" "$SESSION_NAME"

    # Brief stabilization
    sleep 2

    # Step 3: Run send-keys reachability test
    log_info ""
    log_info "STEP 3: Testing send-keys reachability..."
    test_send_keys_reachability "$worker_panes_file" "$SESSION_NAME"

    # Step 4: Run worker ACK test
    log_info ""
    log_info "STEP 4: Testing worker ACK response..."
    test_worker_ack_response "$worker_panes_file" "$SESSION_NAME"

    # Step 5: Run full dispatch test
    log_info ""
    log_info "STEP 5: Running full dispatch test..."
    test_full_dispatch "$master_pane" "$worker_panes_file" "$SESSION_NAME"

    # Step 6: Create evidence bundle
    log_info ""
    log_info "STEP 6: Creating evidence bundle..."
    local bundle_file
    bundle_file=$(create_evidence_bundle "$DEBUG_DIR")

    # Cleanup if requested
    if [[ "$do_cleanup" == true ]]; then
        log_info ""
        log_info "Cleaning up session..."
        cleanup_session "$SESSION_NAME"

        # Also cleanup any orphaned debug sessions
        cleanup_all_debug_sessions
    fi

    # Final summary
    log_info ""
    log_info "=============================================="
    log_info "DEBUG SUITE COMPLETE"
    log_info "=============================================="
    log_info "Evidence Bundle: $bundle_file"
    log_info ""
    log_info "Files captured:"
    ls -la "$DEBUG_DIR/" | grep -v "^d" | awk '{print "  " $9 " (" $5 " bytes)"}'
    log_info ""
    log_info "Next steps:"
    log_info "  1. Review send-keys reachability results"
    log_info "  2. Review worker ACK test results"
    log_info "  3. Analyze full dispatch test"
    log_info "  4. Document findings in ROOT_CAUSE_REPORT.md"
    log_info "=============================================="
}

# Run main
main "$@"
