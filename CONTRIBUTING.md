# Contributing to AI Swarm

Thank you for your interest in contributing to AI Swarm! This document outlines the conventions, patterns, and requirements for contributing to this project.

## Script Conventions

All shell scripts in this project follow a consistent structure and set of conventions.

### Required Boilerplate

Every script must include:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"
```

- `#!/usr/bin/env bash` - POSIX-compatible shebang
- `set -euo pipefail` - Strict error handling
  - `e`: Exit on error
  - `u`: Error on undefined variables
  - `o pipefail`: Pipeline fails if any command fails
- Source `_common.sh` for shared functionality

### Source Guard Pattern

The `_common.sh` file uses a source guard to prevent direct execution:

```bash
# In _common.sh - this allows sourcing but not running directly
[[ "${BASH_SOURCE[0]}" != "${0}" ]] || exit 1
```

Scripts that source `_common.sh` should NOT re-set this guard.

### Environment Variables

All scripts use these environment variables from `_common.sh`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SWARM_STATE_DIR` | `/tmp/ai_swarm` | Base directory for state files, locks, logs |
| `SESSION_NAME` | `swarm-claude-default` | tmux session name |

To override, set the variable before running:

```bash
SWARM_STATE_DIR=/custom/path ./scripts/swarm_status_log.sh append START worker-0 task-001
```

### Logging Functions

Use the logging functions from `_common.sh` for all status and debug messages:

```bash
log_info "Processing complete"    # INFO level
log_warn "Config may be outdated" # WARN level
log_error "Failed to connect"     # ERROR level
```

**Important:** These functions output to stderr (`>&2`), NOT stdout. This ensures logging doesn't interfere with data output from commands.

### Error Handling

- Use `set -euo pipefail` for fail-fast behavior
- Return non-zero exit codes on failure
- Use `log_error` for error messages before exiting
- Handle missing dependencies gracefully with clear error messages

### Session Handling

For consistency with legacy scripts, provide backward compatibility:

```bash
SESSION="${SESSION_NAME}"
```

The `--session` flag pattern for command-line override:

```bash
if [[ "${1:-}" == "--session" ]] && [[ -n "${2:-}" ]]; then
    SESSION="$2"
    shift 2
fi
```

---

## Status Broadcasting

AI Swarm uses a status broadcasting system to track worker lifecycle events.

### swarm_broadcast.sh

The `swarm_broadcast.sh` script provides a simplified interface for broadcasting status updates from worker windows.

#### Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `start <task_id> [reason]` | Broadcast START status | `./swarm_broadcast.sh start task-001` |
| `done <task_id> [reason]` | Broadcast DONE status | `./swarm_broadcast.sh done task-001 "Completed"` |
| `error <task_id> [reason]` | Broadcast ERROR status | `./swarm_broadcast.sh error task-002 "Failed"` |
| `wait <task_id> [reason]` | Broadcast WAIT status | `./swarm_broadcast.sh wait task-003 "Blocked"` |

#### Auto-Detection

The script automatically detects the current worker window using:

```bash
tmux display-message -p -t "$TMUX_PANE" '#{window_name}'
```

Valid worker windows are: `worker-0`, `worker-1`, `worker-2`.

#### Options

| Option | Purpose |
|--------|---------|
| `--session <name>` | Override tmux session name |

### swarm_status_log.sh

The `swarm_status_log.sh` script handles low-level status log operations.

#### Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `append <type> <worker> <task_id> [reason]` | Add entry to log | `append START worker-0 task-001` |
| `tail <n>` | Show last N entries | `tail 10` |
| `query <task_id>` | Find entries by task | `query task-001` |

#### Status Types

| Type | Meaning |
|------|---------|
| `START` | Worker began processing a task |
| `DONE` | Worker completed a task successfully |
| `ERROR` | Worker encountered an error |
| `WAIT` | Worker is waiting (blocked, dependencies) |
| `HELP` | Worker requested help/guidance |
| `SKIP` | Worker skipped a task |

#### Format Specification

Status entries are stored as JSON Lines:

```json
{"timestamp":"2026-02-02T19:00:00Z","type":"START","worker":"worker-0","task_id":"task-001"}
{"timestamp":"2026-02-02T19:00:05Z","type":"DONE","worker":"worker-0","task_id":"task-001","reason":"Completed successfully"}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | string | Yes | ISO 8601 UTC timestamp |
| `type` | string | Yes | Status type (START, DONE, etc.) |
| `worker` | string | Yes | Worker identifier (worker-0, worker-1, worker-2) |
| `task_id` | string | Yes | Task identifier |
| `reason` | string | No | Optional reason/description |

---

## Testing Requirements

All scripts must meet the following testing requirements.

### Basic Requirements

1. **Executable permissions**: Scripts must have execute permissions (`chmod +x`)
2. **Source verification**: Scripts must successfully source `_common.sh`
3. **Help verification**: Scripts should respond to `help`, `-h`, or `--help`

### Error Path Testing

Test that scripts handle error conditions properly:

- **Invalid commands**: Script should exit with non-zero code
- **Missing arguments**: Script should show usage and exit with non-zero code
- **Missing dependencies**: Script should fail with clear error message
- **Invalid inputs**: Script should validate and reject invalid inputs

```bash
# Example error path verification
./scripts/swarm_broadcast.sh invalid_cmd 2>/dev/null && echo "FAIL: no exit" || echo "PASS: non-zero exit"
./scripts/swarm_broadcast.sh start 2>/dev/null && echo "FAIL: no exit" || echo "PASS: non-zero exit"
```

### Integration Testing

For scripts that interact with other swarm components:

1. **Test with custom SWARM_STATE_DIR**: Use temporary directory for isolation
2. **Test swarm_status_log.sh integration**: Verify append/tail/query work together
3. **Test swarm_broadcast.sh integration**: Verify status entries appear in log

```bash
# Example integration test
export SWARM_STATE_DIR=$(mktemp -d)
./scripts/swarm_broadcast.sh start task-test-001 "Test start"
./scripts/swarm_status_log.sh query task-test-001
rm -rf "$SWARM_STATE_DIR"
```

### tmux-Dependent Scripts

For scripts that require tmux:

1. **Graceful degradation**: Handle missing tmux with clear error
2. **Session validation**: Verify session exists before operations
3. **Window validation**: Validate window names (worker-0/1/2)

---

## Adding New Scripts

Follow these steps when adding new scripts to the project.

### Naming Convention

- Use `swarm_*.sh` prefix for swarm-related scripts
- Use descriptive names: `swarm_broadcast.sh`, `swarm_status_log.sh`
- Avoid generic names like `script.sh` or `util.sh`

### File Structure

```
scripts/
├── _common.sh              # Shared configuration and utilities
├── swarm_broadcast.sh      # Status broadcasting wrapper
├── swarm_status_log.sh     # Status log operations
└── claude_auto_rescue.sh   # Auto-confirm prompts
```

### Implementation Checklist

- [ ] Script follows required boilerplate (shebang, set, sourcing)
- [ ] Script sources `_common.sh` for shared functionality
- [ ] Script uses logging functions (`log_info`, `log_warn`, `log_error`)
- [ ] Script handles errors with non-zero exit codes
- [ ] Script supports `--session` flag for tmux session override
- [ ] Script is executable (`chmod +x`)
- [ ] Script has working help (`-h`, `--help`, or `help`)
- [ ] Script is documented in this CONTRIBUTING.md
- [ ] Tests are added if applicable

### Documentation

Add your script to the appropriate section:

- For status/logging scripts: Update "Status Broadcasting" section
- For tmux automation scripts: Update relevant sections
- For new categories: Add new section with usage examples

---

## Development Workflow

### Local Testing

1. Create a temporary state directory:
   ```bash
   export SWARM_STATE_DIR=$(mktemp -d)
   ```

2. Test your script:
   ```bash
   ./scripts/your_script.sh command argument
   ```

3. Verify outputs:
   ```bash
   ./scripts/swarm_status_log.sh tail 10
   ```

4. Cleanup:
   ```bash
   rm -rf "$SWARM_STATE_DIR"
   ```

### tmux Session Setup

For testing tmux-dependent scripts:

```bash
# Create a test session
tmux new-session -d -s swarm-test

# Create worker windows
tmux new-window -t swarm-test -n worker-0
tmux new-window -t swarm-test -n worker-1
tmux new-window -t swarm-test -n worker-2

# Attach for manual testing
tmux attach-session -t swarm-test
```

---

## Quick Reference

### Common Commands

```bash
# Status broadcasting
./scripts/swarm_broadcast.sh start task-001
./scripts/swarm_broadcast.sh done task-001 "Done"
./scripts/swarm_broadcast.sh error task-002 "Failed"
./scripts/swarm_broadcast.sh wait task-003 "Waiting"

# Status log operations
./scripts/swarm_status_log.sh append START worker-0 task-001
./scripts/swarm_status_log.sh tail 10
./scripts/swarm_status_log.sh query task-001

# With custom state directory
SWARM_STATE_DIR=/custom/path ./scripts/swarm_broadcast.sh start task-001

# With custom session
./scripts/swarm_broadcast.sh --session custom-session start task-001
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SWARM_STATE_DIR` | `/tmp/ai_swarm` | State directory for logs and locks |
| `SESSION_NAME` | `swarm-claude-default` | tmux session name |
| `TMUX_PANE` | (set by tmux) | Current tmux pane (auto-detected) |
