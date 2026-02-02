#!/bin/bash
# Task lock management script for AI Swarm
# Supports atomic acquire/release/check/list operations

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

# Use SWARM_STATE_DIR from _common.sh
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
    acquire)
        # acquire <task_id> <worker> [ttl_seconds]
        if [ $# -lt 2 ]; then
            log_error "Error: 'acquire' requires <task_id> and <worker>"
            echo "Usage: $0 acquire <task_id> <worker> [ttl_seconds]" >&2
            exit 1
        fi

        TASK_ID="$1"
        WORKER="$2"
        TTL_SECONDS="${3:-}"

        # Calculate timestamps
        ACQUIRED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        if [ -n "$TTL_SECONDS" ]; then
            EXPIRES_AT=$(date -u -d "+${TTL_SECONDS} seconds" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v "${TTL_SECONDS}s" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "")
        else
            EXPIRES_AT=""
        fi

        # Use Python for atomic lock acquisition with O_CREAT|O_EXCL
        python3 - "$LOCK_DIR" "$TASK_ID" "$WORKER" "$ACQUIRED_AT" "$EXPIRES_AT" << 'PY'
import os
import sys
import json
import datetime

lock_dir, task_id, worker, acquired_at, expires_at = sys.argv[1:6]
lock_file = os.path.join(lock_dir, f"{task_id}.lock")

# Check if lock exists and is not expired
if os.path.exists(lock_file):
    try:
        with open(lock_file, 'r') as f:
            lock_data = json.load(f)
        # Check if lock is expired
        if lock_data.get('expires_at'):
            expires_at_dt = datetime.datetime.fromisoformat(lock_data['expires_at'].replace('Z', '+00:00'))
            if expires_at_dt > datetime.datetime.now(datetime.timezone.utc):
                print(f"Error: Lock already exists for '{task_id}'", file=sys.stderr)
                sys.exit(1)
        else:
            # Lock never expires, still exists
            print(f"Error: Lock already exists for '{task_id}'", file=sys.stderr)
            sys.exit(1)
    except (json.JSONDecodeError, KeyError):
        # Corrupted lock file, can be replaced
        pass

# Build lock data - all 4 fields present
lock_data = {
    "task_id": task_id,
    "worker": worker,
    "acquired_at": acquired_at,
    "expires_at": expires_at if expires_at else None
}

# Atomic create - will fail if file exists (race condition covered above)
try:
    fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(fd, 'w') as f:
        json.dump(lock_data, f, indent=2)
except FileExistsError:
    print(f"Error: Lock already exists for '{task_id}'", file=sys.stderr)
    sys.exit(1)

# Human-readable success output
print(f"Lock acquired for '{task_id}'")
print(f"  Worker: {worker}")
print(f"  Acquired: {acquired_at}")
if expires_at:
    print(f"  Expires: {expires_at}")
else:
    print(f"  Expires: never")
PY
        ;;
    release)
        # release <task_id> <worker>
        if [ $# -lt 2 ]; then
            log_error "Error: 'release' requires <task_id> and <worker>"
            echo "Usage: $0 release <task_id> <worker>" >&2
            exit 1
        fi

        TASK_ID="$1"
        WORKER="$2"
        LOCK_FILE="${LOCK_DIR}/${TASK_ID}.lock"

        if [ ! -f "$LOCK_FILE" ]; then
            log_error "Error: No lock found for '$TASK_ID'"
            exit 1
        fi

        # Read and parse existing lock JSON
        LOCK_DATA=$(python3 - "$LOCK_FILE" "$WORKER" << 'PY'
import sys
import json

lock_file = sys.argv[1]
expected_worker = sys.argv[2]

try:
    with open(lock_file, 'r') as f:
        lock_data = json.load(f)
except (json.JSONDecodeError, FileNotFoundError) as e:
    print(f"Error: Cannot read lock file", file=sys.stderr)
    sys.exit(2)

if lock_data.get('worker') != expected_worker:
    print(f"Error: Lock held by '{lock_data.get('worker')}', not '{expected_worker}'", file=sys.stderr)
    sys.exit(1)

# Success - delete the lock
import os
os.unlink(lock_file)
print(f"Lock released for '{sys.argv[1].split('/')[-1].replace('.lock', '')}'")
PY
)
        RESULT=$?
        if [ $RESULT -eq 0 ]; then
            echo "$LOCK_DATA"
        else
            exit $RESULT
        fi
        ;;
    check)
        # check <task_id>
        if [ $# -lt 1 ]; then
            log_error "Error: 'check' requires <task_id>"
            echo "Usage: $0 check <task_id>" >&2
            exit 1
        fi

        TASK_ID="$1"
        LOCK_FILE="${LOCK_DIR}/${TASK_ID}.lock"

        if [ ! -f "$LOCK_FILE" ]; then
            echo "No lock for '$TASK_ID'"
            exit 0
        fi

        # Read and check lock status
        python3 - "$LOCK_FILE" << 'PY'
import sys
import json
import datetime

lock_file = sys.argv[1]

try:
    with open(lock_file, 'r') as f:
        lock_data = json.load(f)
except (json.JSONDecodeError, FileNotFoundError) as e:
    print(f"Error: Cannot read lock file", file=sys.stderr)
    sys.exit(1)

# Determine status
task_id = lock_data.get('task_id', 'unknown')
worker = lock_data.get('worker', 'unknown')
acquired_at = lock_data.get('acquired_at', 'unknown')
expires_at = lock_data.get('expires_at')

# Check if expired
status = "Active"
if expires_at:
    try:
        expires_at_dt = datetime.datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        if expires_at_dt <= datetime.datetime.now(datetime.timezone.utc):
            status = "Expired"
    except (ValueError, TypeError):
        pass

# Output
print(f"Lock for '{task_id}': {status}")
print(f"  Worker: {worker}")
print(f"  Acquired: {acquired_at}")
if expires_at:
    print(f"  Expires: {expires_at}")
else:
    print(f"  Expires: never")
PY
        ;;
    list)
        # List all locks
        if [ ! -d "$LOCK_DIR" ]; then
            echo "No locks"
            exit 0
        fi

        # Use Python to list all .lock files
        python3 - "$LOCK_DIR" << 'PY'
import sys
import os
import json
import datetime
from pathlib import Path

lock_dir = Path(sys.argv[1])
locks = []

if not lock_dir.exists():
    print("No locks")
    sys.exit(0)

for lock_file in lock_dir.glob("*.lock"):
    try:
        with open(lock_file, 'r') as f:
            lock_data = json.load(f)

        task_id = lock_data.get('task_id', lock_file.stem)
        worker = lock_data.get('worker', 'unknown')
        acquired_at = lock_data.get('acquired_at', 'unknown')
        expires_at = lock_data.get('expires_at')

        # Determine status
        status = "Active"
        if expires_at:
            try:
                expires_at_dt = datetime.datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if expires_at_dt <= datetime.datetime.now(datetime.timezone.utc):
                    status = "Expired"
            except (ValueError, TypeError):
                pass

        locks.append({
            'task_id': task_id,
            'status': status,
            'worker': worker,
            'acquired_at': acquired_at,
            'expires_at': expires_at
        })
    except (json.JSONDecodeError, Exception):
        # Skip corrupted files
        pass

if not locks:
    print("No locks")
else:
    # Sort by task_id
    locks.sort(key=lambda x: x['task_id'])
    for lock in locks:
        expires_str = f", expires: {lock['expires_at']}" if lock['expires_at'] else ", expires: never"
        print(f"{lock['task_id']}: {lock['status']} (worker: {lock['worker']}, acquired: {lock['acquired_at']}{expires_str})")
PY
        ;;
    *)
        log_error "Error: Unknown command '$COMMAND'"
        usage
        exit 1
        ;;
esac
