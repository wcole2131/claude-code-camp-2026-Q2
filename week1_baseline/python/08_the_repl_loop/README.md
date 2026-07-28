# 08 · The REPL Loop (Python port)

Python port of `week1_baseline/ruby/08_the_repl_loop`. Behavior matches the
Ruby implementation described in `../../ruby/08_the_repl_loop/README.md`,
correcting several places where that README doesn't match its own code (see
"Considerations" below); this file documents the actual behavior in Python
terms.

## What This Step Adds

| | Step 7 | Step 8 |
|---|---|---|
| Entry point | `boukensha.run(task="…")` | `boukensha.repl(...)` |
| Turns | one | many |
| History | discarded | accumulates across turns |
| User interaction | none | stdin prompt |

## The New Primitive

### `boukensha.Repl`

The interactive session loop. Built-in commands:

| Command | Effect |
|---|---|
| `/quiet` | Suppress logging output |
| `/loud` | Re-enable logging output |
| `/clear` | Wipe conversation history (tools stay registered) |
| `/help` | Print the command list |
| `/exit` / `/quit` | Leave the REPL |
| Ctrl-D | EOF — leave the REPL |
| Ctrl-C | Interrupt — leave the REPL gracefully |

### `boukensha.repl`

Same signature as `boukensha.run`, minus `task`. Register tools via a
`configure` callback (the same pattern `boukensha.run` established); then the
REPL loop takes over.

```python
import boukensha

def configure(dsl):
    dsl.tool(
        "read_file",
        description="Read a file from disk",
        parameters={"path": {"type": "string", "description": "File path"}},
        block=lambda *, path: open(path).read(),
    )

boukensha.repl(model="claude-haiku-4-5", configure=configure)
```

## Changes From Step 7

### `Context.clear_messages()`
Wipes `messages` while keeping tools registered. Used by the REPL's `/clear`
command. (Ruby names this `clear_messages!`; the bang suffix has no Python
equivalent, so the port drops it, consistent with every other mutating method
in this codebase.)

### `Agent.run`/`_wrap_up` — persist the final reply
Before this step, the agent returned its final text without adding it to
`Context`. That was harmless for one-shot `boukensha.run` calls (the whole
context is thrown away afterward), but a REPL needs the full transcript so
later turns can see the agent's own prior replies. All three places `Agent`
returns final text now call `context.add_message("assistant", text)` first —
the normal completion path, the wind-down success path, and the wind-down
`ApiError` fallback path.

### `Config`'s directory resolution gains a project-local tier
Resolution order is now: `BOUKENSHA_DIR` env var, then `./.boukensha` in the
current working directory (if it exists), then `~/.boukensha`.

### `Client` reports 401s specifically
A `401` response now raises `ApiError("authentication failed (401) — check
your API key")` instead of the generic "API request failed" message, so a bad
or missing key is obvious mid-REPL-session rather than looking like a
transient failure.

## Running It

```bash
./bin/python/08_the_repl_loop
```

Real captured output (piped input, live Anthropic key, model
`claude-haiku-4-5`):

```
Config: #<Boukensha::Config dir=<repo>/.boukensha tasks=player>


╔══════════════════════════════════════╗
║  BOUKENSHA MUD Assistant (v0.8.0)    ║
╚══════════════════════════════════════╝
  config:    <repo>/.boukensha
  provider:  anthropic (claude-haiku-4-5)  ✓ API key set

  /quiet or /loud   toggle logging
  /clear           reset conversation history
  /exit or /quit    leave the REPL

boukensha> list the files in this directory
Here are the files and directories in the current directory:

1. **Makefile** - Build/automation file
2. **README.md** - Project documentation
...
boukensha> now read README.md and summarize the first section
## Summary of the First Section
...
boukensha> /clear
(conversation history cleared)
boukensha> what was the first file I asked you about?
I don't have any record of previous conversations with you. Each conversation
starts fresh for me, and I don't have access to chat history or past
interactions.
...
boukensha> /exit
Goodbye.
```

(Response text truncated above for brevity — see `.boukensha/sessions/<session-id>.jsonl`
for the complete transcript.) The second question demonstrates persistent
history: the agent answers using the accumulated transcript, not just the
last message. After `/clear`, the same question about "the first file" gets a
correct "I don't have that" answer, confirming history was actually wiped.

`examples/example.py`'s `configure` callback registers `read_file` and
`list_directory`, rooted at `python/07_the_run_dsl` (a directory with real
source files to browse) rather than this step's own directory.

## Considerations

**The Ruby README for this step is stale/inaccurate in several places** —
verified against the actual code and the live run above, not transcribed at
face value:

- Its "Running it" section says `cd 07_the_repl_loop` (wrong step number) and
  `ruby examples/step7.rb` (no such file exists — the real launcher runs
  `examples/example.rb`).
- Its example banner (`BOUKENSHA REPL — MUD assistant` / `type a command and
  press Enter`) doesn't match the real banner, which is a box titled
  `BOUKENSHA MUD Assistant (v0.8.0)` followed by `config:`/`provider:` lines
  and a command-hint block, as captured above.
- Its description of `Logger#turn` printing a `╔══ turn N ══╗` header to the
  terminal isn't real — `Logger.turn` only ever writes a `phase: "turn"` line
  to the JSONL log file (and to any `subscribe`rs, of which there are none by
  default). It does get called once per turn now (unlike step 7, where it was
  dead code), but it produces no visible terminal output.

**`/quiet` and `/loud` currently do nothing observable.** They flip a
module-level flag (`boukensha.quiet()`/`boukensha.loud()`), but nothing in
`Logger` ever reads that flag except one `debug()`-gated log line unrelated
to these two commands. The Ruby README itself flags this as an open question
("we need to determine if quiet and loud are legacy logging or if they
actually provide detail logs") — this port reproduces the same inert
behavior rather than inventing logic Ruby doesn't have.

**A new `Agent` is really constructed on every REPL turn**, not once for the
whole session. This is cheap (`Agent.__init__` does no I/O) and matches
Ruby's own acknowledged-but-unresolved behavior ("It seems like we should
initialize only once") — ported faithfully, not "fixed."

**Tool dispatch exceptions still don't crash the loop, and the assistant
message must still be stored before the tool result** — both unchanged
behaviors from `06_the_logger`/`07_the_run_dsl`.

**Ctrl-C (`KeyboardInterrupt`) is only caught around the whole REPL session**,
in `boukensha.repl()`, not inside `Repl.start()` itself — matching Ruby's
`rescue Interrupt` placement around the whole `Boukensha.repl` method body.
An interrupt mid-turn ends the session (prints "Interrupted.") rather than
just cancelling that one turn.

## Tests

```bash
cd week1_baseline/python/08_the_repl_loop
make test    # uv run pytest -v
make lint    # uv run isort --check-only / ruff check / ty check
```

`tests/test_repl.py` covers `Repl`'s built-in commands (`/help`, `/quiet`,
`/loud`, `/clear`, `/exit`/`/quit`), EOF handling, ordinary-line dispatch to a
mocked `Agent`, `LoopError`/`ApiError` being caught and printed without
crashing the loop, and the banner's API-key/config-dir rendering.
`tests/test_boukensha_repl.py` covers `boukensha.repl`'s backend/API-key
resolution, `configure` invocation, and `logger.close()` firing via `finally`
even when `Repl.start()` raises or is interrupted — mirroring
`tests/test_boukensha_run.py`'s coverage of `boukensha.run`.
`tests/test_context.py` covers `clear_messages`. `tests/test_agent.py` covers
the three new `context.add_message("assistant", ...)` call sites.
`tests/test_client.py` covers the 401-specific error message.
`tests/test_config.py` covers the new `./.boukensha` cwd-resolution tier,
including that the `BOUKENSHA_DIR` env var still wins over it.
