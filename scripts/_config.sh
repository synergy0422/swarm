#!/usr/bin/env bash
# NOTE: This file is meant to be SOURCED by _common.sh, not executed directly
# No source guard needed here - only _common.sh sources this file

# =============================================================================
# Centralized Configuration for AI Swarm
# =============================================================================
# All configuration variables should be defined here with environment variable
# override support. Scripts should source _common.sh which sources this file.
#
# Variable priority (highest to lowest):
#   1. Explicit environment variable value (e.g., SWARM_STATE_DIR=/custom/path)
#   2. CLAUDE_SESSION (backward compatibility for v1.3)
#   3. Default value defined below
# =============================================================================

# State directory for locks, status logs, and task tracking
# Used by: swarm_lock.sh, swarm_status_log.sh, swarm_broadcast.sh
SWARM_STATE_DIR="${SWARM_STATE_DIR:-/tmp/ai_swarm}"

# tmux session name for the swarm
# Used by: swarmctl, all worker scripts
# Priority: explicit > CLAUDE_SESSION (v1.3 compat) > SESSION_NAME > default
SESSION_NAME="${CLAUDE_SESSION:-${SESSION_NAME:-swarm-claude-default}}"

# Worker names for task dispatch
# Used by: swarm_dispatch.sh, master_dispatcher.py
WORKERS="${WORKERS:-worker-0 worker-1 worker-2}"

# Logging verbosity level
# Options: DEBUG, INFO, WARN, ERROR
# DEBUG enables log_debug() output, INFO and above silences it
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Export all configuration variables for use by sourced scripts
export SWARM_STATE_DIR SESSION_NAME WORKERS LOG_LEVEL
