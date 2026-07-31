# Step 12 — Context Management

When you call an LLM directly you are responsible for the context window. There is no auto-compacting. This step adds proper token tracking, visual warnings, and automatic compaction so the agent never silently blows past the limit.

## Tool library (inherited from step 10)

**Boukensha ships no tool implementations of its own.** Every capability — filesystem, shell,
MUD — lives outside the framework as its own standalone MCP server, and the agent gets its entire
tool surface by connecting to whichever ones you point it at. This is a deliberate architecture,
not a missing feature: see `docs/plans/mud_manager/mcp_mud_plan.md` for why. The framework itself
only ships the generic mechanism: `Registry`/`Tool`/`Context`, plus `Boukensha::MCP` — a client that
can connect to *any* MCP server and discover/register whatever tools it advertises, and
`Boukensha::MCP::Server` — the matching generic server-side helper every bundled MCP server uses.

### The three bundled servers

| Server | Directory | Tools |
|---|---|---|
| `file_system_mcp` | `week1_baseline/file_system_mcp/` | `pwd`, `list_directory`, `read_file`, `write_file`, `delete_file`, `search_files` |
| `shell_mcp` | `week1_baseline/shell_mcp/` | `run_command` |
| `mud_manager_mcp` | `week1_baseline/mud_manager_mcp/` | 27 MUD gameplay tools wrapping `mud_manager` (`mud_connect`/`look`/`attack`/`shop`/`send_raw`/...) |

Each is a real MCP server (JSON-RPC 2.0 over stdio: `initialize` → `tools/list` → `tools/call`) —
see their own READMEs for config (env vars) and protocol details.

### `Boukensha.run` / `Boukensha.repl`'s `mcp_servers:`

```ruby
Boukensha.run(
  task: "...",
  mcp_servers: [
    Boukensha::MCP.file_system_server(working_dir: "/my/project"),
    Boukensha::MCP.shell_server(working_dir: "/my/project", allowed_commands: ["ruby", "git"]),
    Boukensha::MCP.mud_manager_server(name: "Gandalf", password: "secret"),
  ]
)
```

`mcp_servers:` is the honest, literal shape of "tools are not part of the agent" — a list of
`{command:, dir:, env:}` specs, each connected via `Boukensha::MCP.connect(**spec).register_all(registry)`.
`Boukensha::MCP.file_system_server`/`.shell_server`/`.mud_manager_server` are just convenience
factories building the right spec for this repo's three bundled servers — nothing about connecting
to them is special.

Leave `mcp_servers:` unset and `run`/`repl` build a sensible default set instead: `file_system_mcp` +
`shell_mcp` rooted at `working_dir:` (default `Dir.pwd`; pass `working_dir: false` to exclude both),
plus `mud_manager_mcp` if `settings.yaml`'s `mud:` block has a `username` configured. `allowed_commands:`
and `shell_timeout:` only affect this default `shell_mcp` spec. Pass `mcp_servers: []` to connect to
nothing, or your own list to take full control.

```ruby
Boukensha.run(task: "...", working_dir: "/my/project", allowed_commands: ["ruby", "git"])
```

### `Boukensha::MCP` — the generic client

```ruby
client = Boukensha::MCP.connect(command: [...], dir: "...", env: {...})
client.tools                    # => tools/list result
client.call_tool("look")        # => tools/call result, unwrapped to a String
client.register_all(registry)   # registers every discovered tool generically
client.close
```

`register_all` is what `mcp_servers:` uses internally for each spec. Nothing about it is MUD- or
filesystem-specific.

## Terminal UI (inherited from step 11)

Boukensha ships a full terminal UI (TUI) built on the [`charm`](https://github.com/charm-ruby/charm) gem (bubbletea + lipgloss + bubbles). The plain REPL is still there and can be selected with `tui: false`.

### `Boukensha::Tui`

Wraps a `Repl` instance and replaces its raw `puts`/`gets` I/O with a structured four-zone display:

```
┌──────────────────────────────────────────────┐
│  conversation viewport (scrollable)           │
├──────────────────────────────────────────────┤
│  ⟳ live progress line (hidden when idle)     │
├──────────────────────────────────────────────┤
│  boukensha> input box                         │
├──────────────────────────────────────────────┤
│  status line (always-on)                      │
└──────────────────────────────────────────────┘
```

The **progress line** shows a spinner, current action, iteration counter (`n/MAX`), elapsed seconds, token counts (↑ in / ↓ out), and tool call count while the agent is running. When idle it shows context usage (used/max, percentage, colour-coded — see "Context colour coding" below) and turn count.

The **status line** always shows: version · model · context tokens used/max (colour-coded, with a `⚠` at 85%+) · registered tool count · wall-clock time.

**Keyboard shortcuts:**

| Key | Action |
|-----|--------|
| `Enter` | Submit input or slash command |
| `Esc` | Interrupt the running agent turn |
| `Ctrl+L` | Clear conversation history |
| `PgUp` / `PgDn` | Scroll conversation viewport |
| `Ctrl+C` / `Ctrl+D` | Quit |

The agent runs in a background thread so the UI stays responsive during long turns.

### `Boukensha.repl` — `tui:` keyword

```ruby
Boukensha.repl(tui: true)   # default — launches charm TUI
Boukensha.repl(tui: false)  # falls back to plain terminal REPL
```

The `--no-tui` CLI flag sets `tui: false` from the command line.

### `Repl` composability

`Repl` doesn't hard-code `puts`/`gets`. Three methods are public so `Tui` (or any other front-end) can drive it:

| Method | Purpose |
|--------|---------|
| `on_output(&block)` | Route all REPL output through a callback instead of stdout |
| `handle_command(input)` | Process a slash command; returns `:quit`, `:command`, or `nil` |
| `run_turn(input)` | Run one agent turn and route the result through `on_output` |

`banner`, `logger`, `context`, `model`, and `version` are also exposed as readers.

### `Logger#subscribe`

```ruby
logger.subscribe { |event| ... }
```

Every structured log event (`:iteration`, `:tool_call`, `:tool_result`, `:response`, `:compaction`, etc.) is broadcast to all registered subscribers as well as being written to the JSONL file. `Tui` uses this to update the live progress line and conversation view in real time without polling.

## What's new in this step

### Accurate context tracking

`Context` now maintains two distinct token counts:

| Attribute | What it measures |
|-----------|-----------------|
| `context_window` | The model's maximum input token capacity (default 200,000 for Anthropic) |
| `current_tokens` | Tokens actually used in the most recent API call (`usage.input_tokens` from the response) |

Previously `token_budget` (8,192) was displayed as the limit — that was the *output* `max_tokens`, not the context window. And the cumulative session token sum was shown as usage, which grew without bound even after `/clear`. Both are fixed.

The Agent updates `current_tokens` after every API response (including mid-turn tool-use calls), so the display always reflects what the next call will actually send.

### Context colour coding

The progress and status lines now colour the context indicator based on how full the window is:

| Usage | Colour | Meaning |
|-------|--------|---------|
| < 70% | Grey | Normal |
| 70–84% | Yellow | Approaching limit |
| ≥ 85% | Red | Compaction imminent |

A `⚠` symbol also appears in the status bar at 85%+.

### Auto-compaction

At the start of each agent turn, if `current_tokens / context_window ≥ 0.85`, the Agent automatically compacts the context before making any API call:

```
[context compacted — 12 messages dropped to free space]
```

Compaction drops the oldest 40% of messages (keeping at least 2) and resets `current_tokens` to 0. The first API call after compaction will report the true new size.

### `Context#compact_messages!`

```ruby
dropped = context.compact_messages!(target_fraction: 0.60)
# => 12  (number of messages dropped)
```

### `/compact` command

Manual compaction from the REPL or TUI:

```
boukensha> /compact
(compacted context — 12 messages dropped)
```

### `Logger#compaction` event

```json
{"phase":"compaction","before":172000,"dropped":12,"context_window":200000}
```

Emitted whenever auto- or manual compaction runs. The TUI subscribes to this event to display the compaction notice in the conversation view.

### `Boukensha.run` / `Boukensha.repl` — `context_window:` keyword

`token_budget:` is replaced by `context_window:` (default looked up from the configured model via `Boukensha::Models`):

```ruby
Boukensha.repl(context_window: 128_000)  # for a smaller model
```

## Run the demo

```sh
# Build and install this step's gem. If a later step's gem is already
# installed, `boukensha` will keep launching that version's loader instead —
# remove it first:
gem uninstall boukensha

gem build boukensha.gemspec
gem install boukensha-0.12.0.gem
```

```sh
ruby examples/example.rb

# via the global executable (launches the charm TUI):
BOUKENSHA_DIR=~/Sites/Claude-Code-Camp/.boukensha BOUKENSHA_PATH=~/Sites/Claude-Code-Camp/week1_baseline/12_context boukensha

# plain REPL (no charm dependency required):
BOUKENSHA_PATH=~/Sites/Claude-Code-Camp/week1_baseline/12_context boukensha --no-tui
```
