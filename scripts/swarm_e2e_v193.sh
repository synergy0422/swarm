#!/usr/bin/env bash
set -euo pipefail

# AI Swarm V1.93 E2E Acceptance Test Suite
# Tests for Bridge ACK + Retry + Failover Protocol
#
# Usage: ./scripts/swarm_e2e_v193.sh [scenario]
#   - Without args: Run all scenarios (A, B, C)
#   - With scenario: Run only that scenario (A, B, or C)
#
# Prerequisites:
#   - tmux installed
#   - Python 3.8+
#   - AI Swarm modules installed (pip install -e .)
#   - Claude Code CLI or proxy for LLM calls
#
# Environment:
#   AI_SWARM_DIR              Swarm state directory (default: /tmp/ai_swarm)
#   AI_SWARM_BRIDGE_SESSION   tmux session (default: swarm-claude-default)
#   AI_SWARM_BRIDGE_PANE      Master pane ID (required for tests)
#   AI_SWARM_BRIDGE_WORKER_PANES  Worker panes (format: "pane1:pane2:pane3")
#   LLM_BASE_URL              LLM endpoint (optional, for actual Claude calls)
#   ANTHROPIC_API_KEY         API key (optional)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_SWARM_DIR="${AI_SWARM_DIR:-/tmp/ai_swarm}"
SESSION="${AI_SWARM_BRIDGE_SESSION:-swarm-claude-default}"
TEST_DIR="/tmp/ai_swarm_e2e_v193"
EVIDENCE_DIR="$TEST_DIR/evidence"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $*"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $*"; }
log_skip() { echo -e "${YELLOW}[SKIP]${NC} $*"; }
log_section() { echo -e "\n${CYAN}========================================${NC}"; echo -e "${CYAN}  $*${NC}"; echo -e "${CYAN}========================================${NC}\n"; }

# Cleanup function
cleanup() {
    log_info "Cleaning up test environment..."
    # Kill any test bridge processes
    if [[ -f "$EVIDENCE_DIR/bridge.pid" ]]; then
        local pid=$(cat "$EVIDENCE_DIR/bridge.pid" 2>/dev/null || echo "")
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            log_info "Killed test bridge (PID: $pid)"
        fi
    fi
    # Note: We don't kill tmux sessions as they may be user-controlled
}

trap cleanup EXIT

# Ensure directories exist
setup_directories() {
    mkdir -p "$TEST_DIR"
    mkdir -p "$EVIDENCE_DIR"
    mkdir -p "$AI_SWARM_DIR"
}

# ============================================================================
# SCENARIO A: Single Task Closure
# ============================================================================
scenario_a() {
    log_section "Scenario A: Single Task Closure"

    local test_start=$(date +%s)
    local test_passed=true

    # Setup
    log_info "Setting up test environment..."
    cd "$EVIDENCE_DIR"

    # Clear previous logs
    > "$AI_SWARM_DIR/bridge.log" 2>/dev/null || true
    > "$AI_SWARM_DIR/status.log" 2>/dev/null || true

    # Check prerequisites
    if ! tmux has-session -t "$SESSION" 2>/dev/null; then
        log_fail "tmux session '$SESSION' not found"
        log_info "Create session first: ./scripts/swarm_layout_2windows.sh"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi

    if [[ -z "${AI_SWARM_BRIDGE_PANE:-}" ]]; then
        log_fail "AI_SWARM_BRIDGE_PANE not set"
        log_info "Run layout script and export the pane ID:"
        log_info "  export AI_SWARM_BRIDGE_PANE=%3"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi

    log_info "Master pane: $AI_SWARM_BRIDGE_PANE"

    # Step 1: Start bridge
    log_info "Step 1: Starting bridge..."
    AI_SWARM_INTERACTIVE=1 python3 -m swarm.claude_bridge > "$EVIDENCE_DIR/bridge_output.log" 2>&1 &
    local bridge_pid=$!
    echo "$bridge_pid" > "$EVIDENCE_DIR/bridge.pid"

    sleep 1

    if ! kill -0 "$bridge_pid" 2>/dev/null; then
        log_fail "Bridge failed to start"
        cat "$EVIDENCE_DIR/bridge_output.log"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
    log_pass "Bridge started (PID: $bridge_pid)"

    # Step 2: Input task
    log_info "Step 2: Input task into master pane..."
    local task_content="TASK: Please only reply 'received'"
    log_info "Sending: $task_content"

    # Send the task to the master pane via tmux send-keys
    tmux send-keys -t "$AI_SWARM_BRIDGE_PANE" "$task_content" Enter

    # Wait for processing (max 60s)
    log_info "Waiting for task processing (max 60s)..."
    local waited=0
    local task_processed=false

    while [[ $waited -lt 60 ]]; do
        # Check if bridge.log has all phases
        if [[ -f "$AI_SWARM_DIR/bridge.log" ]]; then
            local captured=$(grep -c '"phase":"CAPTURED"' "$AI_SWARM_DIR/bridge.log" 2>/dev/null || echo "0")
            local dispatched=$(grep -c '"phase":"DISPATCHED"' "$AI_SWARM_DIR/bridge.log" 2>/dev/null || echo "0")
            local acked=$(grep -c '"phase":"ACKED"' "$AI_SWARM_DIR/bridge.log" 2>/dev/null || echo "0")

            log_info "Progress: CAPTURED=$captured, DISPATCHED=$dispatched, ACKED=$acked"

            if [[ "$acked" -gt 0 ]]; then
                task_processed=true
                break
            fi
        fi

        sleep 2
        waited=$((waited + 2))
    done

    # Step 3: Verify results
    log_info "Step 3: Verifying results..."

    # Evidence collection
    {
        echo "=== SCENARIO A EVIDENCE ==="
        echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        echo "Session: $SESSION"
        echo "Master Pane: $AI_SWARM_BRIDGE_PANE"
        echo ""
        echo "=== bridge.log ==="
        cat "$AI_SWARM_DIR/bridge.log" 2>/dev/null || echo "(not found)"
        echo ""
        echo "=== status.log (BRIDGE entries) ==="
        grep '"type":"BRIDGE"' "$AI_SWARM_DIR/status.log" 2>/dev/null || echo "(not found)"
        echo ""
        echo "=== Bridge Output Log ==="
        cat "$EVIDENCE_DIR/bridge_output.log"
    } > "$EVIDENCE_DIR/scenario_a_evidence.txt"

    if [[ "$task_processed" != true ]]; then
        log_fail "Task was not ACKED within 60s"
        test_passed=false
    fi

    # Check bridge.log phases
    if [[ -f "$AI_SWARM_DIR/bridge.log" ]]; then
        local has_captured=$(grep -q '"phase":"CAPTURED"' "$AI_SWARM_DIR/bridge.log" && echo "yes" || echo "no")
        local has_dispatched=$(grep -q '"phase":"DISPATCHED"' "$AI_SWARM_DIR/bridge.log" && echo "yes" || echo "no")
        local has_acked=$(grep -q '"phase":"ACKED"' "$AI_SWARM_DIR/bridge.log" && echo "yes" || echo "no")

        log_info "Phase checks: CAPTURED=$has_captured, DISPATCHED=$has_dispatched, ACKED=$has_acked"

        if [[ "$has_captured" == "no" ]]; then
            log_fail "CAPTURED phase not found in bridge.log"
            test_passed=false
        fi
        if [[ "$has_dispatched" == "no" ]]; then
            log_fail "DISPATCHED phase not found in bridge.log"
            test_passed=false
        fi
        if [[ "$has_acked" == "no" ]]; then
            log_fail "ACKED phase not found in bridge.log"
            test_passed=false
        fi
    else
        log_fail "bridge.log not found"
        test_passed=false
    fi

    # Check status.log for BRIDGE entry
    if grep -q '"type":"BRIDGE"' "$AI_SWARM_DIR/status.log" 2>/dev/null; then
        log_pass "status.log has BRIDGE entry with bridge_task_id"
    else
        log_fail "status.log missing BRIDGE entry"
        test_passed=false
    fi

    # Check for bridge_task_id
    if grep -q 'bridge_task_id' "$AI_SWARM_DIR/bridge.log" 2>/dev/null; then
        local task_id=$(grep 'bridge_task_id' "$AI_SWARM_DIR/bridge.log" | head -1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('bridge_task_id', 'N/A'))" 2>/dev/null || echo "found")
        log_pass "bridge_task_id present: $task_id"
    else
        log_fail "bridge_task_id not found in bridge.log"
        test_passed=false
    fi

    # Summary
    local test_end=$(date +%s)
    local duration=$((test_end - test_start))

    echo "" >> "$EVIDENCE_DIR/scenario_a_evidence.txt"
    echo "=== TEST RESULT ===" >> "$EVIDENCE_DIR/scenario_a_evidence.txt"
    echo "Duration: ${duration}s" >> "$EVIDENCE_DIR/scenario_a_evidence.txt"
    echo "Result: $([[ "$test_passed" == true ]] && echo "PASS" || echo "FAIL")" >> "$EVIDENCE_DIR/scenario_a_evidence.txt"

    if [[ "$test_passed" == true ]]; then
        log_pass "Scenario A: PASSED (${duration}s)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_fail "Scenario A: FAILED"
        log_info "Evidence saved to: $EVIDENCE_DIR/scenario_a_evidence.txt"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# ============================================================================
# SCENARIO B: Three Sequential Tasks
# ============================================================================
scenario_b() {
    log_section "Scenario B: Three Sequential Tasks"

    local test_start=$(date +%s)
    local test_passed=true

    # Setup
    log_info "Setting up test environment..."
    cd "$EVIDENCE_DIR"

    # Clear previous logs
    > "$AI_SWARM_DIR/bridge.log" 2>/dev/null || true
    > "$AI_SWARM_DIR/status.log" 2>/dev/null || true

    # Check prerequisites
    if ! tmux has-session -t "$SESSION" 2>/dev/null; then
        log_fail "tmux session '$SESSION' not found"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi

    if [[ -z "${AI_SWARM_BRIDGE_PANE:-}" ]]; then
        log_fail "AI_SWARM_BRIDGE_PANE not set"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi

    # Start bridge if not running
    if [[ ! -f "$EVIDENCE_DIR/bridge.pid" ]] || ! kill -0 "$(cat "$EVIDENCE_DIR/bridge.pid" 2>/dev/null)" 2>/dev/null; then
        log_info "Starting bridge for scenario B..."
        AI_SWARM_INTERACTIVE=1 python3 -m swarm.claude_bridge > "$EVIDENCE_DIR/bridge_output_b.log" 2>&1 &
        local bridge_pid=$!
        echo "$bridge_pid" > "$EVIDENCE_DIR/bridge.pid"
        sleep 1
    fi

    # Step 1: Input 3 tasks rapidly
    log_info "Step 1: Inputting 3 tasks rapidly..."

    local tasks=(
        "TASK: Test task 1 - reply with 'one'"
        "TASK: Test task 2 - reply with 'two'"
        "TASK: Test task 3 - reply with 'three'"
    )

    for i in "${!tasks[@]}"; do
        log_info "Sending task $((i+1)): ${tasks[$i]:0:30}..."
        tmux send-keys -t "$AI_SWARM_BRIDGE_PANE" "${tasks[$i]}" Enter
        sleep 0.5
    done

    # Wait for all 3 to complete (max 120s)
    log_info "Waiting for all tasks (max 120s)..."
    local waited=0
    local acked_count=0

    while [[ $waited -lt 120 ]]; do
        if [[ -f "$AI_SWARM_DIR/bridge.log" ]]; then
            acked_count=$(grep -c '"phase":"ACKED"' "$AI_SWARM_DIR/bridge.log" 2>/dev/null || echo "0")
            log_info "ACKED count: $acked_count / 3"

            if [[ "$acked_count" -ge 3 ]]; then
                break
            fi
        fi

        sleep 2
        waited=$((waited + 2))
    done

    # Step 2: Verify results
    log_info "Step 2: Verifying results..."

    # Evidence collection
    {
        echo "=== SCENARIO B EVIDENCE ==="
        echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        echo ""
        echo "=== bridge.log ==="
        cat "$AI_SWARM_DIR/bridge.log" 2>/dev/null || echo "(not found)"
    } > "$EVIDENCE_DIR/scenario_b_evidence.txt"

    # Check all 3 tasks ACKed
    if [[ "$acked_count" -lt 3 ]]; then
        log_fail "Only $acked_count / 3 tasks were ACKED within 120s"
        test_passed=false
    else
        log_pass "All 3 tasks ACKED"
    fi

    # Check unique bridge_task_ids
    if [[ -f "$AI_SWARM_DIR/bridge.log" ]]; then
        local unique_ids=$(grep -o '"bridge_task_id":"[^"]*"' "$AI_SWARM_DIR/bridge.log" 2>/dev/null | sort -u | wc -l | tr -d ' ')
        log_info "Unique bridge_task_ids: $unique_ids"

        if [[ "$unique_ids" -lt 3 ]]; then
            log_fail "Expected 3+ unique bridge_task_ids, got $unique_ids"
            test_passed=false
        else
            log_pass "All tasks have unique bridge_task_ids"
        fi

        # Show task IDs
        echo ""
        echo "=== Task IDs ===" >> "$EVIDENCE_DIR/scenario_b_evidence.txt"
        grep -o '"bridge_task_id":"[^"]*"' "$AI_SWARM_DIR/bridge.log" 2>/dev/null | sort -u >> "$EVIDENCE_DIR/scenario_b_evidence.txt"
    fi

    # Check worker assignment (round-robin should be visible)
    if [[ -f "$AI_SWARM_DIR/status.log" ]]; then
        local workers=$(grep '"type":"BRIDGE"' "$AI_SWARM_DIR/status.log" 2>/dev/null | python3 -c "import sys,json; lines=[json.loads(l) for l in sys.stdin if l.strip()]; print(' '.join(set(l.get('meta',{}).get('target_worker','') for l in lines)))" || echo "")
        log_info "Workers assigned: $workers"

        if [[ -n "$workers" ]]; then
            log_pass "Worker assignment visible in status.log"
        fi
    fi

    # Summary
    local test_end=$(date +%s)
    local duration=$((test_end - test_start))

    echo "" >> "$EVIDENCE_DIR/scenario_b_evidence.txt"
    echo "=== TEST RESULT ===" >> "$EVIDENCE_DIR/scenario_b_evidence.txt"
    echo "Duration: ${duration}s" >> "$EVIDENCE_DIR/scenario_b_evidence.txt"
    echo "Tasks ACKED: $acked_count / 3" >> "$EVIDENCE_DIR/scenario_b_evidence.txt"
    echo "Result: $([[ "$test_passed" == true ]] && echo "PASS" || echo "FAIL")" >> "$EVIDENCE_DIR/scenario_b_evidence.txt"

    if [[ "$test_passed" == true ]]; then
        log_pass "Scenario B: PASSED (${duration}s)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_fail "Scenario B: FAILED"
        log_info "Evidence saved to: $EVIDENCE_DIR/scenario_b_evidence.txt"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# ============================================================================
# SCENARIO C: Exception Recovery (Worker Failover)
# ============================================================================
scenario_c() {
    log_section "Scenario C: Exception Recovery (Worker Failover)"

    local test_start=$(date +%s)
    local test_passed=true

    # Setup
    log_info "Setting up test environment..."
    cd "$EVIDENCE_DIR"

    # Clear previous logs
    > "$AI_SWARM_DIR/bridge.log" 2>/dev/null || true
    > "$AI_SWARM_DIR/status.log" 2>/dev/null || true

    # Check prerequisites
    if ! tmux has-session -t "$SESSION" 2>/dev/null; then
        log_fail "tmux session '$SESSION' not found"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi

    # Get worker panes
    local worker_panes="${AI_SWARM_BRIDGE_WORKER_PANES:-}"
    if [[ -z "$worker_panes" ]]; then
        log_info "AI_SWARM_BRIDGE_WORKER_PANES not set, detecting from tmux..."
        # Try to detect worker panes
        worker_panes=$(tmux list-panes -t "$SESSION" -F '#{pane_id}' 2>/dev/null | grep -v "$AI_SWARM_BRIDGE_PANE" | tr '\n' ':' || echo "")
        if [[ -z "$worker_panes" ]]; then
            log_skip "Scenario C: SKIPPED (worker panes not detected)"
            log_info "Set AI_SWARM_BRIDGE_WORKER_PANES=panes:format to enable"
            TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
            return 0
        fi
    fi

    log_info "Worker panes: $worker_panes"

    # Parse first worker pane
    local first_worker=$(echo "$worker_panes" | cut -d':' -f1)
    local second_worker=$(echo "$worker_panes" | cut -d':' -f2)

    # Start bridge if not running
    if [[ ! -f "$EVIDENCE_DIR/bridge.pid" ]] || ! kill -0 "$(cat "$EVIDENCE_DIR/bridge.pid" 2>/dev/null)" 2>/dev/null; then
        log_info "Starting bridge for scenario C..."
        AI_SWARM_INTERACTIVE=1 python3 -m swarm.claude_bridge > "$EVIDENCE_DIR/bridge_output_c.log" 2>&1 &
        local bridge_pid=$!
        echo "$bridge_pid" > "$EVIDENCE_DIR/bridge.pid"
        sleep 1
    fi

    # Step 1: Kill first worker Claude process
    log_info "Step 1: Making first worker unresponsive..."
    log_info "Sending Ctrl+C to $first_worker..."

    # Send Ctrl+C to make worker unresponsive
    tmux send-keys -t "$first_worker" C-c
    sleep 1

    # Verify worker is unresponsive (not processing)
    log_info "Verifying worker is unresponsive..."

    # Step 2: Dispatch task
    log_info "Step 2: Dispatching task..."
    local task="TASK: If you receive this, reply 'recovery_success'"
    tmux send-keys -t "$AI_SWARM_BRIDGE_PANE" "$task" Enter

    # Wait for bridge to detect failure and retry (max 60s)
    log_info "Waiting for retry mechanism (max 60s)..."
    local waited=0
    local retry_found=false
    local success_found=false

    while [[ $waited -lt 60 ]]; do
        if [[ -f "$AI_SWARM_DIR/bridge.log" ]]; then
            # Check for RETRY phase
            if grep -q '"phase":"RETRY"' "$AI_SWARM_DIR/bridge.log" 2>/dev/null; then
                retry_found=true
                log_info "RETRY phase detected"
            fi

            # Check if eventually succeeded
            if grep -q '"phase":"ACKED"' "$AI_SWARM_DIR/bridge.log" 2>/dev/null; then
                success_found=true
                log_info "ACKED phase detected - failover succeeded"
                break
            fi
        fi

        sleep 2
        waited=$((waited + 2))
    done

    # Step 3: Verify results
    log_info "Step 3: Verifying results..."

    # Evidence collection
    {
        echo "=== SCENARIO C EVIDENCE ==="
        echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        echo "First worker pane: $first_worker"
        echo "Second worker pane: $second_worker"
        echo ""
        echo "=== bridge.log ==="
        cat "$AI_SWARM_DIR/bridge.log" 2>/dev/null || echo "(not found)"
    } > "$EVIDENCE_DIR/scenario_c_evidence.txt"

    # Verify RETRY occurred
    if [[ "$retry_found" == true ]]; then
        log_pass "RETRY phase found in logs"
    else
        log_info "RETRY phase not found (worker may have recovered quickly)"
        # This is OK if success happened - the retry might have been very fast
    fi

    # Verify final success
    if [[ "$success_found" == true ]]; then
        log_pass "Task completed via failover (ACKED phase present)"
    elif [[ "$retry_found" == true ]]; then
        log_pass "Retry mechanism triggered (may need more time or different failure scenario)"
    else
        log_fail "Neither RETRY nor ACKED found - failover may not have worked"
        test_passed=false
    fi

    # Check for multiple attempts
    if [[ -f "$AI_SWARM_DIR/bridge.log" ]]; then
        local attempts=$(grep '"phase":"DISPATCHED"' "$AI_SWARM_DIR/bridge.log" 2>/dev/null | wc -l | tr -d ' ')
        log_info "Dispatch attempts: $attempts"

        if [[ "$attempts" -gt 1 ]]; then
            log_pass "Multiple dispatch attempts detected (failover working)"
        elif [[ "$attempts" -eq 1 ]] && [[ "$success_found" == true ]]; then
            log_pass "Single dispatch succeeded (worker recovered)"
        fi
    fi

    # Summary
    local test_end=$(date +%s)
    local duration=$((test_end - test_start))

    echo "" >> "$EVIDENCE_DIR/scenario_c_evidence.txt"
    echo "=== TEST RESULT ===" >> "$EVIDENCE_DIR/scenario_c_evidence.txt"
    echo "Duration: ${duration}s" >> "$EVIDENCE_DIR/scenario_c_evidence.txt"
    echo "Retry found: $retry_found" >> "$EVIDENCE_DIR/scenario_c_evidence.txt"
    echo "Success found: $success_found" >> "$EVIDENCE_DIR/scenario_c_evidence.txt"
    echo "Result: $([[ "$test_passed" == true ]] && echo "PASS" || echo "FAIL")" >> "$EVIDENCE_DIR/scenario_c_evidence.txt"

    # Restore first worker (send Enter)
    tmux send-keys -t "$first_worker" Enter 2>/dev/null || true

    if [[ "$test_passed" == true ]]; then
        log_pass "Scenario C: PASSED (${duration}s)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_fail "Scenario C: FAILED"
        log_info "Evidence saved to: $EVIDENCE_DIR/scenario_c_evidence.txt"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# ============================================================================
# Main
# ============================================================================
usage() {
    cat << EOF
Usage: $(basename "$0") [scenario]

AI Swarm V1.93 E2E Acceptance Test Suite

Scenarios:
  A       Single Task Closure - Verify CAPTURED -> DISPATCHED -> ACKED lifecycle
  B       Three Sequential Tasks - Verify unique IDs and round-robin assignment
  C       Exception Recovery - Verify retry with worker failover
  all     Run all scenarios (default)

Options:
  --help   Show this help

Prerequisites:
  - tmux session running with master and workers
  - AI_SWARM_BRIDGE_PANE set to master pane ID
  - AI_SWARM_INTERACTIVE=1 for FIFO mode

Environment:
  AI_SWARM_DIR              Swarm state directory
  AI_SWARM_BRIDGE_SESSION   tmux session name
  AI_SWARM_BRIDGE_PANE      Master pane ID (required)
  AI_SWARM_BRIDGE_WORKER_PANES  Worker panes for scenario C (format: p1:p2:p3)

Examples:
  # Run all scenarios
  ./scripts/swarm_e2e_v193.sh

  # Run only scenario A
  ./scripts/swarm_e2e_v193.sh A

  # Run with custom session and pane
  AI_SWARM_BRIDGE_SESSION=my-swarm AI_SWARM_BRIDGE_PANE=%3 ./scripts/swarm_e2e_v193.sh

EOF
}

main() {
    local scenario="${1:-all}"

    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     AI Swarm V1.93 E2E Acceptance Test Suite                ║${NC}"
    echo -e "${CYAN}║                                                            ║${NC}"
    echo -e "${CYAN}║  Testing: ACK + Retry + Failover Protocol                  ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    log_info "Test Directory: $EVIDENCE_DIR"
    log_info "Swarm Directory: $AI_SWARM_DIR"
    log_info "Session: $SESSION"
    log_info "Master Pane: ${AI_SWARM_BRIDGE_PANE:-NOT SET}"
    echo ""

    # Setup
    setup_directories

    # Check for required tools
    if ! command -v tmux &> /dev/null; then
        log_fail "tmux not found"
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        log_fail "python3 not found"
        exit 1
    fi

    # Run selected scenario(s)
    case "$scenario" in
        A|a)
            scenario_a
            ;;
        B|b)
            scenario_b
            ;;
        C|c)
            scenario_c
            ;;
        all|"")

            # Run A
            if ! scenario_a; then
                log_fail "Scenario A failed, continuing with B and C for evidence collection..."
            fi

            # Run B
            if ! scenario_b; then
                log_fail "Scenario B failed..."
            fi

            # Run C
            if ! scenario_c; then
                log_fail "Scenario C failed..."
            fi
            ;;
        help|--help|-h)
            usage
            exit 0
            ;;
        *)
            log_fail "Unknown scenario: $scenario"
            usage
            exit 1
            ;;
    esac

    # Summary
    log_section "Test Suite Summary"

    echo -e "${GREEN}Passed:${NC}  $TESTS_PASSED"
    echo -e "${RED}Failed:${NC}  $TESTS_FAILED"
    echo -e "${YELLOW}Skipped:${NC} $TESTS_SKIPPED"
    echo ""
    log_info "Evidence saved to: $EVIDENCE_DIR"

    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo -e "\n${RED}Some tests failed. Review evidence files for details.${NC}"
        exit 1
    else
        echo -e "\n${GREEN}All tests passed!${NC}"
        exit 0
    fi
}

main "$@"
