#!/usr/bin/env bash
set -euo pipefail

# One-click launcher for local proxy (cc-switch) + auto attach
# Usage: ./run_swarm_local_proxy_attach.sh [cluster_id] [workers]

CLUSTER_ID="${1:-default}"
WORKERS="${2:-3}"

# Local proxy endpoint (cc-switch)
export LLM_BASE_URL="http://127.0.0.1:15721"
# Placeholder API key (not used in proxy mode)
export ANTHROPIC_API_KEY="dummy"

cd "$(dirname "$0")"

python3 -m swarm.cli up --cluster-id "$CLUSTER_ID" --workers "$WORKERS"

echo
printf "[SWARM] Attaching to tmux session: swarm-%s\n" "$CLUSTER_ID"
exec tmux attach -t "swarm-$CLUSTER_ID"
