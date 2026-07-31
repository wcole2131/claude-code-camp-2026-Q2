# Plan: Toward a Real MCP Server + a Generic `Boukensha::MCP` Client

**Status: implemented.** Phases 0–2 are built and verified (both against a
live CircleMUD server and, for genericity, against a toy non-MUD MCP
server). See "Implementation notes" at the bottom for what changed and
what was verified. Phase 3 remains a documented option, not built.

Companion to [`generic_interfacing.md`](./generic_interfacing.md) (why a
sidecar exists at all) and
[`mcp_integration_verification.md`](./mcp_integration_verification.md) (proof
the current sidecar works). This doc plans the next step, raised directly by
a design question: what we built is *not* the real Model Context Protocol —
it's a bespoke JSON-lines RPC with hand-duplicated tool schemas per language.
This plans the move to two separable, real things:

1. **`mud_manager_mcp` becomes an actual MCP server** — real JSON-RPC 2.0,
   `initialize`/`tools/list`/`tools/call`, content-typed results.
2. **A new `Boukensha::MCP`** (Ruby) / `boukensha.mcp` (Python) — a *generic*
   MCP client living inside the agent framework itself, that can connect to
   **any** MCP server (not just this one) and register whatever tools it
   advertises, dynamically, with no per-server hand-written schema.

These are two different pieces in two different places, and it's worth being
precise about which is which before touching code:

| | What it is | Where it lives | Analogous to |
|---|---|---|---|
| `mud_manager_mcp` | An MCP **server** for the MUD domain | `week1_baseline/mud_manager_mcp/` (unchanged location) | A specific MCP server, like any `mcpServers` entry in a Claude Desktop config |
| `Boukensha::MCP` | A generic MCP **client** | Inside each language's agent framework, e.g. `week1_baseline/ruby/10_standard_tool_library/lib/boukensha/mcp.rb` | The MCP client code inside Claude Desktop / Claude Code itself |

Today, `boukensha/tools/mud.py` conflates both roles into one file: it's a
transport client *and* a hand-written schema catalog, hardcoded to one
server. This plan separates those.

## Why the current thing isn't "real" MCP

Two gaps, previously discussed and worth restating precisely as the target
to close:

1. **No discovery.** Real MCP clients never hardcode tool schemas — they
   call `tools/list` at connect time and get `{name, description,
   inputSchema}` for every tool the server has, live. Our sidecar
   (`bin/mud_manager_server`) has no such call; both `mud.rb` and `mud.py`
   hand-list the same 27 tools. This is exactly the "open question" from
   `generic_interfacing.md`, resolved there as "hand-duplicate, revisit
   later" — this plan is that revisit.
2. **No generic client.** `Boukensha::Registry` only has purpose-built
   `register()` functions per tool module (`file_system`, `shell`, `mud`).
   There's no code path that says "spawn this MCP server, ask what it has,
   register all of it" for an arbitrary server — every integration is
   bespoke, including the one that happens to be a sidecar.

Not a gap, and out of scope to "fix": **content typing.** Real MCP tool
results are an array of typed content blocks (`text`, `image`, `audio`,
`resource`) so one generic client can handle non-text tools uniformly. MUD
is 100% textual — every `Tools::Mud` response is a string. Implementing the
`content: [{type: "text", ...}]` wrapper is trivial and required for
protocol compliance, but there is no non-text case to design for here. If a
future MCP server in this repo produces images/audio, `Boukensha::MCP`
should already handle it (see "Content handling" below) — but MUD itself
will only ever exercise the `text` branch.

## Target architecture

```
Any MCP server (mud_manager_mcp, or something else entirely)
        │  stdio: JSON-RPC 2.0
        │  initialize → tools/list → tools/call
        ▼
Boukensha::MCP (generic client, one per language port)
        │  registers each discovered tool against
        ▼
Boukensha::Registry (unchanged — this is the point: the registry
                      doesn't know or care a tool came from MCP)
```

`Boukensha::MCP.connect(command: [...], env: {...})` should do the full
handshake and hand back something that can register every discovered tool
against a `Registry` in a couple of lines — collapsing what's currently
~250 hand-written lines in `mud.py` down to a small, domain-agnostic client
plus a config block naming the server to launch.

## Phase 0 — decisions to make before writing code

### Hand-roll the protocol subset, or adopt an MCP SDK gem/package?

**Recommendation: hand-roll**, consistent with how the rest of this repo
works. `boukensha/backends/anthropic.py` and friends are hand-written HTTP
clients, not the `anthropic` SDK; the agent loop is hand-rolled, not built on
an agent SDK (see `docs/journal/0_preweek.md`: "we need to roll our own agent
without an SDK"). An MCP SDK dependency would break that pattern and hide the
exact mechanics this repo exists to teach. The subset of MCP actually needed
here is small: `initialize`, `notifications/initialized`, `tools/list`,
`tools/call`. That's implementable in well under 100 lines per language, on
top of stdlib JSON — no new gem/package dependency required on either side.

### The `required` gap in `Boukensha::Tool`

JSON Schema's `inputSchema` needs a `required: [...]` array. Boukensha's
current parameter format doesn't have one — `Registry#tool`'s `parameters:`
hash is just `{name: {type:, description:}}` per field; "is this required"
currently only exists implicitly, as which block arguments have a Ruby/Python
default value, and informally as an "(optional)" suffix in some
descriptions (e.g. `mud.rb`'s `look` tool: `preposition: nil`, described as
"(optional)"). This needs to become a real, explicit, machine-readable field.

**Recommendation:** add a `required:` key alongside `type`/`description` in
the parameter spec, default `true` (matching current de facto behavior where
most parameters are required), e.g.:

```ruby
parameters: {
  target:      { type: "string", description: "..." },                       # required (default)
  preposition: { type: "string", description: "...", required: false },      # optional
}
```

This is a small, mechanical, non-breaking change to every existing
`registry.tool(...)` call in `file_system.rb`/`.py`, `shell.rb`/`.py`, and
`mud.rb` (existing behavior unaffected; only used when generating
`inputSchema` for MCP `tools/list`, or by anything else that wants to
introspect a tool's shape). Needed before an MCP server can honestly answer
`tools/list`.

### Transport

**stdio only**, matching what's already built (`mud_manager_mcp` is spawned
as a subprocess today; nothing here needs a network listener). Real MCP also
defines Streamable HTTP/SSE for remote servers — explicitly out of scope; if
a future MCP server needs to run remotely, that's a separate, later
extension, not a blocker for this plan.

### Error semantics

MCP distinguishes two failure modes and this repo's current bespoke
`{ok: false, error: "..."}` shape doesn't:

- **Protocol-level errors** (bad method, malformed params) → standard
  JSON-RPC `error: {code, message}` object, no `result`.
- **Tool-level failures** (e.g. `Primitives.attack` raising `ArgumentError`
  for an invalid style) → a *successful* JSON-RPC response whose `result`
  has `isError: true` and a `content` block describing the failure. This is
  the same case `mud.rb`'s tool blocks already `rescue ArgumentError` and
  return an `"error: ..."` string for today — under real MCP that becomes
  `{content: [{type: "text", text: "error: ..."}], isError: true}` instead of
  a bare string.

## Phase 1 — `mud_manager_mcp` speaks real MCP

Rewrite `week1_baseline/mud_manager_mcp/bin/mud_manager_server`:

- Replace the ad hoc `{"id","tool","args"}` request shape with JSON-RPC 2.0:
  `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"look","arguments":{...}}}`.
- Handle `initialize` (report a minimal `capabilities: {tools: {}}` and
  `serverInfo`), then the `notifications/initialized` notification (no
  response — it's a notification, not a request).
- Handle `tools/list`: iterate `ctx.tools` (already populated by
  `Tools::Mud.register`, unchanged) and emit `{name, description,
  inputSchema}` per tool, building `inputSchema` from the (now `required:`-
  aware) parameter hashes.
- Handle `tools/call`: dispatch through `registry.dispatch` exactly as today,
  then wrap the string result as `{content: [{type: "text", text:
  result}], isError: false}` (or `isError: true` for the rescued-error
  case above).
- This is a breaking change to the wire format — no backward-compat shim
  for the old ad hoc protocol (per this repo's stated preference for clean
  breaks over compatibility shims). It must land together with Phase 2's
  client update, not separately, since the old `mud.py` speaks the old
  protocol and would otherwise break the moment the server changes.

Verification: re-run the same three checks from
`mcp_integration_verification.md` (Ruby in-process baseline unaffected;
sidecar driven directly; Python bridge through the sidecar) against the same
live CircleMUD server, confirming identical results under the new wire
format.

## Phase 2 — `Boukensha::MCP`, the generic client

New file per language port: `lib/boukensha/mcp.rb` and `boukensha/mcp.py`.
Shape (illustrative, not final):

```ruby
client = Boukensha::MCP.connect(
  command: ["bundle", "exec", "ruby", "bin/mud_manager_server"],
  dir:     "../../mud_manager_mcp",
  env:     { "MUD_HOST" => "localhost", "MUD_NAME" => "Gandalf", ... }
)
client.register_all(registry)   # tools/list → registry.tool(...) for each, generically
```

`register_all` is the piece that replaces every hand-written
`registry.tool("look", description: "...", parameters: {...}, block: ...)`
call in `mud.py` — the block it generates for every discovered tool is
always the same generic shape: `->(**args) { client.call_tool(name,
**args) }`. No MUD-specific code remains in the Python (or any future
language's) tool layer at all; `boukensha/tools/mud.py` shrinks to a config
block naming the server plus a `Boukensha::MCP.connect(...).register_all(...)`
call.

### Content handling

`call_tool` unwraps the `content` array back to what `Registry#dispatch`
callers already expect (a plain string), per this repo's existing
"errors are strings, not exceptions" convention (`file_system.py`'s
`resolve()` returning an error string rather than raising is the precedent).
Policy:

- One or more `text` blocks → join and return as a string (MUD only ever
  produces exactly one).
- `isError: true` → same string return, no exception — matches how
  `mud.rb`'s own rescued `ArgumentError` already just returns an `"error:
  ..."` string today; callers don't need a new failure path.
- Any other content type (`image`, `audio`, `resource`) → not needed for
  MUD, but a generic client can't silently drop them. Return a placeholder
  string (e.g. `"[unsupported content type: image]"`) rather than raising —
  keeps `Boukensha::MCP` usable by a future non-text MCP server without a
  crash, while being honest that rendering it isn't implemented yet.

### Proving it's actually generic

Hand-registering 27 MUD tools and calling it "generic" would be circular —
the whole point is that `Boukensha::MCP` shouldn't know or care what
server it's talking to. Add one deliberately non-MUD verification: a
trivial second MCP server (e.g. a two-tool "echo"/"add" toy server, a few
lines, no `mud_manager` dependency) that `Boukensha::MCP` connects to and
registers tools from using the exact same code path. This is the test that
actually validates genericity, distinct from the MUD-specific integration
tests.

## Phase 3 (stretch, not required for this plan) — config-driven servers

Once Phase 2 lands, `.boukensha/settings.yaml`'s single `mud:` block could
generalize to an `mcp_servers:` list (name → command/env), letting any
number of MCP servers be registered by config alone, with zero code changes
per server — the `mcpServers` pattern real MCP clients use. Not needed to
satisfy this plan's goal and not scoped further here; flagged so Phase 2's
`Boukensha::MCP` API is designed with this in mind (e.g. `connect` taking a
plain command/env spec rather than anything MUD-specific) rather than
needing a rewrite later.

## What doesn't change

- `week0_explore/mud_manager` (the gem) — untouched.
- `Boukensha::Tools::Mud` (`mud.rb`) — untouched except the mechanical
  `required:` addition to its `parameters:` hashes (Phase 0). Still the one
  place the 27 tool definitions live; still usable directly, in-process, by
  the Ruby step's own agent with no MCP involved at all (per
  `mcp_integration_verification.md` — that path stays a hard non-requirement
  on any of this).
- The single-session, one-socket-one-owner constraint on the MUD sidecar
  (`generic_interfacing.md`'s constraints section). Real MCP's `initialize`
  handshake doesn't add or remove anything here — the sidecar is still
  pinned to one already-logged-in character for its process lifetime either
  way. Genericity (discovery) and statefulness (session pinning) stay
  orthogonal, as discussed; this plan only closes the discovery gap.

## Rough sequencing

1. Phase 0 decisions land as small, low-risk edits (the `required:` field)
   across existing tool modules — safe on its own, no behavior change.
2. Phase 1 + Phase 2 land together (the server's wire-format change and the
   client that speaks it can't ship independently without breaking the
   existing bridge mid-way).
3. Re-verify against the live CircleMUD server (same three checks as
   `mcp_integration_verification.md`) plus the new non-MUD toy-server check
   for genericity.
4. Phase 3 stays a documented option, not committed work.

## Implementation notes

What actually landed, and where:

- **`required:`** added to `mud.rb`'s and `file_system.rb`/`.py`'s
  `parameters:` hashes (16 fields in `mud.rb`; `mud.py`'s hand-written
  literals were about to be deleted in the same pass, so left alone).
  `shell.rb`/`.py` had no optional parameters to annotate.
- **`bin/mud_manager_server`** rewritten to real JSON-RPC 2.0
  (`initialize`/`notifications/initialized`/`tools/list`/`tools/call`),
  `isError` semantics as designed (unknown tool → JSON-RPC error;
  everything else, including MUD's own rescued `ArgumentError`s, is a
  normal `isError: false` text result — MUD tools never actually raise for
  expected failures, so the `isError: true` path only fires for genuinely
  unexpected exceptions).
- **`Boukensha::MCP`** (`lib/boukensha/mcp.rb`) and **`MCPClient`**
  (`boukensha/mcp.py`) built as designed: `connect`/`tools`/`call_tool`/
  `register_all`/`close`, non-text content rendered as
  `"[unsupported content type: ...]"` rather than dropped or raised on.
- **`boukensha/tools/mud.py`** collapsed from ~350 hand-written lines to
  ~40 — a thin config wrapper around `MCPClient.connect(...).register_all(...)`.
  No MUD-specific schema left in Python at all.
- **`mud_manager_mcp/examples/demo.rb`** rewritten to use `Boukensha::MCP`
  instead of the old hand-rolled protocol (mandatory — the old protocol
  stopped existing the moment the server changed).
- **Genericity proof**: `tests/toy_mcp_server.py` (two tools, `echo`/`add`,
  zero Boukensha/mud_manager dependency) + `tests/test_mcp_client.py`
  (5 tests, no `bundle`/Ruby needed) prove `MCPClient` isn't secretly
  MUD-shaped. `Boukensha::MCP` was verified against the same toy server
  manually (no Ruby test framework exists in this repo to make it
  automated — consistent with every other Ruby step having zero automated
  tests).
- **Verified against the real live CircleMUD server** (the same one from
  `mcp_integration_verification.md`) for all three paths: the Ruby step's
  unaffected in-process baseline, `demo.rb` via `Boukensha::MCP`, and
  Python's `mud.py` via `MCPClient` — identical results (room description,
  score, inventory) across all three, under the new protocol.
- Full Python suite: 229 passed (224 prior + 5 new genericity tests), ruff/
  isort/ty clean. Ruby: syntax-checked (no test framework in this repo for
  Ruby steps, per existing convention).

Not built: Phase 3 (config-driven `mcp_servers:` list).
