#!/usr/bin/env bash

# Claude Swarm Status Check
# Displays last 10 lines from all swarm windows

SESSION="swarm-claude-default"

echo "=== Claude Swarm Status ==="
echo ""

WINDOWS="master worker-0 worker-1 worker-2"

for window in $WINDOWS; do
    echo "--- $window ---"
    tmux capture-pane -t "$SESSION:$window" -p | tail -10
    echo ""
done
