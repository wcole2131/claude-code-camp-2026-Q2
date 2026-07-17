#!/usr/bin/env bash
# Seeds data/player.md and data/world.md from the skill's templates if they
# don't exist yet or are empty, so every play session (even a brand new
# conversation with no memory of prior ones) has a consistent structure to
# read and build on rather than starting from a blank page. Safe to call at
# the start of every session -- it never overwrites a file that already has
# content.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/mud_env.sh"

mkdir -p "$MUD_DATA_DIR"

if [ ! -s "$MUD_DATA_DIR/player.md" ]; then
  cp "$DIR/../assets/player_template.md" "$MUD_DATA_DIR/player.md"
  echo "Initialized $MUD_DATA_DIR/player.md from template."
else
  echo "$MUD_DATA_DIR/player.md already has content -- left untouched."
fi

if [ ! -s "$MUD_DATA_DIR/world.md" ]; then
  cp "$DIR/../assets/world_template.md" "$MUD_DATA_DIR/world.md"
  echo "Initialized $MUD_DATA_DIR/world.md from template."
else
  echo "$MUD_DATA_DIR/world.md already has content -- left untouched."
fi
