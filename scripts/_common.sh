#!/usr/bin/env bash
# NOTE: No set -euo pipefail here - this file is sourced, not executed directly
# Each calling script should set its own error handling

# Guard: only allow sourcing, not direct execution
[[ "${BASH_SOURCE[0]}" != "${0}" ]] || exit 1

# Environment variables with fallbacks
# Priority: explicit value > CLAUDE_SESSION (v1.3 compat) > SESSION_NAME > swarm-claude-default
SWARM_STATE_DIR="${SWARM_STATE_DIR:-/tmp/ai_swarm}"
SESSION_NAME="${CLAUDE_SESSION:-${SESSION_NAME:-swarm-claude-default}}"
export SWARM_STATE_DIR SESSION_NAME

# Unified logging functions (output to stderr, NOT stdout)
# IMPORTANT: Use these for status/debug messages only, NOT for actual data output
log_info() { echo "[$(date +%H:%M:%S)][INFO] $*" >&2; }
log_warn() { echo "[$(date +%H:%M:%S)][WARN] $*" >&2; }
log_error() { echo "[$(date +%H:%M:%S)][ERROR] $*" >&2; }
