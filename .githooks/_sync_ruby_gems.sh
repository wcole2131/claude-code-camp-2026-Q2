#!/usr/bin/env bash
# Shared logic for .githooks/post-merge and .githooks/post-checkout.
#
# Keeps every week1_baseline/ruby/<step>/vendor/bundle in sync whenever new
# course content lands via `git pull`/`git merge`/`git checkout`, so
# `week1_baseline/bin/ruby/<step>` never needs a manual `bundle install`
# first. This just calls week1_baseline/bin/setup_ruby_step with no
# arguments, which fixes every ruby/* step (repins Gemfile.lock's
# "BUNDLED WITH" to the Bundler installed on this machine, then runs
# `bundle install`) — see that script for why the repin is needed.
set -uo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
setup="$repo_root/week1_baseline/bin/setup_ruby_step"
[ -x "$setup" ] || exit 0

log="$("$setup" 2>&1)"
status=$?

if [ "$status" -ne 0 ]; then
  echo "warning: week1_baseline/bin/setup_ruby_step failed:" >&2
  echo "$log" >&2
else
  echo "✓ week1_baseline ruby step gems are in sync (bin/setup_ruby_step)"
fi
