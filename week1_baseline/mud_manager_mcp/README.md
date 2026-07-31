# mud_manager_mcp — a real MCP server for the MUD

`mud_manager` (`week0_explore/mud_manager/`) is a Ruby gem: a telnet client
(`MudManager::Session`) plus a library of ~40 CircleMUD command builders
(`MudManager::Primitives`). It's Ruby-only, but every language port of
Boukensha under `week1_baseline/` (Ruby, Python, and whatever comes next)
needs a way to drive a MUD session. Reimplementing the telnet client, login
dance, IAC stripping, and prompt-timing logic from scratch in every language
would mean re-verifying every edge case, in every language, against a live
CircleMUD server.

This directory is that generic interface instead: `bin/mud_manager_server` is
a real **MCP (Model Context Protocol) server** — JSON-RPC 2.0 over stdio,
`initialize` → `tools/list` → `tools/call` — so *any* MCP client, in any
language, can discover and call all 27 MUD tools without hardcoding their
schemas. See `docs/plans/mud_manager/generic_interfacing.md` (why a sidecar
exists at all) and `docs/plans/mud_manager/mcp_generalization_plan.md` (why
it speaks real MCP rather than a bespoke protocol, and what
`Boukensha::MCP`/`MCPClient` — the generic clients that talk to it — look
like).

## What lives here vs. what doesn't

- **`bin/mud_manager_server`** — the MCP server, built on the generic
  `Boukensha::MCP::Server` (a Bundler path dependency on
  `../ruby/10_standard_tool_library`, for the generic primitives only —
  `Registry`/`Context`/`Server`, nothing MUD-specific).
- **`lib/mud_tools.rb`** — the actual tool definitions (27 tools: `look`,
  `attack`, `shop`, `send_raw`, ...). This used to live inside the Boukensha
  framework itself as `Boukensha::Tools::Mud` — it moved here because the
  framework no longer ships any domain tool implementations at all (see
  `docs/plans/mud_manager/mcp_mud_plan.md`). This is server-side code now,
  not agent-side code.
- **`examples/demo.rb`** — a manual smoke test client (see below).
- **Not here:** the `mud_manager` gem itself, and the Ruby agent's own
  in-process usage of these tools (there isn't any anymore — see below).

## Protocol

Real MCP: JSON-RPC 2.0 messages, one per line, over stdin/stdout. The
minimal subset needed for tool calling:

```
→ {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"...","version":"..."}}}
← {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"mud_manager_mcp","version":"0.1.0"}}}

→ {"jsonrpc":"2.0","method":"notifications/initialized","params":{}}
   (a notification -- no id, no response)

→ {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
← {"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"look","description":"...","inputSchema":{"type":"object","properties":{...},"required":[...]}}, ...]}}

→ {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"look","arguments":{}}}
← {"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"The Temple Square\nYou are standing..."}],"isError":false}}
```

Two distinct failure modes, per the MCP spec:

- **Protocol-level errors** (unknown tool name, malformed params) → a
  JSON-RPC `error: {code, message}` object, no `result`.
- **Tool-level failures** (e.g. an invalid `attack` style) → a *successful*
  response whose `result.isError` is `true`, with the failure message as a
  `text` content block — this is how `MudTools`'s own rescued
  `ArgumentError`s already surface today (as a string, not an exception), so
  in practice this path is rarely hit; most "failures" here are just
  ordinary `isError: false` text results that happen to start with
  `"error: "`.

Every `tools/call` is a blocking round trip (the server handles requests one
at a time, in order); there's no pipelining. `tools/list`'s tool set is
static for the lifetime of a connection — it's derived once from
`MudTools.register`'s output at startup.

Connection params come from the environment, matching the `MUD_*` convention
`bin/boukensha` already uses:

| Variable | Default | Required |
|----------|---------|----------|
| `MUD_HOST` | `localhost` | no |
| `MUD_PORT` | `4000` | no |
| `MUD_NAME` | — | yes |
| `MUD_PASSWORD` | — | yes |

## Running it

```sh
bundle install   # first time only
MUD_HOST=localhost MUD_PORT=4000 MUD_NAME=Gandalf MUD_PASSWORD=secret \
  bundle exec ruby bin/mud_manager_server
```

It logs in immediately (same auto-connect behavior as `MudTools.register`),
prints `[mud_manager_server] ready — 27 tools registered` to stderr, then
waits for JSON-RPC requests on stdin.

### Manual smoke test: `examples/demo.rb`

```sh
bundle install   # first time only
MUD_HOST=your.mud.host MUD_PORT=4000 MUD_NAME=YourChar MUD_PASSWORD=yourpass \
  bundle exec ruby examples/demo.rb
```

Uses `Boukensha::MCP` (the generic client, `lib/boukensha/mcp.rb` in the
ruby step) to connect, list tools, and drive `mud_status`, `look`,
`check score`, `check inventory`, then `mud_disconnect` — printing each
request/response pair. Only read-only commands, so it's safe to run against
a live CircleMUD server to confirm the server itself works end to end,
independent of any particular language's client.

## Who uses this

The Ruby step's own agent connects here too now (via `Boukensha::MCP` and
`Boukensha.default_mcp_servers`) — there is no more in-process shortcut, MUD
tools reach the agent exactly the same way regardless of language. Python's
`boukensha.run`/`repl` do the same via `MCPClient.mud_manager_server(...)`
(`boukensha/mcp.py`, Python's equivalent of `Boukensha::MCP`) — no
hand-written MUD tool schema anywhere in Python; every tool comes from
`tools/list` at connect time. Python's tests (`tests/test_tools_mud.py` +
`tests/fake_circlemud.py`) spawn this server for real against a fake
CircleMUD double — a genuine cross-language integration test, not a mock.
`tests/test_mcp_client.py` + `tests/toy_mcp_server.py` prove `MCPClient`
generalizes beyond this server specifically, using a two-tool toy MCP server
with no MUD or Boukensha dependency at all.
