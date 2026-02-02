#!/usr/bin/env bash
# NOTE: No set -euo pipefail here - this file is sourced, not executed directly
# Each calling script should set its own error handling

# Guard: only allow sourcing, not direct execution
[[ "${BASH_SOURCE[0]}" != "${0}" ]] || exit 1

# =============================================================================
# Source centralized configuration (with graceful degradation)
# =============================================================================
# _config.sh defines SWARM_STATE_DIR, SESSION_NAME, WORKERS, LOG_LEVEL
# with environment variable override support. If _config.sh is missing,
# fallback defaults are used.
#
# To skip loading _config.sh (for testing defaults), set:
#   SWARM_NO_CONFIG=1
# =============================================================================
_CONFIG_SCRIPT="$(dirname "${BASH_SOURCE[0]}")/_config.sh"
if [[ "${SWARM_NO_CONFIG:-0}" != "1" ]] && [[ -f "$_CONFIG_SCRIPT" ]]; then
    source "$_CONFIG_SCRIPT"
fi
unset _CONFIG_SCRIPT

# =============================================================================
# Fallback defaults if _config.sh is missing
# =============================================================================
# These are applied only when _config.sh cannot be sourced
SWARM_STATE_DIR="${SWARM_STATE_DIR:-/tmp/ai_swarm}"
SESSION_NAME="${CLAUDE_SESSION:-${SESSION_NAME:-swarm-claude-default}}"
WORKERS="${WORKERS:-worker-0 worker-1 worker-2}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
export SWARM_STATE_DIR SESSION_NAME WORKERS LOG_LEVEL

# Unified logging functions (output to stderr, NOT stdout)
# IMPORTANT: Use these for status/debug messages only, NOT for actual data output
log_info() { echo "[$(date +%H:%M:%S)][INFO] $*" >&2; }
log_warn() { echo "[$(date +%H:%M:%S)][WARN] $*" >&2; }
log_error() { echo "[$(date +%H:%M:%S)][ERROR] $*" >&2; }

# Debug logging - only outputs when LOG_LEVEL=DEBUG
log_debug() {
    if [[ "${LOG_LEVEL:-INFO}" == "DEBUG" ]]; then
        echo "[$(date +%H:%M:%S)][DEBUG] $*" >&2
    fi
}
