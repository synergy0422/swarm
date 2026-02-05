#!/usr/bin/env bash
set -euo pipefail

# Source common functions and config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh" || true

log_info() { echo "[$(date +%H:%M:%S)][INFO] $*" >&2; }
log_error() { echo "[$(date +%H:%M:%S)][ERROR] $*" >&2; }

# Get FIFO path dynamically (uses AI_SWARM_DIR only)
get_fifo_path() {
    echo "${AI_SWARM_DIR:-/tmp/ai_swarm}/master_inbox"
}

# Non-blocking write to FIFO
# Returns 0 on success, 1 if no reader, 2 on other errors
write_fifo_nonblocking() {
    local fifo_path="$1"
    local text="$2"

    # Check if FIFO exists
    if [[ ! -p "$fifo_path" ]]; then
        return 2
    fi

    # Use Python for O_NONBLOCK write (bash doesn't have native support)
    python3 -c "
import os
import sys
import errno

fifo_path = sys.argv[1]
text = sys.argv[2]

try:
    fd = os.open(fifo_path, os.O_WRONLY | os.O_NONBLOCK)
    os.write(fd, (text + '\n').encode('utf-8'))
    os.close(fd)
    sys.exit(0)  # Success
except OSError as e:
    if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
        sys.exit(1)  # No reader
    sys.exit(2)  # Other error
" "$fifo_path" "$text"
}

usage() {
    cat << EOF
Usage: $(basename "$0") <command> [args]

Write task prompts to the master FIFO input channel.

Commands:
  write "<prompt>"  Write a single task prompt to FIFO
  write -           Read prompt from stdin
  help              Show this help message

Examples:
  $(basename "$0") write "Review PR #123"
  $(basename "$0") write - < input.txt
  echo "Task desc" | $(basename "$0") write -

Note: Uses non-blocking write - returns error if no reader.

Environment:
  AI_SWARM_DIR     Directory for swarm state (default: /tmp/ai_swarm)
EOF
}

cmd_write() {
    local prompt=""

    # Check for stdin flag
    if [[ "${1:-}" == "-" ]]; then
        if [[ -t 0 ]]; then
            log_error "No input on stdin"
            exit 1
        fi
        prompt=$(cat)
    else
        prompt="${1:-}"
    fi

    if [[ -z "$prompt" ]]; then
        log_error "No prompt provided"
        exit 1
    fi

    local fifo_path
    fifo_path=$(get_fifo_path)

    if [[ ! -p "$fifo_path" ]]; then
        log_error "FIFO not found: $fifo_path"
        log_error "Is master running with AI_SWARM_INTERACTIVE=1?"
        exit 1
    fi

    if ! write_fifo_nonblocking "$fifo_path" "$prompt"; then
        log_error "No reader on FIFO (is master running with AI_SWARM_INTERACTIVE=1?)"
        exit 1
    fi

    log_info "Task written to FIFO: ${prompt:0:50}..."
}

# Main
case "${1:-}" in
    write)
        cmd_write "${2:-}"
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        if [[ -n "${1:-}" ]]; then
            log_error "Unknown command: $1"
        fi
        usage
        exit 1
        ;;
esac
