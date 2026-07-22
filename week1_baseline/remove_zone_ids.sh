#!/usr/bin/env bash
set -euo pipefail

# Remove Windows/WSL Zone.Identifier files from this project directory.
# Wraps the shared ../bin/remove_zone_ids script, scoped to this folder.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$script_dir/../bin/remove_zone_ids" "$script_dir"
