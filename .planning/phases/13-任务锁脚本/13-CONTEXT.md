# Phase 13: 任务锁脚本 - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Create `swarm_lock.sh` CLI script for task lock management in `/tmp/ai_swarm/locks/`.

Commands:
- `acquire <task_id> <worker> [ttl_seconds]` — Atomically acquire lock
- `release <task_id> <worker>` — Release lock (strict validation)
- `check <task_id>` — Check lock exists and status
- `list` — List all active locks

</domain>

<decisions>
## Implementation Decisions

### Lock file format
- All 4 fields: task_id, worker, acquired_at, expires_at
- TTL is optional (no default)
- User must explicitly provide TTL if they want lock expiry

### Acquire behavior
- Fail immediately if lock exists (atomic, O_CREAT|O_EXCL)
- Error message + non-zero exit code on failure
- Human readable output on success

### Release validation
- Strict match required: task_id AND worker must match the lock
- Error message + non-zero exit code on failure (wrong worker)

### TTL/Expiry
- Expired locks can be overridden (new acquire replaces expired lock)
- Check expiry on both acquire and list operations
- `check <task_id>` outputs: exists + status (active/expired)

</decisions>

<specifics>
## Specific Ideas

- Standard shell scripting patterns (like Phase 12's swarm_status_log.sh)
- SWARM_STATE_DIR environment variable support (default: /tmp/ai_swarm)
- Human-readable output by default

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-任务锁脚本*
*Context gathered: 2026-02-02*
