# Context ⟵ TUI/MCP delta plan

`week1_baseline/ruby/12_context` is **untracked** (never committed — see
`git status`). It was branched independently, before commit `2efa120`
("major refactor bringing mcp") *and* before whatever pass introduced the
`Tasks::Player` task-abstraction that `10_standard_tool_library`/`11_tui`
still carry. So `12_context` still has the pre-MCP
`Tools::FileSystem`/`Tools::Shell`/`Tools::Mud` tool classes, still has no
`Boukensha::MCP`, and its `Config`/`Boukensha.run`/`Boukensha.repl` never
routed through `Tasks::Player` (`system_prompt`/`model`/`provider`/
`max_iterations`/`max_output_tokens` are plain `Config` accessors instead of
`task_settings` lookups).

Meanwhile `11_tui` already has **both** deltas merged in (per
`docs/plans/tui_mcp_delta/tui_plan.md`, already executed): the MCP client/
server (`Boukensha::MCP`, `Boukensha::MCP::Server`), no built-in tool
classes, and the full TUI (`Boukensha::Tui`, `tui:`/`--no-tui`, `Repl`'s
`on_output`/`handle_command`/`run_turn` split). `11_tui` is the current
reference state for "how tools and the front end work" and should be
treated as authoritative for that surface.

`12_context` independently did a lot of real, wanted work on top of its
older base that `11_tui` has none of and must not be lost:

- **Context/token tracking + auto-compaction** — `Context#current_tokens`/
  `#turn_tokens`/`#context_window`/`#compaction_threshold`,
  `#compact_messages!`, `#needs_compaction?`, `#usage_fraction`/`#usage_pct`;
  `Agent` compacts at the top of a turn and tracks a per-turn spend budget
  (`max_turn_tokens`) independent of `max_iterations`; `Repl`'s `/compact`
  command; `Tui`'s context colour coding (grey/yellow/red at 70%/85%) and
  `⚠` indicator.
- **`Boukensha::Models`** (`lib/boukensha/models.rb`) — static
  model→`context_window` lookup table, used to default `context_window:`
  from the configured model id.
- **Reasoning/thinking normalization** — every backend
  (`anthropic.rb`, `openai.rb`, `gemini.rb`, `ollama.rb`, `ollama_cloud.rb`,
  documented in `base.rb`) now emits/consumes a common `"reasoning"` content
  block (`text`/`signature`/`redacted`) alongside `"text"`/`"tool_use"`, and
  `Agent`/`Logger` gained `log_reasoning`/`Logger#reasoning` and a `plan`
  event to log tool-call preambles separately from the response event.
  `openai.rb` also moved from the Chat Completions shape to the Responses
  API shape as part of this.
- **`Config` simplification** — no `Tasks::Player`/`tasks(name)`, no
  `PROMPTS_DIR`/`user_prompts_dir`; `provider_type`/`model`/`system_prompt`
  (loaded straight from `~/.boukensha/prompts/system.md`, with an optional
  per-task override path) are plain accessors, and `agent_max_iterations`/
  `agent_max_output_tokens`/`agent_max_turn_tokens`/
  `agent_compaction_threshold` replace the old task-settings-driven
  resolution in `Agent`.
- Assorted `MODELS` table edits across backends (added/removed model ids,
  pricing/context-window tweaks) — pure data tuning, unrelated to either
  delta, leave untouched.

Goal: bring `11_tui`'s current MCP + TUI-plumbing state into `12_context`
without losing any of the above. This is a three-way merge onto a shared but
older common ancestor, not a straight copy of `11_tui`'s files — most files
in `12_context` already contain real, independent changes that must survive
verbatim in the merged result.

## What's untouched between the two (safe reference points)

`errors.rb` and `prompt_builder.rb` differ only in cosmetic ways (a
whitespace realignment, a doc comment, a missing trailing newline) — no
merge needed, just verify parity while touching neighboring files.

## Steps

1. **`lib/boukensha/mcp.rb` + `lib/boukensha/mcp/server.rb`** — copy both
   files from `11_tui` unchanged (new files in `12_context`; no
   context-management content to preserve there). `WEEK1_BASELINE_DIR`'s
   4-levels-up path math is identical at this directory depth.

2. **`lib/boukensha/registry.rb`** — add back `attr_reader :context` and
   `def tools = @context.tools` (verbatim from `11_tui`). Nothing here
   conflicts with `12_context`'s own work — `registry.rb` is otherwise
   identical between the two.

3. **`lib/boukensha/backends/anthropic.rb`** — extract the inline
   `input_schema:` hash in `to_tools` into an `input_schema_for(parameters)`
   method (verbatim logic from `11_tui`: builds `properties`/`required` from
   the `{name: {type:, description:, required:}}` shape, `required:`
   defaulting to `true`), and call it from `to_tools`. Keep every
   `12_context`-only addition as-is: the `MODELS` table, `normalize_block`/
   `assistant_content`/`denormalize_block` reasoning-block round-tripping,
   the `# https://platform.claude.com/...` header comment.

4. **`lib/boukensha/repl.rb`** — remove the MUD-specific banner/probe
   (`mud_status_string`, `probe_mud`) and the `mud:` constructor
   param/`@mud` ivar, replacing the banner's `mud: #{mud_stat}` line with
   `11_tui`'s generic `tools: #{@context.tool_count} registered (via MCP —
   see mcp_servers:)` line. Keep every other `12_context` addition exactly
   as it stands: the `/compact` command and its `HELP`/banner entries,
   `max_turn_tokens` threaded through `initialize` and `run_turn`'s
   `Agent.new(...)` call, and the existing `on_output`/`handle_command`/
   `run_turn` split (already present in `12_context`, already matches
   `11_tui` structurally).

5. **`lib/boukensha.rb`** — this is the main merge:
   - In both `run` and `repl`: replace the `if working_dir ... Tools::FileSystem.register / Tools::Shell.register end`
     + `resolved_mud = ... ; Tools::Mud.register(registry, **resolved_mud) if resolved_mud`
     block with `11_tui`'s `mcp_servers:` param, `default_mcp_servers(cfg, working_dir:, allowed_commands:, shell_timeout:)`,
     and `connect_mcp_servers(registry, resolved_servers)`, and add
     `mcp_clients&.each(&:close)` to each method's `ensure`. Drop the
     `mud:` keyword param entirely (replaced by the generic `mcp_servers:`
     mechanism — `default_mcp_servers` already folds `cfg.mud_host`/
     `cfg.mud_username` into a `mud_manager_mcp` spec via
     `MCP.mud_manager_server`, matching what `mud_opts_from_config` did).
   - Keep every `12_context`-only addition: `context_window:` param,
     `context_window ||= Models.context_window(model)`, passing
     `context_window:`/`compaction_threshold: cfg.agent_compaction_threshold`
     into `Context.new`, `cfg.agent_max_iterations`/`agent_max_turn_tokens`/
     `agent_max_output_tokens` into the `Logger`/`Agent` construction, and
     `system ||= cfg.system_prompt` / `model ||= cfg.model` / `backend ||=
     cfg.provider_type.to_sym` (i.e. do **not** reintroduce `task_class`/
     `task_settings`/`Tasks::Player` — `12_context` deliberately doesn't use
     them and `11_tui` still does only because it predates that removal).
   - In `repl`'s `Repl.new(...)` call: drop the `mud: resolved_mud` arg
     (no longer resolved), keep `max_iterations:`/`max_turn_tokens:`/
     `max_output_tokens:` as `12_context` already has them.
   - `require_relative` list at the bottom: drop `boukensha/tools/
     file_system`, `boukensha/tools/shell`, `boukensha/tools/mud`; add
     `boukensha/mcp` and `boukensha/mcp/server` (placed the same as in
     `11_tui`, before `boukensha/message`); keep `boukensha/models` and
     `boukensha/tui` exactly where `12_context` already has them. Also drop
     the now-stale `require_relative "boukensha/tasks/player"` line at the
     top if `12_context` still has it (check — it may already be gone since
     `Tasks::Player` isn't used) and the `lib/boukensha/tasks/` dir if
     present in `12_context` (verify with `find 12_context/lib/boukensha/tasks`
     — it wasn't found during investigation, so this is likely a no-op).
   - Update the doc comment above `run` to describe `mcp_servers:` (from
     `11_tui`) instead of `working_dir:`/`allowed_commands:`/
     `shell_timeout:`/`mud:` as tool-registration knobs, while keeping the
     `context_window:` doc line `12_context` already added.

6. **`lib/boukensha_loader.rb`** — swap the `MUD_NAME` branch to build
   `repl_opts[:mcp_servers] = [Boukensha::MCP.mud_manager_server(...)]` (and
   `repl_opts[:working_dir] = false`, matching `11_tui`'s comment structure)
   instead of `repl_opts[:mud] = {...}`. Keep the `--no-tui` → `repl_opts[:tui]`
   line as-is.

7. **Remove `lib/boukensha/tools/`** (`file_system.rb`, `mud.rb`,
   `shell.rb`) from `12_context` — superseded by the standalone MCP server
   gems under `week1_baseline/`.

8. **`boukensha.gemspec` / `Gemfile.lock`** — remove the `mud_manager`
   dependency (keep `charm`), matching `11_tui`'s gemspec (including its
   comment pointing at `docs/plans/mud_manager/mcp_mud_plan.md`). Regenerate
   `Gemfile.lock` with `bundle install --local` inside `12_context` so
   `mud_manager` drops out of the resolved graph and `boukensha (0.12.0)`'s
   own spec entry stops listing it.

9. **`examples/example.rb`** — bring the doc comment and demo call in line
   with `11_tui`'s MCP-aware version (`mcp_servers: defaults to
   [mud_manager_server(...)]` comment instead of `Tools::Mud`/`mud:` comment),
   keeping `working_dir: false`.

10. **`README.md`** — `12_context`'s README currently only documents the
    context-management feature set (it dropped the step-11 TUI section and
    never had the step-10 MCP section). Restructure it to layer three
    things:
    - An "inherited from step 10" MCP tool-library section (bundled
      servers table, `mcp_servers:` usage, `Boukensha::MCP` client) —
      fold in from `11_tui`'s README.
    - An "inherited from step 11" TUI section (`Boukensha::Tui`, `tui:`
      keyword, `Repl` composability) — fold in from `11_tui`'s README.
    - The existing step-12 "What's new" content (context tracking, colour
      coding, auto-compaction, `/compact`, `Logger#compaction`,
      `context_window:` keyword) — keep as-is, but note the TUI section
      needs its status-bar/progress-line description updated to mention
      context colour coding (`12_context`'s `Tui` already does this; the
      README should say so).
    Also mention the reasoning/thinking normalization work
    (`"reasoning"` content blocks, provider-specific thinking support) if
    `12_context`'s current README doesn't already cover it — check first,
    since this plan doesn't require adding brand-new documentation for
    pre-existing `12_context` features, only reconciling the TUI/MCP gap.

## Explicitly out of scope (leave as-is in `12_context`)

- `Context`, `Agent`, `Logger`, `Tui`, `Models`, `Config`'s
  system-prompt/agent-limit accessors, and every backend's reasoning-block
  handling — all `12_context`-only work, unrelated to the TUI/MCP delta.
- `MODELS` table content differences across backends (model ids added/
  removed, pricing/context-window numbers) — orthogonal tuning, not part of
  either delta.
- The absence of a shipped default `prompts/system.md` in `12_context`
  (`11_tui` still ships one under its old `Tasks::Player`-driven
  `PROMPTS_DIR` mechanism, which `12_context` deliberately replaced with a
  `~/.boukensha/prompts/system.md`-only lookup). This is part of the
  `Tasks::Player` removal, not the TUI/MCP delta — do not reintroduce
  `PROMPTS_DIR`. Flag to the user as a possible follow-up (no shipped
  default system prompt means `cfg.system_prompt` can be `nil` out of the
  box) rather than fixing it as part of this plan.
- `.ruby-version` (present in `11_tui`, absent in `12_context`) and
  `vendor/` (bundled gem cache, present in `11_tui` only) — regenerable by
  `bundle install`; add `.ruby-version` only if the user wants strict
  parity, not required for functional correctness.

## Verification

- `ruby -c` every changed file.
- `bundle install --local` (or plain `bundle install`) inside
  `week1_baseline/ruby/12_context`; confirm `mud_manager` is gone from
  `Gemfile.lock` and `charm`/`bubbletea`/`dotenv` still resolve.
- Confirm `week1_baseline/{file_system_mcp,shell_mcp,mud_manager_mcp}` are
  reachable from `12_context` via `Boukensha::MCP::WEEK1_BASELINE_DIR` (same
  4-levels-up math as `11_tui`, since `12_context` sits at the same
  `week1_baseline/ruby/<step>/` depth).
- Grep for lingering `Tools::FileSystem`/`Tools::Shell`/`Tools::Mud`/
  `task_settings`/`Tasks::Player`/`mud:` references after the merge — none
  should remain outside this plan's explicit "out of scope" list.
- No functional/UI testing of the TUI itself (requires a live terminal +
  API key); this plan only restores structural parity with `11_tui`'s tool
  wiring while preserving `12_context`'s context-management and
  reasoning-normalization work.
