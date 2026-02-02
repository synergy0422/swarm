#!/bin/bash
# Task lock management script for AI Swarm
# Supports atomic acquire/release/check/list operations

set -euo pipefail

# Path configuration
SWARM_STATE_DIR="${SWARM_STATE_DIR:-/tmp/ai_swarm}"
LOCK_DIR="${SWARM_STATE_DIR}/locks"

# Ensure lock directory exists
mkdir -p "$LOCK_DIR"

# Usage function
usage() {
    cat <<EOF
Usage: $(basename "$0") <command> [arguments]

Commands:
    acquire <task_id> <worker> [ttl_seconds]    Atomically acquire task lock
    release <task_id> <worker>                  Release lock with strict owner validation
    check <task_id>                             Check lock exists and status (active/expired)
    list                                        List all active locks

Environment:
    SWARM_STATE_DIR     Override default /tmp/ai_swarm (default: /tmp/ai_swarm)

Examples:
    $(basename "$0") acquire task-001 worker-0
    $(basename "$0") acquire task-001 worker-0 3600
    $(basename "$0") release task-001 worker-0
    $(basename "$0") check task-001
    $(basename "$0") list
EOF
}

# Parse command line arguments
if [ $# -eq 0 ]; then
    usage
    exit 1
fi

COMMAND="$1"
shift

case "$COMMAND" in
    -h|--help|help)
        usage
        exit 0
        ;;
    acquire|release|check|list)
        # Valid command
        ;;
    *)
        echo "Error: Unknown command '$COMMAND'" >&2
        usage
        exit 1
        ;;
esac
