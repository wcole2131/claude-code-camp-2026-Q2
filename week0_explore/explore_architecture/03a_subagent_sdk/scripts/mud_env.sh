# Shared configuration and helpers for the mud-player scripts.
# Source this from other scripts: source "$DIR/mud_env.sh"

MUD_HOST="${MUD_HOST:-localhost}"
MUD_PORT="${MUD_PORT:-4000}"
MUD_USER="${MUD_USER:-dummy}"
MUD_PASS="${MUD_PASS:-helloworld}"
MUD_WAIT="${MUD_WAIT:-0.8}"

# Namespaced by MUD_USER so two different characters (e.g. two subagents each
# exporting a different MUD_USER) get an independent tmux session, read-offset
# state, and memory directory automatically, and don't collide or overwrite
# each other's data. Each can still be overridden individually if a caller
# needs a different layout.
MUD_SESSION="${MUD_SESSION:-tbamud-$MUD_USER}"
MUD_STATE_DIR="${MUD_STATE_DIR:-$DIR/.state/$MUD_USER}"

# Project root is always 1 level above scripts/ for this subagent layout
# (scripts -> project root).
MUD_PROJECT_ROOT="${MUD_PROJECT_ROOT:-$(cd "$DIR/.." && pwd)}"
MUD_DATA_DIR="${MUD_DATA_DIR:-$MUD_PROJECT_ROOT/data/$MUD_USER}"

# Total lines currently in the pane (visible + scrollback).
mud_total_lines() {
  tmux capture-pane -t "$MUD_SESSION" -p -S -5000 | wc -l
}

# Polls until $1 (an extended regex) appears anywhere in the last ~300 lines
# of the pane, or $2 seconds pass. The server's client-detection negotiation
# has variable timing, so login steps must wait for the actual prompt text
# rather than a fixed sleep -- a fixed sleep that's too short sends input
# before the prompt exists and desyncs the rest of the login sequence.
mud_wait_for_text() {
  local pattern="$1"
  local timeout="${2:-10}"
  local elapsed=0
  while (( elapsed < timeout * 10 )); do
    if tmux capture-pane -t "$MUD_SESSION" -p -S -300 | grep -Eq -- "$pattern"; then
      return 0
    fi
    sleep 0.2
    elapsed=$((elapsed + 2))
  done
  return 1
}

# Polls until new output beyond $1 (a previously captured total line count)
# contains the in-game status prompt (e.g. "23H 100M 84V (news) (motd) >"),
# or $2 seconds pass. Used after sending an in-game command to know the MUD
# has finished responding instead of guessing a fixed delay.
mud_wait_for_new_prompt() {
  local pre_total="$1"
  local timeout="${2:-10}"
  local elapsed=0
  while (( elapsed < timeout * 10 )); do
    local full total new_part
    full="$(tmux capture-pane -t "$MUD_SESSION" -p -S -5000)"
    total=$(printf '%s\n' "$full" | wc -l)
    if (( total > pre_total )); then
      new_part="$(printf '%s\n' "$full" | tail -n "+$((pre_total + 1))")"
      if printf '%s\n' "$new_part" | grep -Eq '[0-9]+H [0-9]+M [0-9]+V'; then
        sleep 0.3 # grace period to catch any trailing lines from the same batch
        return 0
      fi
    fi
    sleep 0.2
    elapsed=$((elapsed + 2))
  done
  return 1
}
