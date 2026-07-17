#!/usr/bin/env bash
# Sends a single command line to the MUD and prints whatever new output comes
# back. All arguments are joined with spaces into one command line, so
# `mud_send.sh say hello there` sends the single line "say hello there".
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/mud_env.sh"

if [ $# -lt 1 ]; then
  echo "Usage: mud_send.sh <command text...>" >&2
  exit 1
fi

if ! tmux has-session -t "$MUD_SESSION" 2>/dev/null; then
  echo "No active MUD session. Run mud_start.sh first." >&2
  exit 1
fi

PRE_TOTAL=$(mud_total_lines)
tmux send-keys -t "$MUD_SESSION" -l -- "$*"
tmux send-keys -t "$MUD_SESSION" Enter

# Wait for the next status prompt to know the MUD finished responding.
# Commands that don't produce one (e.g. "quit") just fall through to the
# plain wait below instead.
if ! mud_wait_for_new_prompt "$PRE_TOTAL" 5; then
  sleep "$MUD_WAIT"
fi

"$DIR/mud_read.sh"
