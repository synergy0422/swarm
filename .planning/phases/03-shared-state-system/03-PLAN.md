---
phase: 03-shared-state-system
plan: '01'
type: execute
wave: 1
depends_on: []
files_modified:
  - /home/user/AAA/swarm/swarm/status_broadcaster.py
  - /home/user/AAA/swarm/tests/test_status_broadcaster.py
  - /home/user/AAA/swarm/swarm/task_lock.py
  - /home/user/AAA/swarm/tests/test_task_lock.py
  - /home/user/AAA/swarm/swarm/__init__.py
autonomous: true
user_setup: []

must_haves:
  truths:
    - Status log writes in JSONL format to /tmp/ai_swarm/status.log
    - Task locks prevent duplicate execution using atomic file creation
    - Heartbeat updates every 10s, TTL default 300s (override via AI_SWARM_LOCK_TTL)
    - Lazy cleanup of expired locks
  artifacts:
    - path: /home/user/AAA/swarm/swarm/status_broadcaster.py
      provides: StatusBroadcaster class for JSONL status logging
      exports: ['StatusBroadcaster', 'BroadcastState']
    - path: /home/user/AAA/swarm/swarm/task_lock.py
      provides: TaskLockManager class for atomic task locking
      exports: ['TaskLockManager', 'LockInfo']
    - path: /home/user/AAA/swarm/tests/test_status_broadcaster.py
      provides: Unit tests for status broadcaster (10+ tests)
    - path: /home/user/AAA/swarm/tests/test_task_lock.py
      provides: Unit tests for task lock (15+ tests)
  key_links:
    - from: /home/user/AAA/swarm/swarm/status_broadcaster.py
      to: /tmp/ai_swarm/status.log
      via: os.path.join with AI_SWARM_DIR
    - from: /home/user/AAA/swarm/swarm/task_lock.py
      to: /tmp/ai_swarm/locks/
      via: os.path.join with AI_SWARM_DIR
    - from: /home/user/AAA/swarm/swarm/__init__.py
      to: status_broadcaster.py and task_lock.py
      via: module exports
---

<objective>
Create the shared state system with status broadcasting and task locking capabilities for multi-agent coordination.

Purpose: Enable multiple Workers to coordinate task execution, avoid duplicates, and broadcast status updates to Master.

Output:
- `status_broadcaster.py` with StatusBroadcaster class for JSONL status logging
- `task_lock.py` with TaskLockManager class for atomic file-based task locking
- Comprehensive unit tests for both modules
</objective>

<execution_context>
@/home/user/.claude/get-shit-done/workflows/execute-plan.md
@/home/user/.claude/get-shit-done/templates/summary.md

# Existing patterns to follow:
@/home/user/AAA/swarm/swarm/config.py (env var pattern: os.environ.get + default)
@/home/user/AAA/swarm/tests/conftest.py (test isolation via isolated_swarm_dir fixture)
@/home/user/AAA/swarm/tests/test_task_queue.py (test structure pattern)
</execution_context>

<context>
@/home/user/AAA/swarm/.planning/PROJECT.md
@/home/user/AAA/swarm/.planning/ROADMAP.md
@/home/user/AAA/swarm/.planning/STATE.md
@/home/user/AAA/swarm/.planning/phases/03-shared-state-system/03-CONTEXT.md

## Implementation constraints (from Phase 1 decisions):
1. API key only from env vars - NO dotenv loading
2. Auto-create /tmp/ai_swarm with os.makedirs(exist_ok=True)
3. AI_SWARM_DIR override with os.path.join for paths
4. Tests are isolated via pytest fixture (conftest.py)

## Key implementation decisions (from 03-CONTEXT.md):

### Status Protocol Format:
- JSON Lines (one JSON object per line)
- Fields: state, task_id, timestamp (ISO 8601 ms), message, meta
- States: START, DONE, WAIT, ERROR, HELP, SKIP (fixed, no细分)
- Path: {AI_SWARM_DIR}/status.log (default: /tmp/ai_swarm/status.log)

### Lock Implementation:
- Atomic file creation with O_CREAT|O_EXCL (NOT fcntl.flock)
- Per-task locks at {AI_SWARM_DIR}/locks/{task_id}.lock
- Lock content: worker_id, task_id, acquired_at, heartbeat_at, ttl
- TTL: default 300s, override via AI_SWARM_LOCK_TTL env var
- Heartbeat: update every 10s
- Competition: expired locks are lazily cleaned and抢占; non-expired fails fast
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create status_broadcaster.py with StatusBroadcaster class</name>
  <files>/home/user/AAA/swarm/swarm/status_broadcaster.py</files>
  <action>
Create `/home/user/AAA/swarm/swarm/status_broadcaster.py` with:

1. **BroadcastState enum** with values: START, DONE, WAIT, ERROR, HELP, SKIP

2. **StatusBroadcaster class** with:
   - `__init__(self, worker_id: str)` - initialize with worker ID, auto-create AI_SWARM_DIR
   - `_get_status_log_path(self) -> str` - return os.path.join(AI_SWARM_DIR, 'status.log')
   - `broadcast(self, state: BroadcastState, task_id: str, message: str = "", meta: dict = None)` - append JSONL line to status.log
   - `broadcast_start(self, task_id: str, message: str = "")` - convenience method for START
   - `broadcast_done(self, task_id: str, message: str = "")` - convenience method for DONE
   - `broadcast_wait(self, task_id: str, message: str = "")` - convenience method for WAIT
   - `broadcast_error(self, task_id: str, message: str = "")` - convenience method for ERROR
   - `broadcast_help(self, task_id: str, message: str = "")` - convenience method for HELP
   - `broadcast_skip(self, task_id: str, message: str = "")` - convenience method for SKIP

3. **JSONL format** for each status line:
   ```python
   {
       "state": "START",  # or DONE/WAIT/ERROR/HELP/SKIP
       "task_id": "task-123",
       "timestamp": "2026-01-31T12:00:00.000Z",  # ISO 8601 with milliseconds
       "message": "开始执行",  # optional
       "meta": {"error_type": "timeout"}  # optional
   }
   ```

4. **Auto-create directory**: Use `os.makedirs(os.path.dirname(path), exist_ok=True)` before writing

5. **Atomic write**: Write to temp file first, then rename to target path (like task_queue.py pattern)
</action>
  <verify>
Run tests: `pytest /home/user/AAA/swarm/tests/test_status_broadcaster.py -v`
All tests pass (10+ tests for status broadcasting)
</verify>
  <done>
- StatusBroadcaster class exists with all 6 broadcast methods
- JSONL format matches specification
- Auto-creates /tmp/ai_swarm/ and status.log
- Atomic write pattern implemented
- 10+ unit tests passing
</done>
</task>

<task type="auto">
  <name>Task 2: Create test_status_broadcaster.py with comprehensive tests</name>
  <files>/home/user/AAA/swarm/tests/test_status_broadcaster.py</files>
  <action>
Create `/home/user/AAA/swarm/tests/test_status_broadcaster.py` with:

1. **Test class structure** following test_task_queue.py pattern

2. **Test cases** for StatusBroadcaster:
   - `test_broadcast_start_creates_jsonl_line` - verify START state format
   - `test_broadcast_done_creates_jsonl_line` - verify DONE state format
   - `test_broadcast_wait_creates_jsonl_line` - verify WAIT state format
   - `test_broadcast_error_creates_jsonl_line` - verify ERROR state format
   - `test_broadcast_help_creates_jsonl_line` - verify HELP state format
   - `test_broadcast_skip_creates_jsonl_line` - verify SKIP state format
   - `test_broadcast_with_message` - verify message field is written
   - `test_broadcast_with_meta` - verify meta field is written
   - `test_broadcast_timestamp_format` - verify ISO 8601 with milliseconds
   - `test_broadcast_creates_directory` - verify auto-creation of AI_SWARM_DIR
   - `test_broadcast_multiple_lines` - verify JSONL format (multiple lines)
   - `test_convenience_methods` - verify broadcast_start/done/etc work

3. **Test isolation**: Use `isolated_swarm_dir` fixture from conftest.py

4. **Assertions**: Verify JSONL content, timestamp format, file existence
</action>
  <verify>
Run: `pytest /home/user/AAA/swarm/tests/test_status_broadcaster.py -v --tb=short`
Verify: All 10+ tests pass
</verify>
  <done>
- test_status_broadcaster.py exists with 10+ test cases
- All tests use isolated_swarm_dir fixture
- Tests cover all broadcast states and edge cases
- All tests passing
</done>
</task>

<task type="auto">
  <name>Task 3: Create task_lock.py with TaskLockManager class</name>
  <files>/home/user/AAA/swarm/swarm/task_lock.py</files>
  <action>
Create `/home/user/AAA/swarm/swarm/task_lock.py` with:

1. **LockInfo dataclass** with:
   - worker_id: str
   - task_id: str
   - acquired_at: str (ISO 8601 timestamp)
   - heartbeat_at: str (ISO 8601 timestamp)
   - ttl: int (seconds)

2. **TaskLockManager class** with:
   - `__init__(self, worker_id: str)` - initialize with worker ID, auto-create locks dir
   - `_get_locks_dir(self) -> str` - return os.path.join(AI_SWARM_DIR, 'locks')
   - `_get_lock_path(self, task_id: str) -> str` - return {locks_dir}/{task_id}.lock
   - `_get_ttl(self) -> int` - return AI_SWARM_LOCK_TTL env var or 300
   - `acquire_lock(self, task_id: str) -> bool` - atomic lock acquisition
     * Check if lock file exists
     * If exists and expired: delete old lock (lazy cleanup)
     * If exists and not expired: return False (fast fail)
     * If not exists: atomically create with O_CREAT|O_EXCL
     * Write lock JSON with worker_id, task_id, acquired_at, heartbeat_at, ttl
   - `release_lock(self, task_id: str) -> bool` - release lock by deleting file
   - `update_heartbeat(self, task_id: str) -> bool` - update heartbeat_at timestamp
     * Must verify this worker owns the lock (worker_id matches)
     * Use atomic write pattern (temp file + rename)
   - `is_locked(self, task_id: str) -> bool` - check if task is locked
   - `get_lock_info(self, task_id: str) -> LockInfo | None` - read lock info
   - `is_expired(self, lock: LockInfo) -> bool` - check if lock is expired

3. **Atomic file creation pattern**:
   ```python
   import os
   flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
   fd = os.open(path, flags, 0o644)
   with os.fdopen(fd, 'w') as f:
       json.dump(lock_data, f)
   ```

4. **Heartbeat update** every 10 seconds (called by worker during task execution)

5. **Auto-create locks directory**: `os.makedirs(self._get_locks_dir(), exist_ok=True)`
</action>
  <verify>
Run: `pytest /home/user/AAA/swarm/tests/test_task_lock.py -v`
All tests pass (15+ tests for task locking)
</verify>
  <done>
- TaskLockManager class exists with all lock methods
- Atomic O_CREAT|O_EXCL lock acquisition implemented
- Heartbeat update every 10s (configurable via AI_SWARM_LOCK_TTL)
- Lazy cleanup of expired locks
- 15+ unit tests passing
</done>
</task>

<task type="auto">
  <name>Task 4: Create test_task_lock.py with comprehensive tests</name>
  <files>/home/user/AAA/swarm/tests/test_task_lock.py</files>
  <action>
Create `/home/user/AAA/swarm/tests/test_task_lock.py` with:

1. **Test class structure** following test_task_queue.py pattern

2. **Test cases** for TaskLockManager:
   - `test_acquire_lock_creates_lock_file` - verify lock file created
   - `test_acquire_lock_returns_true_on_success` - verify True return
   - `test_acquire_lock_returns_false_if_locked` - verify fast fail on occupied lock
   - `test_acquire_lock_allows抢占_expired` - verify expired locks can be抢占
   - `test_release_lock_deletes_file` - verify lock file deleted
   - `test_release_lock_returns_false_if_not_owned` - verify ownership check
   - `test_update_heartbeat` - verify heartbeat_at updated
   - `test_update_heartbeat_fails_if_not_owned` - verify ownership check
   - `test_is_locked` - verify correct locked state
   - `test_get_lock_info` - verify lock info returned
   - `test_is_expired_within_ttl` - verify not expired within TTL
   - `test_is_expired_past_ttl` - verify expired after TTL
   - `test_lock_content_json_format` - verify JSON format with all fields
   - `test_heartbeat_interval_default` - verify default 10s interval
   - `test_ttl_env_override` - verify AI_SWARM_LOCK_TTL override
   - `test_convenience_methods` - verify acquire/release work

3. **Test isolation**: Use `isolated_swarm_dir` fixture from conftest.py

4. **Race condition testing**: Test that two processes cannot both acquire same lock

5. **Expiration testing**: Mock time to test expiration logic
</action>
  <verify>
Run: `pytest /home/user/AAA/swarm/tests/test_task_lock.py -v --tb=short`
Verify: All 15+ tests pass
</verify>
  <done>
- test_task_lock.py exists with 15+ test cases
- All tests use isolated_swarm_dir fixture
- Tests cover lock acquisition, release, heartbeat, expiration
- All tests passing
</done>
</task>

<task type="auto">
  <name>Task 5: Update __init__.py to export new modules</name>
  <files>/home/user/AAA/swarm/swarm/__init__.py</files>
  <action>
Update `/home/user/AAA/swarm/swarm/__init__.py` to:

1. Add imports for new modules:
   ```python
   from swarm.status_broadcaster import StatusBroadcaster, BroadcastState
   from swarm.task_lock import TaskLockManager, LockInfo
   ```

2. Update `__all__` to include:
   ```python
   __all__ = [
       'TaskQueue',
       'SmartWorker',
       'TmuxSwarmManager',
       'AgentStatus',
       'AgentPane',
       'TmuxSwarmError',
       'StatusBroadcaster',
       'BroadcastState',
       'TaskLockManager',
       'LockInfo',
   ]
   ```
</action>
  <verify>
Run: `python -c "from swarm import StatusBroadcaster, TaskLockManager, BroadcastState, LockInfo; print('Imports successful')"`
Verify: No ImportError, all exports available
</verify>
  <done>
- __init__.py updated with new exports
- All new classes importable from swarm package
</done>
</task>

</tasks>

<verification>
Run comprehensive verification:

1. **Module imports work:**
   ```bash
   python -c "from swarm import StatusBroadcaster, TaskLockManager, BroadcastState, LockInfo; print('OK')"
   ```

2. **Status broadcaster tests:**
   ```bash
   pytest /home/user/AAA/swarm/tests/test_status_broadcaster.py -v
   # Expected: 10+ tests pass
   ```

3. **Task lock tests:**
   ```bash
   pytest /home/user/AAA/swarm/tests/test_task_lock.py -v
   # Expected: 15+ tests pass
   ```

4. **All existing tests still pass:**
   ```bash
   pytest /home/user/AAA/swarm/tests/ -v --ignore=/home/user/AAA/swarm/tests/verify_swarm_v2.py
   # Expected: All tests pass (including previous phases)
   ```

5. **Functional verification:**
   ```bash
   python -c "
   from swarm import StatusBroadcaster, TaskLockManager
   import tempfile
   import os

   # Test StatusBroadcaster
   with tempfile.TemporaryDirectory() as tmp:
       os.environ['AI_SWARM_DIR'] = tmp
       sb = StatusBroadcaster('worker-1')
       sb.broadcast_start('task-001', 'Test task')
       with open(os.path.join(tmp, 'status.log')) as f:
           content = f.read()
           assert 'START' in content
           assert 'task-001' in content
           print('StatusBroadcaster: OK')

   # Test TaskLockManager
   with tempfile.TemporaryDirectory() as tmp:
       os.environ['AI_SWARM_DIR'] = tmp
       tl = TaskLockManager('worker-1')
       acquired = tl.acquire_lock('task-001')
       assert acquired == True
       info = tl.get_lock_info('task-001')
       assert info is not None
       assert info.worker_id == 'worker-1'
       print('TaskLockManager: OK')
   "
   ```
</verification>

<success_criteria>
Phase 3 complete when:

1. [ ] `/home/user/AAA/swarm/swarm/status_broadcaster.py` exists with StatusBroadcaster class
2. [ ] `/home/user/AAA/swarm/swarm/task_lock.py` exists with TaskLockManager class
3. [ ] `/home/user/AAA/swarm/tests/test_status_broadcaster.py` has 10+ passing tests
4. [ ] `/home/user/AAA/swarm/tests/test_task_lock.py` has 15+ passing tests
5. [ ] `/home/user/AAA/swarm/swarm/__init__.py` exports all new classes
6. [ ] All previous phase tests still pass (23 tests for tmux_manager)
7. [ ] Status log writes in JSONL format to {AI_SWARM_DIR}/status.log
8. [ ] Task locks use atomic file creation (O_CREAT|O_EXCL)
9. [ ] Heartbeat updates every 10s, TTL default 300s
10. [ ] Expired locks are lazily cleaned and抢占到

Success metric: `pytest /home/user/AAA/swarm/tests/` passes with 50+ tests total
</success_criteria>

<output>
After completion, create `.planning/phases/03-shared-state-system/03-01-SUMMARY.md`
</output>
