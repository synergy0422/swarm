#!/usr/bin/env bash
# E2E test script for status.log and locks integration
# Tests the complete workflow: acquire lock -> log START -> log DONE -> release lock

set -euo pipefail

# Use temp directory for complete isolation (no pollution of real data)
STATE_DIR="$(mktemp -d)"
export SWARM_STATE_DIR="$STATE_DIR"
STATUS_LOG="$STATE_DIR/status.log"
LOCK_DIR="$STATE_DIR/locks"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATUS_SCRIPT="$SCRIPT_DIR/swarm_status_log.sh"
LOCK_SCRIPT="$SCRIPT_DIR/swarm_lock.sh"

# Test tracking
TEST_NUM=1
FAILED=0
TESTS_PASSED=0
TESTS_FAILED=0

# Generate unique task_id for this test run
TEST_TASK_ID="e2e-test-$(date +%s)"

# Cleanup function - removes temp directory on exit
cleanup() {
    rm -rf "$STATE_DIR" 2>/dev/null || true
}
trap cleanup EXIT

# assert_pass - runs command and reports PASS/FAIL
assert_pass() {
    local description="$1"
    shift
    echo "Test $TEST_NUM: $description"
    if "$@"; then
        echo "  PASS"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "  FAIL"
        FAILED=1
        TESTS_FAILED=1
        exit 1
    fi
    TEST_NUM=$((TEST_NUM + 1))
}

# assert_contains - checks if file contains expected content (simple string match)
assert_contains() {
    local expected="$1"
    local file="$2"
    grep -F "$expected" "$file" > /dev/null 2>&1
}

echo "========================================"
echo "E2E Integration Test: status.log + locks"
echo "========================================"
echo ""
echo "State directory: $STATE_DIR"
echo "Test task ID: $TEST_TASK_ID"
echo ""

# Check dependencies are executable
[ -x "$LOCK_SCRIPT" ] || { echo "ERROR: $LOCK_SCRIPT not found or not executable"; exit 1; }
[ -x "$STATUS_SCRIPT" ] || { echo "ERROR: $STATUS_SCRIPT not found or not executable"; exit 1; }

echo "Dependencies verified"
echo ""

# Test 1: Acquire lock for unique task_id
assert_pass "Acquire lock for $TEST_TASK_ID" "$LOCK_SCRIPT" acquire "$TEST_TASK_ID" worker-e2e

# Test 2: Verify lock file exists in locks/
assert_pass "Verify lock file exists" test -f "$LOCK_DIR/${TEST_TASK_ID}.lock"

# Test 3: Append START record via swarm_status_log.sh
assert_pass "Append START record" "$STATUS_SCRIPT" append START worker-e2e "$TEST_TASK_ID"

# Test 4: Append DONE record via swarm_status_log.sh
assert_pass "Append DONE record" "$STATUS_SCRIPT" append DONE worker-e2e "$TEST_TASK_ID"

# Test 5: Release lock via swarm_lock.sh
assert_pass "Release lock" "$LOCK_SCRIPT" release "$TEST_TASK_ID" worker-e2e

# Test 6: Verify lock file deleted from locks/
assert_pass "Verify lock file deleted" test ! -f "$LOCK_DIR/${TEST_TASK_ID}.lock"

# Test 7: Verify status.log contains START record
assert_pass "Verify START record in status.log" assert_contains "\"task_id\":\"$TEST_TASK_ID\"" "$STATUS_LOG"

# Test 8: Verify status.log contains DONE record
assert_pass "Verify DONE record in status.log" assert_contains "\"type\":\"DONE\"" "$STATUS_LOG"

echo ""
echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo "E2E Test Summary: 8/8 tests passed"
else
    echo "E2E Test Summary: $TESTS_PASSED/8 tests passed"
fi
echo "========================================"
echo ""
echo "Status log contents:"
cat "$STATUS_LOG"
echo ""

exit 0
