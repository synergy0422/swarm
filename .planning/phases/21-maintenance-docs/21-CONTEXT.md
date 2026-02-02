# Phase 21: 维护与扩展 - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Create maintenance documentation to support new contributors and operational sustainability:
- Update README.md with clear navigation to documentation
- Create docs/MAINTENANCE.md for environment recovery, troubleshooting, emergency procedures, maintenance checklist
- Create docs/SCRIPTS.md with complete script reference organized by category
- Create CHANGELOG.md covering v1.0-v1.6 with roadmap forward

</domain>

<decisions>
## Implementation Decisions

### README.md Structure

- **Content scope:** Brief - essentials (What is, Core Value, Quick Start, Common Commands, Links to docs)
- **Quick start:** 5-7 steps detailed (prerequisites: tmux/python, directory setup, environment variables, basic commands, verification)
- **Commands listed:** 6-8 commands (swarm init, swarm status, swarm selfcheck, swarm master, swarm worker, swarm task-wrap, swarm lock)
  - **IMPORTANT:** Commands listed as `swarm <verb>-<noun>` format map to scripts `swarm_<verb>_<noun>.sh` (e.g., "task-wrap" → `swarm_task_wrap.sh`)
- **Sections kept:** Standard set (What, Core Value, Quick Start, Commands, Architecture Overview, Requirements, Troubleshooting Highlights, Links to docs/MAINTENANCE.md, docs/SCRIPTS.md, CHANGELOG.md)

### docs/MAINTENANCE.md Content

- **Recovery procedures:** Standard recovery (reset state directory, restart tmux, clear locks, handle stuck workers, recover corrupted state, session reset)
- **Troubleshooting scenarios:** 8-10 common scenarios (tmux issues, script permissions, config errors, state directory problems, lock conflicts, permission errors)
- **Emergency procedures:** Standard emergency with explicit step order:
  1. 备份 (Backup) - Copy state directory before any destructive action
  2. 优雅停 (Graceful Stop) - Send SIGTERM, allow clean shutdown
  3. 强杀 (Force Kill) - SIGKILL if workers don't stop gracefully
  4. 清锁 (Clear Locks) - Remove all lock files from state directory
  5. 复验 (Verify) - Confirm system is in safe state before restart
- **Maintenance checklist:** Scheduled maintenance (daily/weekly/monthly tasks with time estimates, selfcheck, log review, cleanup)

### docs/SCRIPTS.md Organization

- **Organization:** By category (grouped by function: initialization, task management, status/lock, rescue, communication)
- **Script coverage:** Extended operations (init, status, lock, task-wrap, selfcheck, rescue, broadcast, config, common, comm)
- **Detail per script:** Standard reference (purpose, parameters, examples, output format, exit codes)
- **Examples per script:** Two examples (basic usage + common use case)

### CHANGELOG.md Format

- **Structure:** Categorized by type per version (Features, Bug Fixes, Under the Hood)
- **Detail level:** Brief - 3 bullets per version
- **Version coverage:** v1.0 to v1.6 with roadmap forward (future version placeholder, release cadence info)

</decisions>

<specifics>
## Specific Ideas

No specific references or examples provided - open to standard documentation approaches.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 21-maintenance-docs*
*Context gathered: 2026-02-03*
