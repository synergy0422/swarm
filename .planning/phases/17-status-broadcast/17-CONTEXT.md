# Phase 17: Status Broadcast - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Worker script that broadcasts status entries to `status.log` at key lifecycle points. Script-triggered only (no automatic detection). Integrates with existing `swarm_status_log.sh` and includes CONTRIBUTING.md documentation.

</domain>

<decisions>
## Implementation Decisions

### Trigger mechanism
- Manual/script invocation only
- No automatic detection of [DONE]/[ERROR] markers in pane content
- User or script calls broadcast command when appropriate

### Output format
- JSON Lines format: one JSON object per line
- Required fields:
  - `timestamp` — ISO 8601 format (e.g., 2026-02-02T10:30:00Z)
  - `type` — START, DONE, ERROR, or WAIT
  - `worker` — worker-0, worker-1, or worker-2
  - `task_id` — task identifier
- Optional fields:
  - `reason` — free-form reason or message

### Integration
- Create new script: `scripts/swarm_broadcast.sh`
- Internally calls `swarm_status_log.sh append` for actual file writes
- Reuses existing status.log location and format
- Consistent logging via `_common.sh` (log_info, log_warn, log_error)

### Error handling
- Write failure → stderr error message
- Non-zero exit code (fail fast, don't silently continue)
- Status: CLI user knows operation failed

### Documentation
- CONTRIBUTING.md documents script conventions and testing requirements
- Following patterns from existing scripts (_common.sh usage, logging, etc.)

</decisions>

<specifics>
## Specific Ideas

No specific references — standard approach using existing swarm patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 17-status-broadcast*
*Context gathered: 2026-02-02*
