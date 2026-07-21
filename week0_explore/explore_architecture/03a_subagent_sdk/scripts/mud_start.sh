#!/usr/bin/env bash
# Opens a detached tmux session running telnet against the MUD, and logs in
# with the configured character. Safe to call when a session is already
# running -- it will just report the existing session instead of duplicating it.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/mud_env.sh"

if tmux has-session -t "$MUD_SESSION" 2>/dev/null; then
  echo "Session '$MUD_SESSION' is already running. Use mud_read.sh to see recent output, or mud_stop.sh to disconnect first."
  exit 0
fi

mkdir -p "$MUD_STATE_DIR"
rm -f "$MUD_STATE_DIR/offset"

tmux new-session -d -s "$MUD_SESSION" -x 200 -y 50
tmux set-option -t "$MUD_SESSION" history-limit 5000

tmux send-keys -t "$MUD_SESSION" -l -- "telnet $MUD_HOST $MUD_PORT"
tmux send-keys -t "$MUD_SESSION" Enter

# The client-detection negotiation before the name prompt has variable
# timing, so wait for the actual prompt text at each step rather than
# guessing a fixed delay.
if ! mud_wait_for_text "By what name" 20; then
  echo "Timed out waiting for the name prompt. Current screen:" >&2
  tmux capture-pane -t "$MUD_SESSION" -p >&2
  exit 1
fi
tmux send-keys -t "$MUD_SESSION" -l -- "$MUD_USER"
tmux send-keys -t "$MUD_SESSION" Enter

if ! mud_wait_for_text "Password:" 10; then
  echo "Timed out waiting for the password prompt. Current screen:" >&2
  tmux capture-pane -t "$MUD_SESSION" -p >&2
  exit 1
fi
tmux send-keys -t "$MUD_SESSION" -l -- "$MUD_PASS"
tmux send-keys -t "$MUD_SESSION" Enter

if ! mud_wait_for_text "PRESS RETURN" 10; then
  echo "Timed out waiting for the MOTD screen. Current screen:" >&2
  tmux capture-pane -t "$MUD_SESSION" -p >&2
  exit 1
fi
tmux send-keys -t "$MUD_SESSION" Enter

if ! mud_wait_for_text "Make your choice" 10; then
  echo "Timed out waiting for the main menu. Current screen:" >&2
  tmux capture-pane -t "$MUD_SESSION" -p >&2
  exit 1
fi
PRE_TOTAL=$(mud_total_lines)
tmux send-keys -t "$MUD_SESSION" -l -- "1"
tmux send-keys -t "$MUD_SESSION" Enter

mud_wait_for_new_prompt "$PRE_TOTAL" 10 || true

echo "Connected to $MUD_HOST:$MUD_PORT and logged in as $MUD_USER."
echo "----"
"$DIR/mud_read.sh"
