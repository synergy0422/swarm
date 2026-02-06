# AI Swarm v1.93 Execution Plan: 主脑自然语言派发闭环

**Plan Version:** 1.0
**Created:** 2026-02-06
**Milestone:** v1.93 - Master Natural Language Dispatch Closure
**Status:** Ready for Execution

---

## 1. Executive Summary

This plan addresses the core issue: Master responds to `TASK:` but workers do not execute tasks reliably. The root cause is the absence of dispatch verification (ACK), retry logic, and failure recovery in the Bridge. We will implement a closed-loop protocol where Bridge generates a unique `bridge_task_id` for each task, injects it to workers, waits for `[ACK]` confirmation, retries on timeout with worker failover, and logs structured lifecycle phases. This enables full traceability from capture to completion and ensures eventual task delivery even when individual workers are unresponsive.

---

## 2. Root Cause Hypothesis

**Primary Hypothesis:** The dispatch mechanism in V1.92 sends tasks to worker panes via `send-keys` but has no verification that workers actually received and processed them. When workers fail to respond:

1. Bridge assumes dispatch succeeded and moves on
2. Master shows `[DISPATCHED->WORKER X]` but worker never processes
3. No timeout detection or retry triggers
4. User sees "only master replies" because worker output never appears

**Evidence Required (Phase 1):**
- Confirm `send-keys` reaches worker pane (tmux层面)
- Confirm worker Claude pane is listening for injected commands
- Identify if workers reject TASK: format or process silently
- Measure latency between dispatch and ACK (or lack thereof)

**Likely Contributing Factors:**
- Worker may be in thinking state and not processing new input
- Worker Claude pane may strip/ignore injected TASK: lines
- No heartbeat or ACK mechanism to detect failures
- FIFO fallback might have no reader (master not running)

---

## 3. Phase-by-Phase Plan

### Phase 1: Root Cause Debug (Evidence Gathering)

**Goal:** Gather deterministic evidence of where the dispatch chain breaks. NO code changes, only observation scripts.

**Duration Estimate:** 2-4 hours
**Complexity:** 3/5
**Dependencies:** None

#### Task 1.1: Create Debug Capture Script
**File:** `/home/user/projects/AAA/swarm/scripts/swarm_bridge_debug.sh` (new)

Create a standalone script that:
1. Starts tmux session with V1.92 layout (2 windows)
2. Launches Bridge with verbose logging to `bridge_debug.log`
3. Captures master pane output during bridge startup
4. Captures all worker pane outputs to separate files
5. Injects a test task and captures all pane states for 60 seconds

**Acceptance Criteria:**
- Script is idempotent (can run multiple times safely)
- All logs are timestamped with millisecond precision
- Single command produces comprehensive evidence bundle

#### Task 1.2: Verify Send-Keys Reachability
**File:** `/home/user/projects/AAA/swarm/scripts/swarm_bridge_debug.sh`

Add diagnostic that:
1. Injects a known unique string (e.g., `DEBUG_$(date +%s)_TEST`)
2. Immediately capture target worker pane
3. Check if injected string appears within 5 seconds
4. Repeat for all 3 workers to identify responsive ones

**Expected Output:**
```
Worker 0: INJECTED_1739999999_TEST -> FOUND in pane
Worker 1: INJECTED_1739999999_TEST -> NOT FOUND
Worker 2: INJECTED_1739999999_TEST -> FOUND in pane
```

**Acceptance Criteria:**
- Deterministic results (not flaky)
- Identifies which workers can receive injected text
- Captures tmux-level vs Claude-level difference

#### Task 1.3: Test Worker ACK Response
**File:** `/home/user/projects/AAA/swarm/scripts/swarm_bridge_debug.sh`

Add diagnostic that:
1. Sends `TASK: ACK_TEST_PLEASE_REPLY [bridge-task-id:TEST123]` to each worker
2. Captures worker pane for 30 seconds
3. Checks if worker outputs any response containing TEST123
4. Measures time to first response

**Acceptance Criteria:**
- Identifies if workers respond to TASK: format
- Measures response latency
- Determines if response is from Claude or just echo

#### Task 1.4: Output Root Cause Report
**File:** `/home/user/projects/AAA/swarm/.planning/milestones/v1.93/ROOT_CAUSE_REPORT.md`

Document:
1. What was tested (逐条列出)
2. What worked
3. What failed (with evidence)
4. Primary root cause (singular)
5. Secondary contributing factors
6. Recommended fix strategy

**Acceptance Criteria:**
- Report enables decision without re-running experiments
- Each claim has attached evidence (log snippets)
- Clear actionable recommendations for Phase 2

---

### Phase 2: Protocol Completion (ACK + Retry + Failover)

**Goal:** Implement closed-loop dispatch with verification and recovery.

**Duration Estimate:** 8-12 hours
**Complexity:** 5/5
**Dependencies:** Phase 1 complete with ROOT_CAUSE_REPORT

#### Task 2.1: Add Bridge Task ID Generation
**File:** `/home/user/projects/AAA/swarm/swarm/claude_bridge.py`

**Changes:**
- Add `BridgeTaskIdGenerator` class (new)
  - Generates unique IDs: `br-{timestamp}-{random_suffix}` format
  - Persists recent IDs for deduplication
  - Thread-safe generation

**Code Location:** After line 194 (after `DedupeState` class)

**Acceptance Criteria:**
- Each dispatched task gets unique ID
- ID format: `br-{unix_ns}-{3-char_suffix}` (e.g., `br-1739999999123-abc`)
- No ID collision within 1 hour window
- Existing tests pass (mock-based)

#### Task 2.2: Implement Structured Phase Logging
**File:** `/home/user/projects/AAA/swarm/swarm/claude_bridge.py`

**Changes:**
- Rename `_log_status()` to `_log_phase()` (or add new method)
- Add `Phase` enum: `CAPTURED`, `PARSED`, `DISPATCHED`, `ACKED`, `RETRY`, `FAILED`
- Update `_log_phase()` to:
  - Write structured JSON to `bridge.log`
  - Include: `ts`, `phase`, `bridge_task_id`, `task_preview`, `target_worker`, `attempt`, `latency_ms`

**Code Location:** Lines 546-583 (`_log_status` method)

**Acceptance Criteria:**
- Bridge.log format changes from:
  ```
  [2026-02-06 10:00:00] dispatched
  ```
  To:
  ```
  {"ts":"2026-02-06T10:00:00.000Z","phase":"DISPATCHED","bridge_task_id":"br-1234567890-abc","task":"Fix bug","target_worker":"%4","attempt":1}
  ```

#### Task 2.3: Enhance status.log Meta Fields
**File:** `/home/user/projects/AAA/swarm/swarm/claude_bridge.py`

**Changes:**
- Update `_log_status()` calls to include:
  - `meta.type=BRIDGE`
  - `meta.bridge_task_id`
  - `meta.target_worker`
  - `meta.attempt`
  - `meta.dispatch_mode` (fifo vs direct)

**Code Location:** Throughout `ClaudeBridge` class

**Acceptance Criteria:**
- All Bridge entries in status.log have required meta fields
- `jq '.meta' status.log` shows structured metadata
- Existing consumers of status.log remain compatible

#### Task 2.4: Implement ACK Detection
**File:** `/home/user/projects/AAA/swarm/swarm/claude_bridge.py`

**Changes:**
- Add `_wait_for_ack()` method:
  ```
  1. After dispatch to worker, capture pane state
  2. Loop for ACK_TIMEOUT (configurable, default 10s)
  3. Check for pattern: \[ACK\] <bridge-task-id>
  4. Return True on match, False on timeout
  ```
- Add `AI_SWARM_BRIDGE_ACK_TIMEOUT` env var (default: 10.0)

**New Method Location:** After `_dispatch_to_worker()` (around line 493)

**Acceptance Criteria:**
- Bridge waits for ACK after each direct dispatch
- ACK pattern configurable (default: `[ACK] br-XXX`)
- Clear logging of ACK success/failure
- ACK detection works across poll intervals

#### Task 2.5: Implement Retry with Worker Failover
**File:** `/home/user/projects/AAA/swarm/swarm/claude_bridge.py`

**Changes:**
- Add dispatch configuration:
  ```
  AI_SWARM_BRIDGE_MAX_RETRIES=3  # Per worker
  AI_SWARM_BRIDGE_RETRY_DELAY=2.0  # Seconds between retries
  ```
- Modify `_dispatch_to_worker()`:
  ```
  For each attempt up to max_retries:
    1. Select next worker (round-robin)
    2. Dispatch task with bridge_task_id
    3. Wait for ACK
    4. If ACK received: return success
    5. If timeout: log RETRY, increment attempt, continue
    6. If all workers failed: log FAILED, exit
  ```
- Add `BridgeDispatchError` exception class

**Code Location:** Rewrite `_dispatch_to_worker()` (lines 474-492)

**Acceptance Criteria:**
- Retry same worker first (N times)
- If same worker fails N times, switch to next worker
- Each attempt logged with latency
- Final failure includes all attempts in meta

#### Task 2.6: Add Dispatch Mode Explicit Tracking
**File:** `/home/user/projects/AAA/swarm/swarm/claude_bridge.py`

**Changes:**
- Add `dispatch_mode` attribute:
  - `fifo`: FIFO write succeeded
  - `direct`: FIFO unavailable, direct dispatch used
  - `direct_fallback`: FIFO failed, fell back to direct
- Track mode throughout dispatch flow
- Log mode in structured phases

**Code Location:** Around line 274 (in `__init__`)

**Acceptance Criteria:**
- Mode is known before dispatch
- Mode is logged with dispatch event
- Fallback behavior is explicit in logs

#### Task 2.7: Update Tests for New Protocol
**File:** `/home/user/projects/AAA/swarm/tests/test_claude_bridge.py`

**New Tests:**
- `TestBridgeTaskIdGenerator`: ID generation and uniqueness
- `TestAckDetection`: ACK pattern matching and timeout
- `TestRetryLogic`: Retry with failover scenarios
- `TestStructuredLogging`: bridge.log format validation
- `TestStatusLogMeta`: status.log meta field validation

**Modifications:**
- Update existing tests for new phase logging
- Mock ACK detection in dispatch tests

**Acceptance Criteria:**
- All tests pass
- Test coverage >= 80%
- Tests verify protocol behavior, not just API

---

### Phase 3: Observability Enhancement

**Goal:** Enable rapid diagnosis of dispatch issues.

**Duration Estimate:** 3-5 hours
**Complexity:** 2/5
**Dependencies:** Phase 2 complete

#### Task 3.1: Add Bridge Log Analysis Command
**File:** `/home/user/projects/AAA/swarm/scripts/swarm_bridge.sh` (new command) OR `/home/user/projects/AAA/swarm/swarm/cli.py`

Add `bridge-status` command:
```
Usage: ./scripts/swarm_bridge.sh status [OPTIONS]

Options:
  --recent N     Show last N bridge events (default: 10)
  --failed       Show only FAILED/RETRY events
  --task ID      Show lifecycle of specific bridge_task_id
  --phase PHASE  Filter by phase (CAPTURED|PARSED|DISPATCHED|ACKED|RETRY|FAILED)
  --json         Output as JSON for piping

Output Example:
  BRIDGE_TASK_ID      PHASE      WORKER  ATTEMPT  LATENCY_MS
  br-123456-abc       DISPATCHED %4      1        125
  br-123456-abc       ACKED      %4      1        340
```

**Acceptance Criteria:**
- Single command shows recent task lifecycle
- Filter by phase/worker/task_id works
- Latency calculations accurate
- JSON output for automation

#### Task 3.2: Add Dashboard Command
**File:** `/home/user/projects/AAA/swarm/scripts/swarm_bridge.sh` (new command)

Add `bridge-dashboard` command showing:
- Bridge running status (PID, uptime)
- Recent success/failure rates
- Last error with context
- Active dispatch operations

**Acceptance Criteria:**
- 30-second refresh with --watch flag
- Clear visual indication of health status
- Shows any stuck dispatches

#### Task 3.3: Document Observability Commands
**File:** `/home/user/projects/AAA/swarm/docs/MAINTENANCE.md`

Add section:
1. How to view bridge logs
2. Command reference for bridge-status/bridge-dashboard
3. Common patterns and their log signatures
4. Troubleshooting flowchart

**Acceptance Criteria:**
- New user can diagnose issue in < 2 minutes
- Examples cover all acceptance scenarios

---

### Phase 4: E2E Acceptance & Documentation

**Goal:** Verify all scenarios pass, document for future maintainers.

**Duration Estimate:** 4-6 hours
**Complexity:** 3/5
**Dependencies:** Phase 3 complete

#### Task 4.1: Create E2E Test Scripts
**File:** `/home/user/projects/AAA/swarm/scripts/swarm_e2e_v193.sh` (new)

Create comprehensive test script for scenarios:

**Scenario A: Single Task Closure**
```bash
1. Start V1.93 tmux session
2. Start bridge
3. Input: "TASK: 请只回复'received'"
4. Verify within 60s:
   - bridge.log shows: CAPTURED -> DISPATCHED -> ACKED
   - status.log has BRIDGE entry with bridge_task_id
   - worker pane outputs: received (actual Claude response)
5. Report: PASS/FAIL with evidence
```

**Scenario B: Three Sequential Tasks**
```bash
1. Input 3 different tasks rapidly
2. Verify:
   - bridge_task_id unique for each
   - Worker assignment follows round-robin
   - All 3 complete within 120s
3. Report: PASS/FAIL with lifecycle traces
```

**Scenario C: Exception Recovery**
```bash
1. Kill worker-1 Claude process (make unresponsive)
2. Dispatch task
3. Verify:
   - Bridge times out on worker-1
   - Retries worker-2, succeeds
   - Logs show RETRY -> DISPATCHED -> ACKED
4. Report: PASS/FAIL with failure explanation
```

**Acceptance Criteria:**
- All 3 scenarios pass deterministically
- Scripts are idempotent
- Evidence captured automatically

#### Task 4.2: Update Documentation
**Files:**
- `/home/user/projects/AAA/swarm/README.md` - Add v1.93 features
- `/home/user/projects/AAA/swarm/docs/ARCHITECTURE.md` - Update Bridge protocol section
- `/home/user/projects/AAA/swarm/docs/SCRIPTS.md` - Add bridge commands
- `/home/user/projects/AAA/swarm/CHANGELOG.md` - Add v1.93 entry

**Acceptance Criteria:**
- Documentation matches actual behavior
- New operators can run v1.93 from docs alone
- Version differences clearly called out

#### Task 4.3: Backward Compatibility Verification
**Files:** All scripts and docs

**Tests:**
1. V1.92 scripts (`swarm_layout_2windows.sh`, `swarm_bridge.sh`) still work
2. Existing status.log consumers unaffected
3. Environment variables are additive (new vars have defaults)

**Acceptance Criteria:**
- V1.92 users can upgrade without config changes
- No regression in existing functionality

---

## 4. Code Changes Summary

### Primary Changes to `/home/user/projects/AAA/swarm/swarm/claude_bridge.py`

| Location | Change | Complexity |
|----------|--------|------------|
| Lines 1-30 | Add docstring with ACK protocol | Low |
| After Line 194 | Add `BridgeTaskIdGenerator` class | Medium |
| After Line 250 | Add `BridgePhase` enum (CAPTURED/PARSED/etc) | Low |
| Around Line 274 | Add dispatch config attrs | Low |
| Around Line 474-493 | Rewrite `_dispatch_to_worker()` with ACK + retry | High |
| Around Line 370 | Add `_wait_for_ack()` method | Medium |
| Around Line 546 | Rename/update `_log_phase()` | Medium |
| Lines 617+ | Update main loop for new protocol | Medium |

### New Files

| File | Purpose |
|------|---------|
| `/home/user/projects/AAA/swarm/scripts/swarm_bridge_debug.sh` | Root cause evidence gathering |
| `/home/user/projects/AAA/swarm/scripts/swarm_e2e_v193.sh` | E2E acceptance tests |
| `/home/user/projects/AAA/swarm/.planning/milestones/v1.93/ROOT_CAUSE_REPORT.md` | Debug findings |

### Modified Files

| File | Changes |
|------|---------|
| `/home/user/projects/AAA/swarm/tests/test_claude_bridge.py` | 5 new test classes, ~100 lines |
| `/home/user/projects/AAA/swarm/docs/MAINTENANCE.md` | Observability section |
| `/home/user/projects/AAA/swarm/README.md` | v1.93 feature summary |
| `/home/user/projects/AAA/swarm/docs/ARCHITECTURE.md` | Bridge protocol updated |
| `/home/user/projects/AAA/swarm/CHANGELOG.md` | v1.93 entry |

---

## 5. Testing Strategy

### Unit Tests (pytest)

| Test Class | Coverage | Key Assertions |
|------------|----------|----------------|
| `TestBridgeTaskIdGenerator` | ID format, uniqueness | Format: `br-{ns}-{3}`; no collision |
| `TestAckDetection` | ACK pattern matching | Timeout detection, pattern capture |
| `TestRetryLogic` | Failover scenarios | Worker switch after N retries |
| `TestStructuredLogging` | bridge.log format | JSON schema validation |
| `TestStatusLogMeta` | status.log meta | All required fields present |
| `TestPhaseTransitions` | Lifecycle correctness | Proper phase ordering |

### E2E Tests (shell scripts)

| Scenario | Pass Criteria | Max Duration |
|----------|---------------|--------------|
| A: Single Task Closure | ACK + worker response within 60s | 120s |
| B: Three Sequential | Round-robin + 3 unique IDs within 120s | 180s |
| C: Exception Recovery | Timeout -> Retry -> Success within 60s | 90s |

### Manual Verification

| Check | Method |
|-------|--------|
| Prompt prefix handling | Input `❯ TASK: ...`, verify capture |
| Multi-pane safety | Run without AI_SWARM_BRIDGE_PANE, verify error |
| Backward compatibility | Run V1.92 scripts unchanged |

---

## 6. Risk Analysis

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Worker Claude ignores injected TASK: | High | Medium | Phase 1 evidence will reveal; may need worker-side injection format change |
| ACK pattern conflicts with Claude output | Medium | Low | Make ACK pattern configurable, default unlikely collision |
| Retry storms on worker failure | Medium | Medium | Cap total retries, add exponential backoff |
| Performance degradation with logging | Low | Low | Async logging option if needed |
| Breaking change to status.log format | Medium | Low | Meta field additive only; never remove fields |

### Contingency Plans

1. **If workers cannot ACK:**
   - Fall back to "dispatch acknowledged" by tmux success
   - Add separate health-check mechanism for workers
   - Document that ACK is best-effort

2. **If retry logic causes storms:**
   - Implement circuit breaker per worker
   - Global retry cap (not per-worker)
   - Alert on high retry rates

3. **If bridge.log format breaks parsing:**
   - Keep human-readable fallback line
   - Version the log format
   - Provide migration script

---

## 7. Rollback Plan

### Emergency Rollback (If v1.93 breaks production)

**Step 1: Stop Bridge**
```bash
./scripts/swarm_bridge.sh stop
```

**Step 2: Restore Previous Version**
```bash
git checkout v1.92 -- swarm/claude_bridge.py
```

**Step 3: Restart with Previous Bridge**
```bash
AI_SWARM_INTERACTIVE=1 ./scripts/swarm_bridge.sh start
```

**Rollback Time:** < 2 minutes

### Known State Transition Points

| Version | Breaking Change | Recovery Action |
|---------|----------------|-----------------|
| V1.92 -> V1.93 | bridge.log format | Parse both JSON and line formats |
| V1.92 -> V1.93 | status.log meta fields | Meta is additive; safe |

### Backup Commands

```bash
# Backup current state
cp -r /tmp/ai_swarm/bridge.log /tmp/ai_swarm/bridge.log.v193
cp swarm/claude_bridge.py swarm/claude_bridge.py.v193

# Restore
cp swarm/claude_bridge.py.v193 swarm/claude_bridge.py
```

---

## 8. Execution Checklist

### Before Starting Phase 1

- [ ] Read ROOT_CAUSE_REPORT from previous attempts (if exists)
- [ ] Verify tmux session can be created
- [ ] Confirm Claude Code CLI is accessible
- [ ] Backup current bridge.log and status.log

### Phase 1 Exit Criteria

- [ ] Debug script runs without errors
- [ ] Evidence of send-keys reachability (pass/fail)
- [ ] Evidence of worker ACK capability (pass/fail)
- [ ] ROOT_CAUSE_REPORT written with recommendations

### Phase 2 Exit Criteria

- [ ] All new classes have unit tests
- [ ] Unit tests pass (>80% coverage)
- [ ] Structured logging verified (JSON format)
- [ ] ACK detection working in isolation

### Phase 3 Exit Criteria

- [ ] `bridge-status` command works
- [ ] `bridge-dashboard` command works
- [ ] Documentation updated

### Phase 4 Exit Criteria

- [ ] Scenario A passes
- [ ] Scenario B passes
- [ ] Scenario C passes
- [ ] Backward compatibility verified
- [ ] Documentation complete

---

## 9. References

| Document | Path |
|----------|------|
| Requirements | `/home/user/projects/AAA/swarm/.planning/milestones/v1.93-REQUIREMENTS.md` |
| Roadmap | `/home/user/projects/AAA/swarm/.planning/milestones/v1.93-ROADMAP.md` |
| Current Implementation | `/home/user/projects/AAA/swarm/swarm/claude_bridge.py` |
| Bridge Launch Script | `/home/user/projects/AAA/swarm/scripts/swarm_bridge.sh` |
| Layout Script | `/home/user/projects/AAA/swarm/scripts/swarm_layout_5.sh` |
| Status Broadcaster | `/home/user/projects/AAA/swarm/swarm/status_broadcaster.py` |
| Existing Tests | `/home/user/projects/AAA/swarm/tests/test_claude_bridge.py` |

---

## 10. Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Plan Author | Claude Sonnet 4.5 | - | 2026-02-06 |
| Technical Review | (Pending) | | |
| Security Review | (Pending) | | |
| Final Approval | (Pending) | | |

---

**Plan Version:** 1.0
**Next Review:** After Phase 1 Root Cause Report
