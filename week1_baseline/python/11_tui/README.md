# 11 · A Terminal UI (Python port)

Python port of `week1_baseline/ruby/11_tui`. Boukensha now ships a full terminal UI (TUI) —
Ruby builds it on the [`charm`](https://github.com/charm-ruby/charm) gem (bubbletea + lipgloss +
bubbles); Python has no binding to those Go libraries, so this port uses
[`textual`](https://github.com/Textualize/textual) instead, which is the closest Python
equivalent: a real full-screen async event loop, a built-in widget library, and CSS-based
styling. The plain REPL from step 10 is still there and can be selected with `tui=False`.

## Tool library (inherited from step 10)

**Boukensha ships no tool implementations of its own.** Every capability — filesystem, shell,
MUD — lives outside the framework as its own standalone MCP server, and the agent gets its entire
tool surface by connecting to whichever of those servers you point it at. Unchanged from step 10;
see `docs/plans/mud_manager/mcp_mud_plan.md` for the design rationale, and step 10's own history in
`docs/plans/python_port/10_standard_tools.md` for how `boukensha.mcp.MCPClient` and the three
bundled servers (`file_system_mcp`, `shell_mcp`, `mud_manager_mcp`) work.

## What's new in this step

### `boukensha.tui.Tui`

New class. Wraps a `Repl` instance and replaces its raw `print`/`input` I/O with a structured
four-zone display:

```
+--------------------------------------------------+
|  conversation viewport (scrollable)               |
+--------------------------------------------------+
|  <spinner> live progress line (hidden when idle)  |
+--------------------------------------------------+
|  boukensha> input box                             |
+--------------------------------------------------+
|  status line (always-on)                          |
+--------------------------------------------------+
```

The **progress line** shows a spinner, current action, iteration counter (`n/MAX`), elapsed
seconds, token counts (↑ in / ↓ out), and tool call count while the agent is running. When idle it
shows context usage and turn count.

The **status line** always shows: version · model · context tokens used · registered tool count ·
wall-clock time.

**Keyboard shortcuts:**

| Key | Action |
|-----|--------|
| `Enter` | Submit input or slash command |
| `Esc` | Interrupt the running agent turn |
| `Ctrl+L` | Clear conversation history |
| `PgUp` / `PgDn` | Scroll conversation viewport |
| `Ctrl+C` / `Ctrl+D` | Quit |

Each agent turn runs on a background thread (`App.run_worker(..., thread=True)`) so the UI stays
responsive during long turns — Ruby's direct analog (`Thread.new`).

**Interrupting a running turn (`Esc`) works differently from Ruby.** Ruby's `Thread#raise` can
inject an exception into a running thread at any point, including mid-HTTP-call — Python threads
have no equivalent. Instead, `Agent` accepts an optional `interrupt: threading.Event`; `Tui` sets
the event on `Esc`, and `Agent.run()`'s loop checks it once per iteration boundary before starting
the next model round-trip, raising `KeyboardInterrupt` to unwind. In practice this means an
interrupt takes effect at the next iteration boundary rather than instantly mid-call — a small,
deliberate behavior difference from Ruby's (unsafe but instant) approach.

### `boukensha.repl` — new `tui=` keyword

```python
boukensha.repl(tui=True)   # default -- launches the textual TUI
boukensha.repl(tui=False)  # falls back to the plain terminal REPL
```

There's no Python equivalent of Ruby's global `boukensha` executable or its `--no-tui` CLI flag
(this port has never had a `09_global_executable` step — see
`docs/plans/floating_artifacts/boukensharc.md`), so `tui=False` is the direct way to get the plain
REPL when embedding this in your own script.

### `Repl` refactored for composability

`Repl` no longer hard-codes `print`/`input`. It exposes:

| Member | Purpose |
|--------|---------|
| `on_output(callback)` | Route all REPL output through a callback instead of stdout |
| `handle_command(line)` | Process a slash command; returns `"quit"`, `"command"`, or `None` |
| `run_turn(line, *, interrupt=None)` | Run one agent turn and route the result through `on_output` |
| `logger`, `context`, `model`, `version` | Now public readers (were private) |

`Tui` drives `Repl` through exactly this surface rather than through `Repl.start()`'s own
`input()` loop.

### `Logger.subscribe`

```python
logger.subscribe(lambda event: ...)
```

Every structured log event (`iteration`, `tool_call`, `tool_result`, `response`, etc.) is
broadcast to all registered subscribers in addition to being written to the JSONL file. This
already existed in `python/10_standard_tool_library` ahead of schedule; `Tui` is what actually
uses it now, to update the live progress line in real time without polling.

## Run it

```sh
week1_baseline/bin/python/11_tui
```

This launches the textual TUI by default (`examples/example.py` calls `boukensha.repl(...)`,
which defaults to `tui=True`). It connects to `mud_manager_mcp` using credentials from
`~/.boukensha/settings.yaml`'s `mud:` block, same as step 10's demo — set `BOUKENSHA_DIR` to point
at a different config directory.

To run the plain REPL instead (no `textual` rendering, just stdin/stdout), call
`boukensha.repl(tui=False, ...)` directly from your own script — there's no launcher flag for it
since, unlike Ruby, there's no global executable/CLI layer to parse one.

## Scope: Ruby's packaging additions are not ported

Ruby's `charm`/`bubbletea` native-gem dependency, its `patches/bubbletea/` C-extension patch
workflow, and the `--no-tui` global-executable CLI flag are all Ruby-specific packaging concerns
with no Python analog — this port installs `textual` the normal way (`uv add textual`, a
pure-Python-distributed wheel) and keeps using the `week1_baseline/bin/python/<step>` launcher
convention established since `00_config`.

## Technical Considerations

Observations we don't want to fix right now, just to preserve for future steps:

- There's not yet enough tool coverage to accomplish every task efficiently — several agent goals
  would still map down to the same handful of primitives (`run_command` as an escape hatch for
  anything `file_system_mcp` doesn't cover directly).
- `Tui`'s interrupt is cooperative (checked once per agent iteration), not instant — a turn stuck
  mid-single-iteration (e.g. a slow API call or a long-running tool call) won't respond to `Esc`
  until that call returns.
