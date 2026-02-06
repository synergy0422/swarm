#!/usr/bin/env bash
set -euo pipefail

# Preferred entrypoint for the V1.92 2-window layout.
# Kept as a thin wrapper to preserve behavior in swarm_layout_5.sh.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/swarm_layout_5.sh" "$@"
