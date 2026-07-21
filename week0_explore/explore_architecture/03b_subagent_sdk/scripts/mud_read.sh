#!/usr/bin/env bash
# Passively reads whatever new output has arrived in the MUD session since the
# last read/send, without sending anything. Useful for checking on combat
# spam, tells, or other unprompted output between commands. Sends nothing to
# the MUD, so it is always safe to call.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/mud_env.sh"

if ! tmux has-session -t "$MUD_SESSION" 2>/dev/null; then
  echo "No active MUD session. Run mud_start.sh first." >&2
  exit 1
fi

mkdir -p "$MUD_STATE_DIR"
OFFSET_FILE="$MUD_STATE_DIR/offset"
LAST=$(cat "$OFFSET_FILE" 2>/dev/null || echo 0)

FULL="$(tmux capture-pane -t "$MUD_SESSION" -p -S -5000)"
TOTAL=$(printf '%s\n' "$FULL" | wc -l)

if [ "$TOTAL" -gt "$LAST" ]; then
  printf '%s\n' "$FULL" | tail -n "+$((LAST + 1))"
else
  echo "(no new output)"
fi

echo "$TOTAL" > "$OFFSET_FILE"
