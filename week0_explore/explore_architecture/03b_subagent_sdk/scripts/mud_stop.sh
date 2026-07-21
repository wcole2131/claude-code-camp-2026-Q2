#!/usr/bin/env bash
# Gracefully quits the MUD (if connected) and tears down the tmux session.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/mud_env.sh"

if tmux has-session -t "$MUD_SESSION" 2>/dev/null; then
  tmux send-keys -t "$MUD_SESSION" -l -- "quit"
  tmux send-keys -t "$MUD_SESSION" Enter
  sleep 1
  tmux kill-session -t "$MUD_SESSION" 2>/dev/null || true
  echo "Sent quit and closed session '$MUD_SESSION'."
else
  echo "No active session to stop."
fi

rm -f "$MUD_STATE_DIR/offset"
