# Phase 6 Context: 集成测试

**Created:** 2026-01-31
**Phase:** 06-integration-testing

## Decisions

### 1. Test Environment: Hybrid Approach

| Test Type | Environment | Rationale |
|-----------|-------------|-----------|
| Unit/Logic tests | Mock tmux | Fast, deterministic, CI-friendly |
| E2E tests (1-2 key scenarios) | Real tmux sessions | Validates actual workflow |

- E2E tests marked with `@pytest.mark.integration` (skipped by default)
- Run with `pytest -m integration` when tmux available locally or in CI

### 2. E2E Test Runner: pytest integration

- Reuse existing pytest infrastructure:
  - `conftest.py` fixtures for isolation
  - `monkeypatch` for env injection
  - `tmp_path` for test directories
- Place E2E tests in `tests/test_e2e_*.py` or `tests/integration/`

### 3. Auto-rescue Testing: Unit + Integration Split

**Unit tests (pattern injection):**
- Test `WaitPatternDetector` and `AutoRescuer` pattern detection
- No tmux required, pure logic testing

**Integration test (real tmux):**
- Test ONE safe auto-rescue scenario: "Press ENTER" whitelisted pattern
- Skip `[y/n]` confirmations (dangerous, requires manual)

### 4. Verification Scope: Critical Paths Only

Verify these core workflows:

| # | Critical Path | Verification |
|---|---------------|--------------|
| 1 | `swarm up` startup | Master + N workers start, status.log shows RUNNING |
| 2 | Task dispatch flow | Master dispatch → mailbox/instructions → worker execution → status update |
| 3 | Status observation | `swarm status` displays correct state |
| 4 | Safe auto-rescue | Press ENTER pattern auto-confirms |
| 5 | Cleanup | `swarm down` terminates all sessions |

### 5. Test Cleanup: Debug-friendly Isolation

- Each test uses unique `cluster_id` (e.g., `test-001`, `test-002`)
- On failure: preserve tmux sessions for debugging
- On success: clean up automatically
- Sessions named `swarm-{cluster_id}` for easy identification

## Test Scenarios (E2E)

### Scenario 1: Happy Path - Task Distribution

```
1. Start: swarm up --workers 2 --cluster-id e2e-happy
2. Verify: status.log shows master + 2 workers RUNNING
3. Add task: Write to tasks.json with pending task
4. Verify: instructions/{worker_id}.jsonl receives instruction
5. Verify: status.log updates to ASSIGNED then DONE
6. Verify: swarm status shows task completed
7. Cleanup: swarm down --cluster-id e2e-happy
```

### Scenario 2: Safe Auto-rescue (Press ENTER)

```
1. Start: swarm up --workers 1 --cluster-id e2e-rescue
2. Simulate: Send command that outputs "Press ENTER to continue"
3. Verify: AutoRescuer detects pattern and sends Enter
4. Verify: Worker continues without hanging
5. Cleanup: swarm down --cluster-id e2e-rescue
```

## Excluded from Phase 6

- `[y/n]` auto-confirm testing (dangerous, opt-in)
- Multi-cluster interaction tests
- Performance/load testing
- Long-running stability tests

## Success Criteria

1. E2E tests pass with real tmux sessions
2. Auto-rescue unit tests cover pattern detection logic
3. One safe auto-rescue integration test passes
4. All critical paths verified end-to-end
5. 159+ existing unit tests still pass (no regression)
