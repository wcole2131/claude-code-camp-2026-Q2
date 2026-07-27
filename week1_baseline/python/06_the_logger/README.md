# 06 · The Logger (Python port)

Python port of `week1_baseline/ruby/06_the_logger`. Behavior matches the
Ruby implementation described in `../../ruby/06_the_logger/README.md`; this
file documents the same design in Python terms.

`boukensha.Logger` records each agent run as structured JSON Lines. It is a
file logger, not user-facing display output — the console `print()` calls
from `05_agent_loop`'s loop (`[iteration N/max]`, `tool call → ...`,
`tool result → ...`) are gone, replaced entirely by structured log lines.

## Session Logs

Each `Logger` instance creates a session id and writes one log file for that
session:

```text
.boukensha/sessions/<session-id>.jsonl
```

Every line is a complete JSON object with `session_id`, `at`, and `phase`
fields, plus phase-specific data. This keeps logs grep/tail friendly and
machine readable.

```json
{"phase":"session_start","session_id":"20260528T143011Z-a1b2c3d4","at":"2026-05-28T10:30:11-04:00"}
{"phase":"iteration","n":1,"max":25,"session_id":"20260528T143011Z-a1b2c3d4","at":"2026-05-28T10:30:11-04:00"}
```

Model response lines include the active task, provider, model, normalized
token counts, and estimated USD cost when the backend has token pricing
data:

```json
{"phase":"response","task":"player","provider":"anthropic","model":"claude-haiku-4-5","input_tokens":1000,"output_tokens":100,"cost_usd":0.0015}
```

## `boukensha.Logger`

A plain object with one method per phase:

| Method | Phase | Logs |
|---|---|---|
| `iteration(n=..., max=...)` | `iteration` | loop counter |
| `limit_reached(kind=..., n=..., max=...)` | `limit_reached` | the iteration ceiling was hit, before wind-down |
| `turn_end(reason=..., iterations=..., tokens=None)` | `turn_end` | why the turn ended and how many iterations it took |
| `prompt(messages=..., tools=...)` | `prompt` | message count/summaries, tool count/names |
| `tool_call(name=..., args=...)` | `tool_call` | tool name and arguments |
| `tool_result(name=..., result=..., ok=True, error=None)` | `tool_result` | the full, untruncated tool result |
| `response(text=..., usage=None, stop_reason=None, task=None, backend=None)` | `response` | response text, token usage, task/provider/model, estimated cost |
| `raw(data=...)` | `raw` | raw provider response, only when `boukensha.debug()` has been called |

## Task Configuration

Step 6 uses the same task-based settings shape as `05_agent_loop`:

```yaml
tasks:
  player:
    provider: anthropic
    model: claude-haiku-4-5
    prompt_override:
      system: true
```

When `prompt_override.system` is true, the player task reads
`.boukensha/prompts/player/system.md`. Otherwise it falls back to this
step's shipped `prompts/system.md`.

Default usage:

```python
logger = Logger()
agent = Agent(context=ctx, registry=registry, builder=builder, client=client, logger=logger)
```

You can also provide a session id or override the destination directory:

```python
Logger(session_id="manual-session")
Logger(dir="/tmp/boukensha-sessions")
```

For compatibility, `log=` still accepts an explicit file path, but normal
iteration usage should write under `.boukensha/sessions`.

## Debug Events

Call `boukensha.debug()` before running the agent to include raw provider
responses:

```python
import boukensha

boukensha.debug()
```

## Global State

Ruby hangs a small amount of module-level state directly off the
`Boukensha` module (`Boukensha.config`, `.debug!`/`.debug?`,
`.quiet!`/`.loud!`/`.quiet?`). The Python port puts the equivalent functions
directly in `boukensha/__init__.py`, the closest Python has to a package's
"top" namespace:

| Ruby | Python |
|---|---|
| `Boukensha.config` (memoized) | `boukensha.get_config()` — renamed from a literal `config()` to avoid colliding with the `boukensha.config` *submodule* |
| `Boukensha.debug!` / `.debug?` | `boukensha.debug()` / `boukensha.is_debug()` |
| `Boukensha.quiet!` / `.loud!` / `.quiet?` | `boukensha.quiet()` / `boukensha.loud()` / `boukensha.is_quiet()` |

`boukensha/logger.py` reads this state via `import boukensha` (the whole
module) rather than `from boukensha import get_config, is_debug` — the
latter would fail with a circular-import error, since `boukensha/__init__.py`
imports `Logger` before it defines these functions. Accessing them as
`boukensha.get_config()`/`boukensha.is_debug()` inside method bodies works
because they only need to exist by the time those methods are actually
*called*, long after both modules have finished importing.

## What the Loop Looks Like

Running the example writes to `.boukensha/sessions/<session-id>.jsonl`
instead of printing per-iteration/tool-call output to the console. The
console output is now just the surrounding banner:

```
=== BOUKENSHA Step 6: The Logger ===

Config: #<Boukensha::Config dir=<repo>/.boukensha tasks=player>
Provider: anthropic
Model: claude-haiku-4-5
Max iterations: 25
Max output tokens: 1024

=== FINAL RESPONSE ===
This is the Agent Loop step of the BOUKENSHA framework...
```

## Considerations

**Tool dispatch exceptions no longer crash the loop.** `Agent._handle_tool_calls`
now wraps `registry.dispatch(...)` in `except Exception as e:`, turning a
raised exception (e.g. `UnknownToolError` for a hallucinated tool name) into
an `"ERROR: {type(e).__name__}: {e}"` result string and a
`tool_result(..., ok=False, error=...)` log line, instead of propagating and
killing `Agent.run`.

**The assistant message must be stored before the tool result.** Unchanged
from `05_agent_loop` — the Anthropic API requires the assistant's tool_use
block to appear in the message history before its corresponding tool_result.

**`provider_name` derives its value from the backend's class name, not the
configured provider string** — and for OpenAI specifically, those two don't
match. `type(backend).__name__` for the OpenAI backend is `"OpenAI"`, and
the snake-casing regex used to derive a provider name from it produces
`"open_ai"` (an underscore gets inserted between the lowercase `n` and the
uppercase `A`), even though `tasks.player.provider` in `settings.yaml` spells
it `"openai"`. This is a quirk in the Ruby source itself, reproduced here
faithfully rather than "corrected" — the OpenAI backend's `response` log
lines will say `"provider": "open_ai"`.

## Run Example

```bash
./week1_baseline/bin/python/06_the_logger
```

Or directly:

```bash
cd week1_baseline/python/06_the_logger
uv run python examples/example.py
```

Requires a real API key for the configured provider in `.boukensha/.env`.
`Logger`'s field shapes and `Agent`'s logger-call-sites (including the new
tool-exception-handling behavior) are covered by `tests/test_logger.py` and
`tests/test_agent.py` against mocked/temp-directory loggers, so you don't
need a real API key to verify that logic is correct.

## Tests

```bash
cd week1_baseline/python/06_the_logger
make test    # uv run pytest -v
make lint    # uv run isort --check-only / ruff check / ty check
```
