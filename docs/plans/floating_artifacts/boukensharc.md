# Floating artifact: `~/.boukensharc` / global executable loader

See `docs/plans/floating_artifacts/README.md` for what "floating artifact" means and why this
doc exists outside the normal per-step plan docs.

## What it is

Three files that together package the Ruby side as an installable gem so a global `boukensha`
command works from any directory, and let that command pick which step's code to actually run:

- `boukensha.gemspec` — declares the gem (name, version, files, the `bin/boukensha` executable)
- `bin/boukensha` — the shebang script installed on `$PATH`
- `lib/boukensha_loader.rb` — resolves *which step's* `lib/boukensha.rb` to load, then boots the
  REPL

Introduced whole in `week1_baseline/ruby/09_global_executable` (commit `7f7bf9b`, "added global
executable for ruby"). From there it is copied forward into every later numbered step directory
(`10_standard_tool_library`, and whatever `11_*` etc. come next) as part of that step's own gem
release — the gem version bumps, the "bundled default" comment/example paths get updated to name
the current step, but the files are not that step's headline content.

## Where the chain stops

`docs/plans/python_port/` goes 00 → 08 → 10 with no 09: there is no
`week1_baseline/python/09_global_executable`, no `docs/plans/python_port/09*.md`, no
`week1_baseline/bin/python/09_global_executable`. Packaging a Ruby project as an installable gem
with a Bundler-resolved global executable is a Ruby-specific concern with no Python analogue in
this port's scope, so it was skipped rather than ported — the copy-forward-then-delta chain that
carries every other file across steps and languages simply never runs through this one.

Two practical consequences follow from that:

- **Diff noise for future porting.** The `python-port` skill (see
  `.claude/skills/python-port/SKILL.md`) finds the next step to port by diffing adjacent Ruby step
  directories. Diffing `ruby/08_the_repl_loop` against `ruby/10_standard_tool_library` (since 09
  doesn't exist on the Python side) will show the *entire* gemspec/bin/loader machinery as part of
  "the delta," even though none of it should be ported — only the actual step-10 content (standard
  tool library / MCP migration) should. Read this doc instead of re-deriving that exclusion from
  scratch.
- **Its *behavior* still tracks real API changes worth checking.** `boukensha_loader.rb` calls
  `Boukensha.repl(**repl_opts)`. Whatever `repl_opts` it builds has to match `Boukensha.repl`'s
  actual keyword-argument surface at that step — and that surface *does* have a Python equivalent
  (`boukensha/__init__.py`'s `repl`/`run` functions). So when this file's `load_and_start_repl`
  changes, check whether the underlying `Boukensha.repl` change it's reacting to is itself part of
  the current step's Python delta — usually yes, even though the loader file wrapping it is not.

## Current shape (as of `ruby/10_standard_tool_library`, in-progress MCP migration)

Resolution order for which step's `lib/boukensha.rb` to load:

1. `BOUKENSHA_PATH` env var (points at a step folder)
2. `~/.boukensharc` (a file containing a single step-folder path)
3. bundled default — the `lib/` shipped inside whichever step built the currently-installed gem

Separate axis, not step-related: `BOUKENSHA_DIR` (default `~/.boukensha`) controls the *config*
directory (`settings.yaml`, `.env`, `system.md`), independent of which step's code is running.

After resolving and requiring the step's `lib/boukensha.rb`, `load_and_start_repl` builds
`repl_opts` before calling `Boukensha.repl(**repl_opts)`. This is the part that keeps changing:

- If the legacy `MUD_NAME` env var is set, it builds an explicit MUD connection override and
  passes it through `repl_opts`.
- Otherwise it passes no override, and `Boukensha.repl` builds its own defaults from
  `settings.yaml`.

## Change history

**Step 9 (`09_global_executable`, commit `7f7bf9b`):** `load_and_start_repl` just calls
`Boukensha.repl` with no arguments — no `MUD_NAME` handling exists yet because step 9 predates the
MUD tool entirely.

**Step 10, first commit (`3a2bb4b`, "added standard tools with ruby"):** step 10 introduced a
built-in `Tools::Mud`, so the loader gained `MUD_NAME` handling to match:

```ruby
if ENV["MUD_NAME"]
  repl_opts[:working_dir] = false
  repl_opts[:mud] = {
    host: ENV.fetch("MUD_HOST", "localhost"), port: ENV.fetch("MUD_PORT", "4000").to_i,
    name: ENV.fetch("MUD_NAME"), password: ENV.fetch("MUD_PASSWORD") { abort "..." }
  }
end
Boukensha.repl(**repl_opts)
```

`repl_opts[:mud]` and `working_dir: false` matched `Boukensha.repl`'s keyword surface at that
commit, where the framework itself owned a small set of built-in tools (file system, shell, mud)
and `working_dir:` toggled whether the in-process file-system/shell tools were attached.

**Step 10, current working tree (uncommitted as of 2026-07-31):** the framework's built-in tools
were removed entirely. All tools — file system, shell, mud — are now separate MCP servers
(`week1_baseline/file_system_mcp/`, `shell_mcp/`, `mud_manager_mcp/`) that `Boukensha::MCP`
(`lib/boukensha/mcp.rb`, new this step) connects to over stdio and registers generically (see
`docs/plans/mud_manager/mcp_mud_plan.md` for the design rationale). `Boukensha.repl` no longer
accepts `mud:` or a tool-suppressing `working_dir: false`; instead it takes `mcp_servers:` — an
explicit list of server specs, defaulting (when omitted) to `default_mcp_servers`, built from
`working_dir:`/`allowed_commands:`/`shell_timeout:` plus `settings.yaml`'s `mud:` block. The loader
was updated to match:

```ruby
if ENV["MUD_NAME"]
  # connect to mud_manager_mcp only, skipping the default file_system_mcp/shell_mcp servers
  repl_opts[:mcp_servers] = [
    Boukensha::MCP.mud_manager_server(
      host: ENV.fetch("MUD_HOST", "localhost"), port: ENV.fetch("MUD_PORT", "4000").to_i,
      name: ENV.fetch("MUD_NAME"), password: ENV.fetch("MUD_PASSWORD") { abort "..." }
    )
  ]
end
# If MUD_NAME is not set, Boukensha.repl builds its default mcp_servers: list from
# config.mud_* values automatically (see Boukensha.default_mcp_servers).
Boukensha.repl(**repl_opts)
```

Net effect: `MUD_NAME` set now means "connect to *only* `mud_manager_mcp`, nothing else" (there's
no more separate `working_dir: false` flag, because there's no more in-process file-system/shell
tool to suppress — omitting them from the `mcp_servers:` list *is* suppressing them).

## Guidance for future AI work

**Continuing the Ruby side (step 11 and beyond):** when copying a step forward,
`boukensha_loader.rb` / `bin/boukensha` / `*.gemspec` travel with it (version bump, updated
"bundled default" comment). Treat any *behavioral* edit inside `load_and_start_repl` as tied to
whatever that step changed in `Boukensha.run`/`Boukensha.repl`'s keyword-argument surface — not as
that step's own new content — and append a new entry to "Change history" above rather than editing
the existing entries away.

**Using the `python-port` skill:** when diffing Ruby steps to find "the next delta" and the diff
spans the 09 gap (e.g. `python/08` → `python/10`), exclude `boukensha_loader.rb`, `bin/boukensha`,
and `*.gemspec` from what you treat as step content — that's this artifact, not the step. Do still
check whether `Boukensha.repl`'s Python equivalent needs the same keyword-argument change the Ruby
loader is reacting to (e.g. an `mcp_servers`-shaped parameter) — that part is real port content and
belongs in the step's plan doc and delta table, sourced from `Boukensha.repl` itself, not from this
file.

**If a future step adds a Python-side global-executable equivalent** (e.g. a `pipx`/console-script
entry point), don't assume the Ruby resolution order ports 1:1 — start a "Python equivalent"
section in this doc rather than silently inventing one, since Python has no Bundler-gem analogue
and the env-var/rc-file/bundled-default precedence would need its own decision.

## Related docs

- `docs/plans/mud_manager/mcp_mud_plan.md`, `mcp_generalization_plan.md`, `generic_interfacing.md`,
  `mcp_integration_verification.md` — the MCP migration this artifact's latest change reflects.
- `week1_baseline/ruby/09_global_executable/README.md` — original step README; still accurate for
  the packaging mechanism itself, but its `BOUKENSHA_PATH=... boukensha` / `repl_opts[:mud]`-era
  examples predate the MCP migration above.
