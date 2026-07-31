Status: implemented. Both stages below are built, tested, and (as of the 2026-07-31 audit
described in "Audit findings and fixes") verified against `ruby/10_standard_tool_library`'s current
source. This doc is a historical record of what was built and why, not a pending proposal.

## Goal

Turn `week1_baseline/python/10_standard_tool_library/` into a faithful port of
`week1_baseline/ruby/10_standard_tool_library/`, keeping the two in sync as Ruby's own step kept
changing. Unlike every other step in this port, `10_standard_tool_library` was not a single
copy-forward-then-delta pass — Ruby's step itself was rewritten out from under this plan partway
through, so the Python side was built in two stages against two different Ruby designs. Both stages
are captured below because the code, tests, and README all reflect the second (MCP) design, not the
first — a reader diffing against an old checkout should understand why the shape changed rather than
assume a bug.

## Stage 1 (superseded): direct in-process tool modules

**No longer describes the code.** Implemented in commit `717b716` ("added standard tool library
port to python"), this stage ported Ruby's *then-current* design: two hand-written tool-registration
modules, `Boukensha::Tools::FileSystem` and `Boukensha::Tools::Shell`, registered directly against
the agent's `Registry` in-process, wired into `Boukensha.run`/`Boukensha.repl` via `working_dir:`/
`allowed_commands:`/`shell_timeout:` keyword arguments. A third Ruby tool module, `Tools::Mud`
(~480 lines, 25 tools wrapping the `mud_manager` gem), existed in Ruby at the time but was
deliberately **descoped** from this port — no Python `mud_manager` equivalent existed, and porting
a raw-socket CircleMUD client felt like its own future step rather than something to fold into "a
standard tool library."

This stage produced `boukensha/tools/__init__.py`, `boukensha/tools/file_system.py`, and
`boukensha/tools/shell.py`. **All three files are gone as of Stage 2** — deleted, not just
unreferenced. If you're looking for direct-registration filesystem/shell tools in either language,
they don't exist anymore in this step; see Stage 2.

## Stage 2 (current): everything arrives over MCP

Implemented in commit `2efa120` ("major refactor bringing mcp", 2026-07-31), which rewrote
`ruby/10_standard_tool_library` and `python/10_standard_tool_library` **simultaneously** — same
commit, both languages — replacing Stage 1's in-process tool modules with a generic MCP (Model
Context Protocol) client, and moving all tool implementations (filesystem, shell, *and* the
previously-descoped MUD tools) out of `boukensha` entirely into three standalone MCP server
projects: `week1_baseline/file_system_mcp/`, `week1_baseline/shell_mcp/`, and
`week1_baseline/mud_manager_mcp/` (all Ruby/gem-based — there is no per-language server
duplication; Python's client spawns the same Ruby servers Ruby's own client does).

**Full design rationale for this architecture lives in `docs/plans/mud_manager/`, not here** —
this doc only tracks what's specific to the *Python port* of it:

- [`generic_interfacing.md`](../mud_manager/generic_interfacing.md) — why an MCP sidecar exists at
  all, and confirms Option B (stdio sidecar) "was built and is live for the Python port."
- [`mcp_generalization_plan.md`](../mud_manager/mcp_generalization_plan.md) — why the client speaks
  real MCP (JSON-RPC 2.0 over stdio) instead of a bespoke protocol.
- [`mcp_mud_plan.md`](../mud_manager/mcp_mud_plan.md) — why `Boukensha` itself ships no domain
  tools at all, filesystem/shell included, not just MUD.
- [`mcp_integration_verification.md`](../mud_manager/mcp_integration_verification.md) — live-server
  proof the sidecar approach actually works.
- [`gem_consolidation_plan.md`](../mud_manager/gem_consolidation_plan.md) — later Ruby-only
  packaging change (folding `mud_manager_mcp` into `mud_manager`); no Python-side effect.

Do not duplicate those docs' content here if this plan is revised again — link to them.

### What Python actually has

`boukensha/mcp.py` (`MCPClient`) is a near line-for-line port of Ruby's `lib/boukensha/mcp.rb`:

- `MCPClient.connect(command:, cwd:, env:)` spawns the given command as a subprocess, speaks the
  minimal JSON-RPC 2.0 subset needed for tool calling (`initialize`,
  `notifications/initialized`, `tools/list`, `tools/call`), and strips inherited `BUNDLE_*`/
  `RUBYOPT` env vars before spawning (so a Ruby server launched via `bundle exec` from inside an
  already-bundled process re-resolves its own Gemfile from `cwd` instead of inheriting the wrong
  one).
- `register_all(registry)` discovers whatever tools the connected server advertises and registers
  each one generically — the `Registry` never knows a tool came from MCP.
- Three convenience factory `@staticmethod`s build `{command, cwd, env}` specs for this repo's
  bundled servers: `file_system_server(working_dir=)`, `shell_server(working_dir=, timeout=,
  allowed_commands=)`, `mud_manager_server(name=, password=, host=, port=)`.
- `close()` is idempotent and also registered via `atexit`, matching Ruby's own cleanup guarantee.

`boukensha/__init__.py`'s `run()`/`repl()` build a default `mcp_servers:` list
(`_default_mcp_servers`) when the caller doesn't pass one explicitly: `file_system_mcp` +
`shell_mcp` rooted at `working_dir=` (skipped entirely when `working_dir=False`), plus
`mud_manager_mcp` when `Config.mud_host` and `Config.mud_username` are both set (Mud is **no
longer descoped** — Stage 2 ports it, unlike Stage 1's explicit exclusion). Connected clients are
tracked and closed in a `finally` block alongside the logger.

`Config` gained `mud_host`/`mud_port`/`mud_username`/`mud_password` readers (`config.py`,
mirroring `config.rb`'s `dig(:mud, ...)` block), read from `settings.yaml`'s `mud:` section.

`Repl._banner()` shows a `tools:` line reporting `Context.tool_count` ("registered (via MCP — see
mcp_servers:)"), matching Ruby's banner.

### `week1_baseline/bin/python/10_standard_tool_library`

Standard launcher, unchanged in shape from every other step.

## Audit findings and fixes (2026-07-31)

A correctness audit compared `python/10_standard_tool_library` against `ruby/10_standard_tool_library`
**as Ruby currently exists** (post-Stage-2), not against this doc's now-outdated Stage 1 content
(the audit is what triggered rewriting this doc in the first place — it had gone stale enough to
describe deleted files as current). Findings:

- **Confirmed correct:** `boukensha/mcp.py` vs `lib/boukensha/mcp.rb`, `__init__.py`'s MCP
  connect/cleanup wiring vs `lib/boukensha.rb`, `backends/anthropic.py`'s `_input_schema_for` vs
  `anthropic.rb`'s `input_schema_for`, `Config.mud_*` readers vs `config.rb`, `version.py ==
  "0.10.0"` matching `version.rb` (neither side bumped further in Stage 2), README.md's content
  (already described the MCP architecture accurately, no Stage-1 leftovers), `examples/example.py`,
  and the full test suite (233 tests passing, including MCP-client and Mud tests backed by
  `tests/toy_mcp_server.py`/`tests/fake_circlemud.py` fakes rather than the real Ruby servers).
- **Gap found and fixed:** `Repl._banner()` was missing the `tools:` line entirely (Ruby's
  `repl.rb:101` has it; Python's `_banner()` went straight from `provider:` to the blank line).
  Fixed by adding the line, using the already-existing `Context.tool_count`; added
  `test_banner_reports_tool_count` to `tests/test_repl.py`.
- **Bug found and fixed:** `_default_mcp_servers`'s Mud-connect condition
  (`boukensha/__init__.py`) required `cfg.mud_host and cfg.mud_username and cfg.mud_password`, one
  condition stricter than Ruby's `cfg.mud_host && cfg.mud_username` (`mcp.rb`/`lib/boukensha.rb`
  line 228 — `mud_host` always has a truthy `"localhost"` default, so Ruby's check is effectively
  just "username is set"). Practical effect: a user who configured `mud.username` but not
  `mud.password` got silently no Mud server in Python, where Ruby would attempt the connection and
  let it fail downstream when the MUD server rejects the login. Fixed by dropping the extra
  condition and wrapping the now-possibly-`None` `password=` argument in `cast(str, cfg.mud_password)`
  — same "Ruby passes `nil` through and lets it fail later; the cast expresses that for Python's
  static typing" pattern this file already uses for `api_key` (see the comment directly above the
  `match backend:` blocks in `run()`/`repl()`).
- **Not verified by the audit:** actually spawning the real Ruby `file_system_mcp`/`shell_mcp`/
  `mud_manager_mcp` gem servers cross-language from a live Python process end-to-end (bundler/gem
  availability was unconfirmed in the audit environment) — the passing test suite exercises the
  protocol via fakes, not the live Ruby servers. `mcp_integration_verification.md` covers live-server
  verification for Ruby's own client; no equivalent live run exists yet for Python's client
  specifically.

## Decisions carried over (no longer open)

- **Copy-forward-then-delta workflow**, `uv` + `hatchling`, flat `boukensha/` layout,
  `.python-version` = 3.14, `ruff`/`isort`/`ty` via `uv run`, `pytest` in `tests/` — unchanged, and
  unaffected by either stage.
- **Port observed Ruby quirks/behavior faithfully rather than silently correcting or omitting
  them** — established by `02_the_registry`/`04_api_client`/`08_the_repl_loop`, reapplied in the
  2026-07-31 audit to the Mud-connect condition: once the extra `mud_password` check was found to
  diverge from Ruby, the fix was to match Ruby's actual (looser) condition, not to keep Python's
  stricter one on the theory that stricter is safer.
- **Tools return error strings, never raise, for agent-recoverable failures** — this remains true
  at the MCP-server layer (`file_system_mcp`/`shell_mcp`), not in `boukensha` itself, since
  `boukensha` no longer implements any tool logic directly.
- **Never trust a Ruby README at face value; verify against actual code** — reapplied here in a new
  form: never trust *this plan doc* at face value either, once the underlying Ruby step changes
  shape out from under it. The original version of this doc (Stage 1) went stale the moment Stage 2
  landed and nobody had reason to open it again until the 2026-07-31 audit.
