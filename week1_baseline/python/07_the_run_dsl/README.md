# 07 · The `boukensha.run` DSL (Python port)

Python port of `week1_baseline/ruby/07_the_run_dsl`. Behavior matches the
Ruby implementation described in `../../ruby/07_the_run_dsl/README.md`,
correcting a few places where that README doesn't match its own code (see
"Considerations" below); this file documents the actual behavior in Python
terms.

## What This Step Adds

A single top-level entry point: `boukensha.run`.

Every previous step required manually creating and wiring together a
`Context`, `Registry`, backend, `PromptBuilder`, `Client`, `Logger`, and
`Agent`. This step hides all of that behind one function call plus a small
callback for registering tools.

## The New Primitive

### `boukensha.RunDSL`

A tiny host object passed into your `configure` callback. It exposes exactly
one method, `tool(...)`, which forwards straight to the underlying
`Registry.tool`. This keeps the DSL surface intentionally small.

### `boukensha.run`

```python
def run(
    *,
    task: str,
    system: str | None = None,
    model: str | None = None,
    backend: str | None = None,
    api_key: str | None = None,
    ollama_host: str = "http://localhost:11434",
    log: str | Path | None = None,
    max_output_tokens: int | None = None,
    configure: Callable[[RunDSL], None] | None = None,
) -> str: ...
```

| Option | Default | Description |
|---|---|---|
| `task` | *(required)* | The user message handed to the agent |
| `system` | task's configured system prompt | System prompt |
| `model` | task's configured model | Model name |
| `backend` | task's configured provider | `"anthropic"`, `"openai"`, `"gemini"`, `"ollama"`, or `"ollama_cloud"` |
| `api_key` | `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`GEMINI_API_KEY`/`OLLAMA_API_KEY` (per backend; not needed for `"ollama"`) | API key for the chosen backend |
| `ollama_host` | `"http://localhost:11434"` | Ollama base URL |
| `log` | `None` | Optional session log path override; by default logs go to `.boukensha/sessions/<session-id>.jsonl` |
| `max_output_tokens` | task's configured value (1024) | Max tokens per API response |
| `configure` | `None` | A callback invoked with a `RunDSL` instance, for registering tools |

There is no `token_budget`/context-window parameter — `boukensha.run` only
controls per-reply output size (`max_output_tokens`), not overall context
size.

`model`/`backend`/`system`/`max_output_tokens` all default to whatever the
`player` task's settings resolve to (`tasks.player` in `.boukensha/settings.yaml`
— see prior steps' READMEs for that resolution order); passing any of them
explicitly overrides the task-configured value for that one call.

## Before and After

**Step 6 — manual plumbing:**

```python
config = Config()
player_settings = config.tasks("player")
system_prompt = Player.system_prompt(
    player_settings, user_prompts_dir=config.user_prompts_dir, default_prompts_dir=Config.PROMPTS_DIR
)
ctx = Context(task=Player, system=system_prompt)
registry = Registry(ctx)
backend = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], model="claude-haiku-4-5")
builder = PromptBuilder(ctx, backend)
client = Client(builder)
logger = Logger()
agent = Agent(context=ctx, registry=registry, builder=builder, client=client, logger=logger, task_settings=player_settings)

registry.tool("read_file", description="Read a file", parameters={"path": {"type": "string"}}, block=lambda *, path: Path(path).read_text())

ctx.add_message("user", "Read lib/boukensha.rb")
result = agent.run()
```

**Step 7 — just describe what you want:**

```python
import boukensha

def configure(dsl):
    dsl.tool("read_file", description="Read a file", parameters={"path": {"type": "string"}}, block=lambda *, path: Path(path).read_text())

result = boukensha.run(task="Read boukensha/__init__.py", configure=configure)
```

## Run Example

```bash
./bin/python/07_the_run_dsl
```

The example registers two tools (`read_file`, `list_directory`) and asks the
agent to read `README.md` and summarise this framework. Real captured output
from running the example against a live Anthropic key:

```
=== BOUKENSHA Step 7: The Boukensha.run DSL ===

Config: #<Boukensha::Config dir=<repo>/.boukensha tasks=player>

=== FINAL RESPONSE ===
## Summary of the MUD Player Assistant Framework

Based on the README.md, here's what this framework can do:
...
```

(Full response text omitted here for brevity — see `.boukensha/sessions/<session-id>.jsonl`
for the complete transcript of any given run.) `Config` is resolved twice on
purpose here — once by `examples/example.py` for the banner, and again
internally by `boukensha.run` — the same harmless duplication this port has
had since `06_the_logger`'s `Logger` directory resolution.

## Considerations

**The Ruby README for this step is stale in a few places** — its H1 says
"Step 6" (an off-by-one in the Ruby source itself); its options table lists
`token_budget:`/`max_tokens:` keywords that don't exist on the actual
`Boukensha.run` method; and it lists only `:anthropic`/`:ollama` as supported
backends when the real code supports all five this port already has. This
README documents the real signature and backend list instead of
transcribing that table.

**`backend`/`model` resolve from task settings, not from the block.** The
`configure` callback only registers tools — it has no way to influence which
backend or model gets used. That's set entirely by `boukensha.run`'s own
keyword arguments (or their task-config-derived defaults), evaluated before
`configure` ever runs.

**Two pieces of dead code reappear this step** that `06_the_logger` had
just deleted: the four MUD-connection `Config` accessors (`mud_host`,
`mud_port`, `mud_username`, `mud_password`) and `LoopError`. Neither is used
anywhere in this step either — ported faithfully as unused API surface
rather than re-deleted, matching how this port has always treated Ruby's own
quirks and dead code (see `Logger.close`, never called, from `06_the_logger`).

**`Logger` gains two more unused additions**: `turn(n=...)` (a phase the
agent loop never actually logs — it only ever calls `turn_end`) and
`subscribe(callback)` (lets external code observe every logged event as it's
written; nothing in this step calls it). Both are ported as real, working,
but currently-unused API surface.

**Tool dispatch exceptions still don't crash the loop, and the assistant
message must still be stored before the tool result** — both unchanged
behaviors from `06_the_logger`.

## Tests

```bash
cd week1_baseline/python/07_the_run_dsl
make test    # uv run pytest -v
make lint    # uv run isort --check-only / ruff check / ty check
```

`tests/test_run_dsl.py` covers `RunDSL.tool` forwarding to the registry.
`tests/test_boukensha_run.py` covers `boukensha.run`'s backend selection
(including the `ValueError` for an unrecognized one), per-backend API-key
env-var resolution, `configure` being invoked with a real `RunDSL`, and
`logger.close()` firing via `finally` even when `Agent.run()` raises.
`tests/test_logger.py` covers the new `turn`/`subscribe` methods.
`tests/test_config.py` re-adds the MUD-accessor tests `06_the_logger` had
removed, matching Ruby's own reintroduction of those accessors this step.
