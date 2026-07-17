#!/usr/bin/env bash
# Reports whether a MUD session is currently active, and shows the last few
# lines of the screen without consuming the read offset (unlike mud_read.sh).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/mud_env.sh"

if tmux has-session -t "$MUD_SESSION" 2>/dev/null; then
  echo "Session '$MUD_SESSION' is running ($MUD_HOST:$MUD_PORT, user $MUD_USER)."
  echo "----"
  tmux capture-pane -t "$MUD_SESSION" -p | tail -n 8
else
  echo "No active session named '$MUD_SESSION'."
fi
