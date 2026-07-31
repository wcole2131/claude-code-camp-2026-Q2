# TUI ⟵ MCP delta plan

`week1_baseline/ruby/11_tui` was branched from `10_standard_tool_library`
*before* commit `2efa120` ("major refactor bringing mcp"). That commit moved
every built-in tool (filesystem, shell, MUD) out of the `boukensha` gem and
into three standalone MCP servers (`file_system_mcp`, `shell_mcp`,
`mud_manager_mcp`), replacing `Tools::FileSystem`/`Tools::Shell`/`Tools::Mud`
with a generic `Boukensha::MCP` client/server pair. `11_tui` still has the
pre-refactor tool-registration code, so it's missing that MCP layer entirely.
Meanwhile, `11_tui` independently gained TUI-specific things `10` never had:
`Boukensha::Tui`, the `tui:`/`--no-tui` toggle, and a `Repl` refactored around
`on_output`/`handle_command`/`run_turn` so a front end other than raw
stdin/stdout can drive it.

Goal: bring the MCP delta into `11_tui` without losing any of the TUI work.
This is a merge of two independent deltas onto the same pre-refactor base,
not a straight copy of `10`'s files.

## Baseline delta (10_standard_tool_library, commit 2efa120)

- Added `lib/boukensha/mcp.rb` — generic stdio JSON-RPC MCP client
  (`Boukensha::MCP`), with `.file_system_server`/`.shell_server`/
  `.mud_manager_server` convenience factories for this repo's three bundled
  servers (resolved via `WEEK1_BASELINE_DIR`, 4 levels up from
  `lib/boukensha/mcp.rb` — works unchanged from any `week1_baseline/ruby/NN_*`
  step).
- Added `lib/boukensha/mcp/server.rb` — the mirrored generic server side
  (`Boukensha::MCP::Server`), used by the three server gems themselves (not
  by `boukensha` at runtime, but kept in the framework so servers share one
  implementation).
- Removed `lib/boukensha/tools/{file_system,mud,shell}.rb` — no built-in
  tools ship with the framework anymore.
- `lib/boukensha.rb`: `run`/`repl` gained `mcp_servers:` (replacing
  `mud:`), built via `default_mcp_servers` (file_system_mcp + shell_mcp from
  `working_dir:`, plus mud_manager_mcp if `settings.yaml` has `mud_host`) and
  connected via `connect_mcp_servers`; clients are closed in `ensure`.
- `lib/boukensha/registry.rb`: gained `attr_reader :context` and a `tools`
  delegate, so `MCP::Server` can enumerate registered tools generically.
- `lib/boukensha/backends/anthropic.rb`: extracted `input_schema_for`,
  mirroring `MCP::Server#input_schema_for` (JSON Schema shape shared by both
  directions).
- `lib/boukensha/repl.rb`: dropped the MUD-specific banner/probe
  (`mud_status_string`/`probe_mud`) in favor of a generic
  `tools: N registered (via MCP — see mcp_servers:)` line, and dropped the
  `mud:` constructor param entirely.
- `lib/boukensha_loader.rb`: the legacy `MUD_NAME` env-var override now
  builds `repl_opts[:mcp_servers] = [Boukensha::MCP.mud_manager_server(...)]`
  instead of `repl_opts[:mud]`.
- `Gemfile`/`Gemfile.lock`/`boukensha.gemspec`: dropped the `mud_manager`
  dependency — it now belongs to `mud_manager_mcp` only.
- `examples/example.rb`, `README.md`: updated to describe the MCP wiring.

## TUI-only work already in 11_tui (must survive the merge untouched)

- `lib/boukensha/tui.rb` (`Boukensha::Tui`) — drives `Repl` via
  `on_output`, `handle_command`, `run_turn`, and reads `repl.context`,
  `repl.logger`, `repl.model`, `repl.version`. None of this touches tools or
  MCP directly; it only needs `Context#tool_count` (unchanged) for the status
  bar.
- `lib/boukensha.rb`: `tui:` keyword on `repl`, `Tui.new(repl).start` vs
  `repl.start` fallback.
- `lib/boukensha_loader.rb`: `--no-tui` CLI flag → `repl_opts[:tui]`.
- `lib/boukensha/repl.rb`: `on_output`/`handle_command`/`run_turn` split,
  `attr_reader :logger, :context, :model, :version`.
- `charm` gem dependency (gemspec/Gemfile) and `patches/bubbletea/`.

`Logger#subscribe`, `Context`, `Tool`, `Agent`, `Client`, `Config` are
identical between `10` and `11` already — no merge needed there.

## Steps

1. **`registry.rb`** — add `attr_reader :context` and `def tools = @context.tools`
   (verbatim from `10`).
2. **`backends/anthropic.rb`** — add `input_schema_for` and use it in place
   of the inline `input_schema:` hash (verbatim from `10`).
3. **`mcp.rb` + `mcp/server.rb`** — copy both files from `10` unchanged; they
   have no TUI-related content and `WEEK1_BASELINE_DIR`'s path math is
   identical at this directory depth.
4. **`repl.rb`** — apply only the MUD→tools banner swap and drop the `mud:`
   param/`@mud` ivar/`mud_status_string`/`probe_mud`, keeping every TUI
   addition (`on_output`, `handle_command`, `attr_reader`s, the `start`/
   `run_turn` split) exactly as `11` already has it.
5. **`boukensha.rb`** — in both `run` and `repl`: swap the
   `Tools::FileSystem/Shell/Mud.register` block and `mud`/`resolved_mud`
   handling for `mcp_servers:`/`default_mcp_servers`/`connect_mcp_servers`
   (verbatim logic from `10`), add `mcp_clients&.each(&:close)` to `ensure`,
   and update the doc comment. Keep the `tui:` keyword,
   `Tui.new(repl).start` branch, and the `Repl.new(...)` call as `11` already
   has them (minus the now-gone `mud: resolved_mud` arg). Update
   `require_relative` list: drop `tools/file_system`, `tools/shell`,
   `tools/mud`; add `boukensha/mcp` and `boukensha/mcp/server`; keep
   `boukensha/tui` last.
6. **`boukensha_loader.rb`** — swap the `MUD_NAME` branch to build
   `repl_opts[:mcp_servers]` via `Boukensha::MCP.mud_manager_server(...)`
   instead of `repl_opts[:mud]`, matching `10`. Keep the `--no-tui` →
   `repl_opts[:tui]` line as-is.
7. **Remove `lib/boukensha/tools/`** (`file_system.rb`, `mud.rb`,
   `shell.rb`) — superseded by the standalone MCP server gems under
   `week1_baseline/`.
8. **Gemfile / gemspec / Gemfile.lock** — remove the `mud_manager`
   dependency from `boukensha.gemspec` (keep `charm`), then regenerate
   `Gemfile.lock` with `bundle install --local` so `mud_manager` drops out of
   the resolved graph.
9. **`examples/example.rb`** — bring in line with `10`'s MCP-aware demo
   comment/wiring (still `working_dir: false`, mud connection resolved from
   config via `default_mcp_servers`).
10. **`README.md`** — keep all existing TUI sections (`Boukensha::Tui`,
    `tui:` keyword, `Repl` composability, `Logger#subscribe`), and fold in
    `10`'s MCP sections (bundled servers table, `mcp_servers:` usage,
    `Boukensha::MCP` client) as an "inherited from step 10" section above
    them. Fix the stale claim that `examples/example.rb` is "carried over
    unchanged" — it now reflects the MCP-based demo like `10`'s does.

## Verification

- `ruby -c` every changed file.
- `bundle install --local` (or plain `bundle install`, all gems are already
  installed locally: `charm`, `bubbletea`, `dotenv`; `mud_manager` should
  disappear from the lock) inside `week1_baseline/ruby/11_tui`.
- Confirm `week1_baseline/{file_system_mcp,shell_mcp,mud_manager_mcp}` are
  still reachable from `11_tui` via `Boukensha::MCP::WEEK1_BASELINE_DIR` (same
  4-levels-up math as `10`, since `11_tui` sits at the same
  `week1_baseline/ruby/<step>/` depth).
- No functional/UI testing of the TUI itself (requires a live terminal +
  API key); this plan only restores structural parity with `10`'s tool
  wiring.
