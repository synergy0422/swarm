#!/usr/bin/env bash
set -euo pipefail

# One-click launcher for local proxy (cc-switch)
# Usage: ./run_swarm_local_proxy.sh [cluster_id] [workers]

CLUSTER_ID="${1:-default}"
WORKERS="${2:-3}"

# Local proxy endpoint (cc-switch)
export LLM_BASE_URL="http://127.0.0.1:15721"
# Placeholder API key (not used in proxy mode)
export ANTHROPIC_API_KEY="dummy"

cd "$(dirname "$0")"

python3 -m swarm.cli up --cluster-id "$CLUSTER_ID" --workers "$WORKERS"

echo
printf "[SWARM] Attach: tmux attach -t swarm-%s\n" "$CLUSTER_ID"
printf "[SWARM] Status: python3 -m swarm.cli status --cluster-id %s --panes\n" "$CLUSTER_ID"
printf "[SWARM] Down:   python3 -m swarm.cli down --cluster-id %s\n" "$CLUSTER_ID"
