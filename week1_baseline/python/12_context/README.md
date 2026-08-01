# 12 · Context Management (Python port)

Python port of `week1_baseline/ruby/12_context`. When you call an LLM directly you are
responsible for the context window — there is no auto-compacting. This step adds proper token
tracking, visual warnings, and automatic compaction so the agent never silently blows past the
limit. It also removes the `Tasks::Player`/`tasks/` abstraction from earlier steps: agent settings
(system prompt, model, provider, iteration/token/output limits) now come straight off `Config`
instead of being resolved through a task class.

## Tool library (inherited from step 10)

**Boukensha ships no tool implementations of its own.** Every capability — filesystem, shell,
MUD — lives outside the framework as its own standalone MCP server, and the agent gets its entire
tool surface by connecting to whichever of those servers you point it at. Unchanged from step 10;
see `docs/plans/mud_manager/mcp_mud_plan.md` for the design rationale, and step 10's own history in
`docs/plans/python_port/10_standard_tools.md` for how `boukensha.mcp.MCPClient` and the three
bundled servers (`file_system_mcp`, `shell_mcp`, `mud_manager_mcp`) work. `Boukensha::MCP::Server`
(Ruby's generic server-side JSON-RPC helper, new in this step's Ruby source) has **no Python
counterpart** — Python only ever connects to these servers as a client, spawning the Ruby processes
as subprocesses; nothing in this port hosts an MCP server itself.

## Terminal UI (inherited from step 11)

Unchanged from step 11 except for the context-usage display described below; see
`docs/plans/python_port/11_tui.md` for the full `Tui`/`Repl` composability design (`on_output`,
`handle_command`, `run_turn`, cooperative-cancellation via `threading.Event` in place of Ruby's
unsafe `Thread#raise`). The four-zone layout, keybindings, and `boukensha.repl(tui=...)` keyword
are all as before.

## What's new in this step

### Accurate context tracking

`Context` now maintains two distinct token counts:

| Attribute | What it measures |
|-----------|-----------------|
| `context_window` | The model's maximum input token capacity (default 200,000 for Anthropic) |
| `current_tokens` | Tokens actually used in the most recent API call (`usage["input_tokens"]` from the response) |

Previously the old `Tasks`-derived `max_output_tokens` (8,192-ish) was displayed as the limit —
that was the *output* ceiling, not the context window — and a cumulative session token sum was
shown as usage, which grew without bound even after `/clear`. Both are fixed: `Agent` updates
`current_tokens` after every API response (including mid-turn tool-use calls), so the display
always reflects what the next call will actually send.

### Context colour coding

The progress and status lines now colour the context indicator based on how full the window is:

| Usage | Colour | Meaning |
|-------|--------|---------|
| < 70% | Grey | Normal |
| 70–84% | Yellow | Approaching limit |
| ≥ 85% | Red | Compaction imminent |

A `⚠` symbol also appears in the status bar at 85%+.

### Auto-compaction

At the start of each agent turn, if `current_tokens / context_window >= 0.85` (configurable via
`compaction_threshold`), `Agent` automatically compacts the context before making any API call:

```
[context compacted — 12 messages dropped to free space]
```

Compaction drops the oldest 40% of messages (keeping at least 2) and resets `current_tokens` to 0.
The next API call after compaction reports the true new size.

### `Context.compact_messages()`

```python
dropped = context.compact_messages(target_fraction=0.60)
# => 12  (number of messages dropped)
```

### `/compact` command

Manual compaction from the REPL or TUI:

```
boukensha> /compact
(compacted context — 12 messages dropped)
```

### `Logger.compaction` event

```json
{"phase": "compaction", "before": 172000, "dropped": 12, "context_window": 200000}
```

Emitted whenever auto- or manual compaction runs. `Tui` subscribes to this event to display the
compaction notice in the conversation view.

### `max_turn_tokens` — a second, independent ceiling

Alongside the existing iteration ceiling, `Agent` now also tracks a *per-turn spend budget*
(`Context.turn_tokens`, the sum of every API call's input+output tokens made during the current
turn — distinct from `current_tokens`, which tracks window pressure, not cumulative spend). When
`turn_tokens` reaches `max_turn_tokens` (default 60,000, configurable via
`Config.agent_max_turn_tokens`, 0 disables it), `Agent` stops starting new iterations and makes the
same one-shot wind-down call it already made for the iteration ceiling — just tagged
`kind="max_tokens"` instead of `kind="max_iterations"`.

### Reasoning content blocks

Every backend now normalizes provider-specific "thinking" output into a common `{"type":
"reasoning", "text": ..., "signature": ..., "redacted": ...}` content block (see
`boukensha/backends/base.py`'s docstring for the full contract): Anthropic's
`thinking`/`redacted_thinking`, Gemini's `thought` parts (with `thoughtSignature`), and
Ollama/OllamaCloud's `thinking` string. `Agent` emits one `logger.reasoning(...)` event per
non-empty (or redacted) reasoning block. None of the backends currently *request* extended
thinking by default (Anthropic sends no `thinking` config; OpenAI explicitly sends
`reasoning: {"effort": "none"}`; Gemini and Ollama explicitly disable it) — this is forward-looking
normalization for when a caller does enable it, not a new default behavior.

### OpenAI backend: full switch to the Responses API

`gpt-5.x` rejects `reasoning_effort` + tools on `/v1/chat/completions` ("Please use
`/v1/responses`"), so `boukensha/backends/openai.py` now targets `/v1/responses` instead of chat
completions. That changes more than the URL: messages become `input` items, the system prompt
becomes a top-level `instructions` string, tool definitions are flat (no `function:` wrapper), and
tool results round-trip via `function_call_output` items matched by `call_id` rather than a
`{"role": "tool"}` message.

### Tool preamble text now logged separately from the response placeholder

When the model calls a tool with accompanying preamble text (e.g. "Let me check that."), the
preamble is now logged as its own `logger.plan(text=...)` event; the `logger.response(...)` event
for a tool-use turn always carries the synthesized `"(tool use — N calls)"` placeholder, regardless
of whether there was preamble text. Previously the preamble text, when present, replaced the
placeholder in the single `response` event.

### `boukensha.run` / `boukensha.repl` — `context_window:` keyword

```python
boukensha.repl(context_window=128_000)  # for a smaller model
```

Defaults to a lookup in `boukensha.models.context_window(model)` — a small static model→window
table (currently just the three Anthropic models, all 200,000), independent of each backend's own
`MODELS` table (which also carries cost/usage-unit data). An unrecognized model id falls back to a
conservative 32,000 rather than assuming a large window.

### `Config` no longer resolves settings through a `Tasks::Player`-equivalent class

`boukensha/tasks/` (the `Base`/`Player` classes from steps 00–11) is removed entirely. `Config` now
exposes `provider_type`, `model`, `system_prompt`, and `agent_max_iterations` /
`agent_max_output_tokens` / `agent_max_turn_tokens` / `agent_compaction_threshold` directly —
reading the same `settings.yaml` key paths (`tasks.player.provider`, `tasks.player.model`,
`tasks.player.prompt_override.system`, `agent.*`) the old task-class lookup used, just without the
class indirection.

## Run it

```sh
week1_baseline/bin/python/12_context
```

Launches the textual TUI by default (`examples/example.py` calls `boukensha.repl(...)`, which
defaults to `tui=True`). It connects to `mud_manager_mcp` using credentials from
`~/.boukensha/settings.yaml`'s `mud:` block, same as prior steps — set `BOUKENSHA_DIR` to point at
a different config directory.

Verified end-to-end against a real MUD server and the live Anthropic API (`boukensha.run(...)`,
one-shot mode) while porting this step; the JSONL log confirms the new fields land correctly:

```json
{"phase": "session_start", "max_iterations": 25, "max_turn_tokens": 60000, "max_output_tokens": 1024, "context_window": 200000, "model": "claude-haiku-4-5", "provider": "anthropic"}
{"phase": "prompt", "context_window": 200000, "message_count": 1, ...}
{"phase": "response", "usage": {"input_tokens": 3198, "output_tokens": 54, ...}, "stop_reason": "tool_use"}
{"phase": "turn_end", "reason": "completed", "iterations": 2, "tokens": 6717}
```

To run the plain REPL instead (no `textual` rendering, just stdin/stdout), call
`boukensha.repl(tui=False, ...)` directly from your own script.

## Scope: Ruby's packaging additions are not ported

`Boukensha::MCP::Server` (`lib/boukensha/mcp/server.rb`, new in Ruby this step) is the generic
server-side helper the three standalone Ruby MCP server repos (`mud_manager_mcp`, `file_system_mcp`,
`shell_mcp`) use internally. It has no Python analogue and isn't ported: this project has never had
a Python-hosted MCP server, only a Python *client* (`boukensha/mcp.py`) that spawns the Ruby
servers as subprocesses (see step 10's plan). Ruby's `tasks/base.rb`/`tasks/player.rb` removal has
no packaging equivalent to skip — that class hierarchy is simply gone from both languages now.

## Technical Considerations

Observations we don't want to fix right now, just to preserve for future steps:

- `Config.system_override` (`dig("system", "override")`) is ported for parity with Ruby's
  `system_override?`, but neither language's codebase actually calls it anywhere — it's dead code
  in both, not a Python-porting gap.
- Unrecognized model ids default to a 32,000-token context window via `boukensha.models`, which is
  wrong for e.g. `gpt-5.5` (1,000,000) — this mirrors Ruby's own minimal 3-entry table exactly
  rather than "fixing" it with a fuller table Ruby doesn't have either.
- `Tui`'s interrupt is still cooperative (checked once per agent iteration), not instant — a turn
  stuck mid-single-iteration (e.g. a slow API call or a long-running tool call) won't respond to
  `Esc` until that call returns. Unaffected by this step.
