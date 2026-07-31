# Plan: No Tools Live In The Agent — Everything Arrives Over MCP

**Status: implemented.** All phases below are built and verified — against
the live CircleMUD server, a real filesystem, and real shell commands, from
Ruby's own agent's default `mcp_servers:` wiring (closing the one exception
`mcp_generalization_plan.md` had left open). See "Implementation notes" at
the bottom for what actually landed, including a couple of real bugs found
and fixed along the way and a few naming deviations from this doc's original
sketch.

Companion to [`mcp_generalization_plan.md`](./mcp_generalization_plan.md)
(which built a real, generic MCP client/server pair, but left it optional —
`file_system`/`shell` still register in-process, and even `mud` is only
MCP-brokered for *non-Ruby* languages). This plan removes that hedge. The
target, stated plainly: **`Boukensha` itself ships no domain tool
implementations at all.** Not `file_system.rb`, not `shell.rb`, not
`mud.rb`. Every capability — filesystem, shell, MUD, anything added later —
lives outside the agent framework as its own standalone MCP server. The
framework's own package contains only the generic mechanism: `Registry`,
`Tool`, `Context`, and `Boukensha::MCP` (client *and*, new in this plan,
server). `run`/`repl` stop taking `working_dir:`/`allowed_commands:`/`mud:`
kwargs that trigger built-in registration, and instead take a list of MCP
servers to connect to — the entire tool surface is whatever those servers
advertise via `tools/list`, discovered fresh, nothing hardcoded.

## Why this is more than "finish the MUD work"

The previous plan treated MCP-brokering as a fix for one specific problem:
`mud_manager` is a Ruby-only gem, so non-Ruby languages need a bridge.
`file_system`/`shell` never got that treatment because they have no such
problem — every language already has native filesystem/subprocess access.

That reasoning is true but incomplete: it only asks "does this tool need
brokering to cross a language boundary." It doesn't ask the question this
plan is answering — "should the agent have *any* built-in tools at all, or
should tool acquisition be one uniform mechanism regardless of whether a
boundary happens to exist." Under this plan, the answer is uniform: nothing
is special-cased. `file_system`/`shell` move out for the same reason `mud`
tools are MCP-served — not because they can't run in-process, but because
the agent shouldn't know how to run any tool in-process, period.

## Target architecture

```
week1_baseline/ruby/10_standard_tool_library/lib/boukensha/
  registry.rb, tool.rb, context.rb   -- generic primitives (unchanged)
  mcp.rb                             -- Boukensha::MCP, the generic CLIENT (already built)
  mcp/server.rb                      -- NEW: Boukensha::MCP::Server, the generic SERVER helper
  agent.rb, client.rb, backends/*    -- LLM agent loop (unchanged, always was domain-agnostic)
  tools/                             -- DELETED. No file_system.rb, shell.rb, mud.rb.

week1_baseline/mud_manager_mcp/          (already exists, unchanged in kind)
week1_baseline/file_system_mcp/          (NEW -- same shape)
week1_baseline/shell_mcp/                (NEW -- same shape)
  each: bin/<name>_server -- builds its own Registry, registers its OWN
        tool definitions (moved here from lib/boukensha/tools/*.rb), then
        Boukensha::MCP::Server.new(registry).serve -- same ~15 lines each,
        no hand-rolled JSON-RPC loop duplicated three times.

Boukensha.run(
  task: "...",
  mcp_servers: [
    { command: [...], dir: "../../file_system_mcp", env: { "WORKING_DIR" => Dir.pwd } },
    { command: [...], dir: "../../shell_mcp",        env: { "WORKING_DIR" => Dir.pwd } },
    { command: [...], dir: "../../mud_manager_mcp",  env: { "MUD_HOST" => "...", ... } },
  ]
)
```

`run`/`repl` do nothing but loop over `mcp_servers` and call
`Boukensha::MCP.connect(**spec).register_all(registry)` for each — one code
path, no per-domain special casing, whether the server is MUD, filesystem,
shell, or something added next year.

## A consequence worth naming explicitly: one implementation per domain, not one per language

Today `file_system.rb` and `file_system.py` are hand-duplicated (same for
`shell.rb`/`shell.py`) — every language port re-implements the same
filesystem logic. Once filesystem tools are their own MCP server, that
duplication has no reason to exist: there only needs to be **one**
`file_system_mcp` implementation (in whichever language), and every
language's agent — Ruby's own, Python's, a future Node port — connects to
that one server the same way. This is the same "port once, reuse
everywhere" win `mud_manager_mcp` already delivered for MUD, now extended to
every tool domain, not just the one with a hard cross-language blocker.

## Decisions

### 1. Extract a generic `Boukensha::MCP::Server` (and its Python mirror)

Three server directories each need the same ~90-line JSON-RPC request loop
`mud_manager_mcp/bin/mud_manager_server` currently hand-rolls
(`initialize`/`notifications/initialized`/`tools/list`/`tools/call`,
`input_schema_for`, error mapping). Copy-pasting it three times is exactly
the duplication this whole effort exists to avoid.

**Recommendation:** extract `Boukensha::MCP::Server` — takes a `Registry`,
runs the stdio JSON-RPC loop generically (deriving `tools/list` from
whatever's registered, dispatching `tools/call` via `registry.dispatch`).
Every server's `bin/*_server` script shrinks to: build a registry, register
its own tools (the domain logic that used to live in `lib/boukensha/tools/`,
now local to that server directory), call
`Boukensha::MCP::Server.new(registry).serve`. `mud_manager_mcp` gets
refactored onto this first (pure refactor, no new server yet) to prove it
before building the two new ones on top of it.

### 2. Where does server-side config (`working_dir`, `allowed_commands`, `timeout`) come from?

Same convention as `MUD_HOST`/`MUD_PORT`/`MUD_NAME`/`MUD_PASSWORD` — environment
variables read at server startup, since these are now subprocesses, not
in-process function calls:

| Server | Variable | Default |
|---|---|---|
| `file_system_mcp` | `WORKING_DIR` | required |
| `shell_mcp` | `WORKING_DIR` | required |
| `shell_mcp` | `SHELL_TIMEOUT` | `30` |
| `shell_mcp` | `ALLOWED_COMMANDS` | unset = allow all; comma-separated list otherwise |

### 3. `mcp_servers:` alone, or keep convenience sugar?

A raw `mcp_servers:` list is the literal, honest shape of "tools are not
part of the agent" — but it makes every call site spell out three
subprocess specs instead of `working_dir: "..."`.

**Recommendation:** keep the primitive raw (no hidden magic in `run`/`repl`
beyond "connect to what's listed"), but add small opt-in helper functions
that build the common specs — e.g. `Boukensha::MCP.local_file_system(working_dir:)`
returning the right `{command:, dir:, env:}` hash for the bundled
`file_system_mcp`. Callers who want the one-liner get it; the framework
itself still only knows "connect to these servers," never "how to run a
filesystem tool."

### 4. Server lifecycle

Unchanged from the existing pattern: one subprocess per server, spawned
once at `run`/`repl` startup and held for the session, not re-spawned per
tool call. This matters more now than it did for MUD alone — `bundle exec
ruby` startup is ~5-6s (measured earlier, dominated by Bundler/gem
resolution), so a `read_file` call must not pay that cost per call. This
was already true for `mud_manager_mcp`; it now has to be true for the two
new servers as well.

### 5. Ruby's own agent stops being the exception

Today, Ruby's own `Boukensha.run`/`repl` register `Tools::Mud` in-process,
directly — the one path this whole effort explicitly left alone as "not a
requirement." Under this plan that asymmetry goes away: Ruby's own agent
also reaches MUD (and filesystem, and shell) exclusively through
`mcp_servers:`, identically to Python. There is no more in-process
registration path for anything, in any language.

## Honest tradeoffs

- **Latency.** Every tool call — even `pwd` — becomes a subprocess IPC round
  trip instead of a direct method call. Small and constant per call once a
  server is warm, but non-zero, and worth saying plainly rather than
  glossing over.
- **Pedagogical shift.** This repo's `week1_baseline/<lang>/` steps have so
  far been "hand-port the same lesson into a new language, including every
  tool implementation." Once tool implementations move out into shared MCP
  servers, that specific lesson (port `file_system.rb` to `file_system.py`)
  stops applying to future ports — a new language port gets tools "for
  free" via `Boukensha::MCP`, the same way this plan gives Python's `mud.py`
  its tools for free today. That's the intended outcome, not a bug, but it
  does change what "porting a step" means going forward, and is worth
  naming rather than discovering by surprise later.

## Phased sequencing

1. **Extract `Boukensha::MCP::Server`** (Ruby) and refactor
   `mud_manager_mcp/bin/mud_manager_server` onto it — pure refactor, same
   external behavior, verified against the same live CircleMUD checks
   already established.
2. **Build `file_system_mcp` and `shell_mcp`** as new standalone server
   directories, moving `file_system.rb`/`shell.rb`'s tool logic into them,
   config via the env vars above.
3. **Delete `lib/boukensha/tools/{file_system,shell,mud}.rb`** and the
   equivalent Python modules. Rewrite `boukensha.rb`/`__init__.py`'s
   `run`/`repl` to take `mcp_servers:` (plus the opt-in helpers from
   decision 3), dropping `working_dir:`/`allowed_commands:`/`shell_timeout:`/
   `mud:` as registration triggers entirely.
4. **Rewrite the test suites** that exercised the now-removed in-process
   modules (`test_tools_file_system.py`, `test_tools_shell.py`) to match
   `test_tools_mud.py`'s shape — spawn the real server, dispatch through
   the registry via `MCPClient`, same pattern already proven for MUD.
5. Re-verify end to end: the live-CircleMUD checks for `mud_manager_mcp`,
   plus equivalent real-filesystem/real-shell checks for the two new
   servers, all reached exclusively through `mcp_servers:` — including from
   Ruby's own agent, closing the one exception this effort had left open.

## What doesn't change

- `week0_explore/mud_manager` (the gem) and its command primitives.
- The LLM agent loop, backends, prompt building, logging — always
  domain-agnostic, untouched by any of this.
- `Boukensha::MCP` (the client) and its content-handling/genericity
  guarantees, already built and proven in `mcp_generalization_plan.md`.

## Implementation notes

What actually landed, file by file, plus a couple of real bugs this
uncovered along the way:

- **`Boukensha::MCP::Server`** (`lib/boukensha/mcp/server.rb`) — the generic
  server helper, exactly as scoped. `mud_manager_mcp/bin/mud_manager_server`
  now uses it (~30 lines, down from hand-rolling the JSON-RPC loop). Needed
  one small addition to make this possible: `Registry` gained a `tools`
  accessor (`context.tools` proxy) and `attr_reader :context`, since the
  server needs to enumerate a registry's tools generically from outside it.
  No Python `MCPServer` was built — nothing in this repo ever hosts a
  server from Python (all three bundled servers are Ruby), so it would have
  been unused speculative code.
- **`file_system_mcp/` and `shell_mcp/`** — built as new standalone
  directories, each with their own `Gemfile` (path-depending on the ruby
  step for generic primitives *only*), `bin/*_server`, and a `lib/*_tools.rb`
  holding the tool logic moved out of the framework. Config via
  `WORKING_DIR`/`SHELL_TIMEOUT`/`ALLOWED_COMMANDS` env vars, per the plan.
- **`mud.rb` → `mud_manager_mcp/lib/mud_tools.rb`** — moved essentially
  verbatim (module renamed from `Boukensha::Tools::Mud` to a standalone
  `MudTools`, since it's no longer nested inside a framework namespace it's
  not part of). `boukensha.gemspec`'s `mud_manager` dependency was removed
  in the same pass — the framework no longer touches that gem at all now
  that nothing inside it does.
- **`Boukensha::MCP.file_system_server`/`.shell_server`/`.mud_manager_server`**
  — the convenience factories from decision 3, added as class methods on
  `Boukensha::MCP` itself (mirrored in Python as `MCPClient` static methods)
  rather than as separate `Tools::X` modules, since they're just spec
  builders now, not registration code.
- **`boukensha.rb`/`__init__.py`** — `run`/`repl` take `mcp_servers:`
  (`None`/unset → build defaults from `working_dir:`/`allowed_commands:`/
  `shell_timeout:`/`settings.yaml`'s `mud:` block; `[]` → connect to
  nothing; anything else → used as-is). `Repl`'s banner lost its
  MUD-specific TCP-probe (`mud_status_string`/`probe_mud`) since there's no
  longer a single `mud:` config to probe — it now just reports
  `context.tool_count`, a generic number regardless of which servers
  produced it.
- **Real bug found and fixed**: `Boukensha::MCP#connect!`/`MCPClient.__init__`
  spawn `bundle exec ruby ...` for a *different* Gemfile than whatever the
  calling process itself is running under. The first working version of
  this (an env-filtering `.reject`) didn't actually work —
  `Process.spawn`'s env hash *merges* with the inherited environment;
  removing a key from the hash you pass doesn't unset it in the child, only
  an explicit `nil` value does. Without the fix, Ruby's own agent (already
  running under one `bundle exec`) spawning `mud_manager_mcp` (a *different*
  Gemfile) inherited the wrong `BUNDLE_GEMFILE`/`RUBYOPT` and resolved
  `mud_manager` against the wrong bundle, failing with a `LoadError` that had
  nothing to do with the actual code. Python's `MCPClient` never had this
  bug — `subprocess.Popen`'s `env=` argument fully replaces the environment
  rather than merging, so the equivalent filter there worked on the first
  try.
- **Real bug found and fixed**: reading a non-UTF-8 file through
  `file_system_mcp`'s `read_file` used to succeed (Ruby's `File.read`
  doesn't validate encoding the way Python's text-mode read does), and the
  invalid bytes then crashed `JSON.generate` downstream in the transport
  layer with a confusing `JSON::GeneratorError` instead of a clean tool
  error. Fixed by having `read_file` check `content.valid_encoding?` itself
  and return `"error: file is not valid UTF-8 text"` — restoring the
  original Python-era behavior/test expectations exactly, and keeping the
  "invalid data → clean per-tool error string" convention intact rather
  than papering over it with a generic transport-level sanitizer.
- **Tests**: `test_tools_file_system.py`/`test_tools_shell.py` rewritten to
  spawn the real Ruby servers (matching `test_tools_mud.py`'s existing
  shape) rather than testing in-process Python modules that no longer
  exist. Filesystem tests share one module-scoped server across ~16 tests
  by giving each test its own subdirectory of a shared root (a fresh
  subprocess per test would cost ~5-6s of Bundler startup each); shell
  tests use three module-scoped servers grouped by config (default/timeout/
  allow-list), since `timeout:`/`allowed_commands:` are now fixed at server
  startup rather than per-call. `test_boukensha_run.py`/`test_boukensha_repl.py`'s
  registration tests were rewritten to mock `_connect_mcp_servers` and
  assert on the specs it would have been called with, rather than mocking
  `boukensha.file_system`/`.shell` (which no longer exist).
- **Verified live**: Ruby's own agent, using its *default* `mcp_servers:`
  (no explicit list), successfully connected to all three real servers
  simultaneously — `file_system_mcp` and `shell_mcp` against a real
  directory, `mud_manager_mcp` against the same live CircleMUD server used
  throughout this whole effort — landing 34 tools in one `Registry` and
  dispatching through all three domains correctly. Full Python suite: 232
  passed, ruff/isort/ty clean.
