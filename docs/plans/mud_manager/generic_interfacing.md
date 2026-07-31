# Generic Interfacing: Cross-Language Access to the MUD

**Status: implemented.** Option B (sidecar over stdio) was built and is live for
the Python port — see [Implementation](#implementation) at the bottom for what
exists and where. The rest of this doc is the design exploration that led there,
kept as the rationale for *why* it looks the way it does.

## Problem

`mud_manager` (`week0_explore/mud_manager`) is a Ruby gem: a telnet client
(`MudManager::Session`) plus a library of ~40 CircleMUD command builders
(`MudManager::Primitives`). It is wired into the agent exactly once, in
`week1_baseline/ruby/10_standard_tool_library/lib/boukensha/tools/mud.rb`,
which registers ~25 tools (`look`, `attack`, `cast_spell`, `shop`, ...) against
the Ruby `Registry`.

This repo now ports the same agent framework hand-by-hand into other
languages — `week1_baseline/python/10_standard_tool_library` mirrors the Ruby
`file_system` and `shell` tool modules line-for-line, but there is **no MUD
tool module yet on the Python side**, and none is possible without either:

1. reimplementing the telnet client (socket handling, IAC stripping, the
   login-menu dance, the `"> "` prompt-sentinel read strategy) from scratch in
   every language, re-verifying every timing-sensitive edge case against a
   live CircleMUD server each time, or
2. giving every language port a generic way to drive **one** MUD session
   without owning the socket itself.

Every future port (Node, Go, whatever comes after Python) hits the same wall.
This doc explores option 2: a language-agnostic interface to `mud_manager`.

## Constraints from the existing code

- **The session is stateful and long-lived.** One `TCPSocket` per logged-in
  character, held open across the whole agent run (`Mud.register` opens it
  once via closure — see `mud.rb:1` header comment — and every tool call
  reuses it).
- **Only one process should own the socket.** CircleMUD's login dance
  (`session.rb:169`) already special-cases `"Reconnecting"` vs `"Welcome"` —
  a second concurrent login with the same character name would trigger that
  same reconnect path server-side and likely evict the first connection.
  Whatever design we pick must preserve "one socket, one owner."
- **Reads are synchronous per command, not streamed.** `send_cmd` in
  `mud.rb:77-82` is `drain → send_command → read_until_prompt`: exactly one
  blocking round trip per tool call, already serialized by the caller. There
  is no concurrent multi-command pipelining to preserve across a new
  boundary — a plain request/response call maps onto this cleanly.
- **The background thread + mutex/condvar in `Session`** (`session.rb:39-43`,
  `198-225`) is purely an internal implementation detail for buffering async
  MUD chatter between commands. It doesn't need to exist on the "client"
  side of any interface — it only needs to keep existing inside whatever
  process still owns the socket.
- **No automated tests exist today** — the only test artifact is
  `week0_explore/mud_manager/examples/live_session_test.rb`, a manual script
  that requires a live CircleMUD server and real credentials. Any interface
  we introduce is an opportunity to fix this by letting a fake MUD-in-a-box
  test double sit behind the same boundary.

## Options considered

### A. Reimplement per language (status quo, extended)

Port `Session` and `Primitives` into Python (and Node, and...) the same way
`file_system.py`/`shell.py` were hand-ported from Ruby.

- **Pros:** No new process, no IPC, fits the repo's existing "hand-port
  everything" pedagogical style exactly.
- **Cons:** The hard part isn't the ~40 primitive builders (those are pure
  string templates) — it's `session.rb`'s telnet/IAC-stripping, the
  login-menu regex dance, and the `read_until_prompt` timing heuristic
  (`quiet_seconds`, the `"> "` sentinel, the fallback-to-drain-on-timeout
  behavior). All of that would need independent reimplementation *and*
  independent verification against a live server, per language, with every
  bug fixed once instead of everywhere. This is exactly the duplication the
  problem statement wants to avoid.

### B. Extract `mud_manager` into a sidecar process, speak line-delimited JSON over stdio

Give the Ruby gem a small "server mode" entry point: it opens the socket,
runs `session.login(name, password)` exactly as `Mud.register` already does
today, then loops reading one JSON object per line from stdin and writing one
JSON object per line to stdout.

```
→ {"id": 1, "tool": "look", "args": {"target": null, "preposition": null}}
← {"id": 1, "ok": true, "result": "The Temple Square\nYou are standing..."}

→ {"id": 2, "tool": "attack", "args": {"target": "rat", "style": "kill"}}
← {"id": 2, "ok": false, "error": "not connected — call mud_connect first"}
```

Each language's agent spawns this subprocess (e.g.
`Popen(["ruby", "-r", "mud_manager/server", ...])` from Python), writes a
request line, blocking-reads the matching response line, and returns
`result` (or raises on `error`) — the same shape `send_cmd.call` already
returns today. Framing is trivial: embedded newlines inside a MUD response
(room descriptions, `who` lists) are just an ordinary JSON string value,
already `\n`-escaped by the JSON encoder, so "one JSON object per line" holds
regardless of what CircleMUD sends back.

- **Pros:** All CircleMUD-specific complexity (telnet, IAC stripping, login
  regexes, prompt sentinel, all 40 primitives) lives in exactly one codebase
  — the Ruby gem, basically unchanged, just with a request loop bolted on.
  Every other language's `tools/mud.*` module shrinks to a thin bridge:
  spawn, write a line, read a line, same size/shape as `file_system`/`shell`
  tool modules already are. Process lifetime is tied to the parent (dies
  with it — no orphaned sockets, no port to leak). Requires zero new
  dependencies (stdio is available everywhere); no port allocation or
  discovery problem the way a network service would have. The "one socket,
  one owner" constraint falls out for free — there is exactly one sidecar
  process per agent run.
- **Cons:** Introduces a subprocess to manage (spawn, detect a dead child,
  surface a clear error rather than hanging on a broken pipe). Slightly less
  ad-hoc-inspectable during development than a raw TCP/HTTP endpoint (can't
  just `curl` it — though `echo '{"tool":"look","args":{}}' | ruby ... ` works
  fine by hand).

### C. Run `mud_manager` as a standing network service (TCP/Unix socket or HTTP)

Same RPC idea as B, but the Ruby side listens on a socket/port instead of
stdio, and each language connects as a network client.

- **Pros:** Inspectable with `nc`/`curl` during development; in principle
  lets multiple independent processes attach.
- **Cons:** That last point is actually a liability here, not a benefit — two
  attached clients driving the same character session is exactly the
  reconnect-collision scenario the login dance already has to special-case.
  Adds real operational surface this project doesn't otherwise need: picking
  a port, detecting "is the server already running," cleaning up an orphaned
  server process if the agent crashes without disconnecting. For a
  single-agent-process-at-a-time pedagogical repo, this is solving a
  multi-tenant problem nobody has.

**Recommendation: B.** It gets the same language-agnostic win as C without
inventing lifecycle/discovery problems the project doesn't have, and it's the
smallest structural change — the Ruby gem keeps being the single source of
truth for CircleMUD behavior, it just grows a request loop.

## Open question: how do other languages learn the tool schema?

The RPC boundary in option B only needs to carry *dispatch* (tool name + args
→ result text). But each language's `Registry.tool(...)` call also needs a
`description` and a `parameters` schema to hand to its own LLM backend's
`to_tools` conversion (`backends/base.py:70`) — and today those ~25
descriptions/schemas are hand-written Ruby literals inside `mud.rb`.

Two ways to handle that, and this is a real judgment call rather than a
clear winner:

1. **Duplicate the schema by hand per language**, same as `file_system.py`
   and `shell.py` were hand-ported today — only *dispatch* crosses the
   bridge. Consistent with how this repo has ported everything else so far;
   costs 25 tool definitions of manual translation (and re-translation on
   drift) per new language.
2. **Add a `describe` RPC call** that returns the full tool catalog (name,
   description, parameter schema) as JSON, and have each language's
   `tools/mud.*` module build its registry entries from that response at
   registration time instead of listing them as literals. Eliminates
   per-language drift risk for 25 tools, at the cost of being a genuine
   architecture change (schema becomes data fetched at runtime, not code) —
   a bigger departure from the "hand-port everything" pattern used
   elsewhere.

Worth deciding before implementing B, since it changes the shape of every
language's `tools/mud.*` module (thin literal-registration file vs.
dynamic-registration-from-`describe` file).

**Decision: option 1** (hand-duplicate the schema). Implemented as-is; revisit
only if keeping the schema in sync across languages by hand turns out to hurt
in practice — see [Implementation](#implementation).

## Implementation

Option B is built, tested, and wired in for the Python port. The sidecar
lives in its own top-level directory, `week1_baseline/mud_manager_mcp/`,
rather than inside the Ruby lesson step — it's cross-cutting infrastructure
shared by every language port, not part of any one step's lesson content:

- **`week1_baseline/mud_manager_mcp/bin/mud_manager_server`** — the sidecar.
  Builds a real `Boukensha::Context`/`Registry`, calls `Tools::Mud.register`
  against it completely unmodified (so the dispatch table *is* `mud.rb`'s
  existing tool blocks, not a reimplementation), then loops `STDIN.each_line`
  → `registry.dispatch(tool, args)` → one JSON object per line on `STDOUT`.
  Connection params come from `MUD_HOST`/`MUD_PORT`/`MUD_NAME`/
  `MUD_PASSWORD`, matching the env-var convention `bin/boukensha` already
  used. Its own `Gemfile` depends on `boukensha` via a Bundler path
  dependency on `../ruby/10_standard_tool_library` (plus `mud_manager` via a
  path dependency on `week0_explore/mud_manager`) — so the 27 tool
  definitions stay in exactly the one place they were already written
  (`mud.rb`), reused rather than duplicated or vendored into the sidecar's
  own directory.
- **`week1_baseline/python/10_standard_tool_library/boukensha/tools/mud.py`**
  — the bridge. `MudBridge` spawns the sidecar with `bundle exec ruby
  bin/mud_manager_server` (cwd set to `mud_manager_mcp/` so Bundler resolves
  *its* `Gemfile`), and `register()` hand-registers the same 27 tools against
  the Python `Registry`, one for one with `mud.rb`, each block a one-line
  call into `bridge.call(tool, **args)`.
- **`boukensha.run`/`boukensha.repl`** in Python's `boukensha/__init__.py`
  gained a `mud=` kwarg mirroring Ruby's: a dict registers it, `False`
  disables it, `None` (default) falls back to `Config.mud_*` — same
  `mud_opts_from_config` shape as `boukensha.rb`.
- **Tests**: `week1_baseline/python/10_standard_tool_library/tests/
  fake_circlemud.py` is a small in-process TCP double that replays the
  CircleMUD login dance (the "opportunity to fix" no-test-coverage gap noted
  above), and `tests/test_tools_mud.py` spawns the *real* Ruby sidecar
  against it — a genuine cross-language integration test, not a mock. It's
  module-scoped (one sidecar process reused across the file, not one per
  test — `bundle exec ruby` startup is ~5-6s on its own, dominated by
  Bundler/gem resolution rather than anything MUD-specific) and skips itself
  if `bundle` isn't on `PATH`.

Not built: the `describe` RPC (schema option 2) — not needed yet with only
one other language port to keep in sync.
