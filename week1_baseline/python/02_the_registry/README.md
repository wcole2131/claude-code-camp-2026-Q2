# 02 · The Tool Registry (Python port)

Python port of `week1_baseline/ruby/02_the_registry`. Behavior matches the
Ruby implementation described in `../../ruby/02_the_registry/README.md`;
this file documents the same design in Python terms.

The Tool Registry is how BOUKENSHA manages what capabilities the agent can
use.

It has two jobs:
  1. storing tools
  2. dispatching tools when asked

This step starts from the `01_struct_skeleton` port (same `Config`/
`Context`/`Tool`/`Message`, copied and carried forward per the Ruby
original's self-contained-bundle-per-step structure) and adds a `Registry`
on top.

## New Files

| File | Description |
|---|---|
| `boukensha/registry.py` | The `Registry` class — registers tools and dispatches calls |
| `boukensha/errors.py` | BOUKENSHA-specific error classes |

## How It Works

The agent NEVER calls a tool directly.
It emits a structured request (name and args) and the Registry looks up the
tool and runs it.

```
Agent:  "Hey registry call move with direction='north'"
Registry: "looking up "move" in the tool table"
Registry: "Found it now calling the block with the provided args"
Registry: "Here's the result"
Agent: "Thanks buddy"
Registry: "Thats why you pay me the big tokens"
```

## `boukensha.Registry`

| Method | Description |
|---|---|
| `tool(name, *, description, parameters=None, block)` | Registers a new tool on the context |
| `dispatch(name, args=None)` | Looks up a tool by name and calls it with the provided args |

## `boukensha.UnknownToolError`

Raised when `dispatch` is called with a name that has no registered tool.
A harness needs explicit error boundaries — an unrecognised tool name
should never silently fail.

**Example:**
```
UnknownToolError: No tool registered as 'flee'
```

## Expected Output

```
=== BOUKENSHA Step 2: Tool Registry ===

Config:  #<Boukensha::Config dir=/home/andrew/Sites/Claude-Code-Camp/.boukensha tasks=player>
Context: #<Context task=player turns=0 tools=2>
Tools:
  #<Tool name=move description=Move the player in a direction (north, so params=['direction']>
  #<Tool name=shout description=Shout a message so everyone in the zone c params=['message']>

Dispatching 'shout' with message='dragon spotted'...
Result: DRAGON SPOTTED

Dispatching 'move' with direction='north'...
Result: You move north into a torch-lit corridor.

UnknownToolError caught: No tool registered as 'flee'
```

## Considerations

Ruby's `dispatch` converts string keys to symbol keys before calling the
block — the API returns arguments as string-keyed JSON but Ruby blocks with
keyword params expect symbols. Python's `**kwargs` call accepts plain `str`
keys directly, so this port drops that translation step entirely (the same
simplification already applied to `Config.dig`/`fetch` in the `00_config`
port) — `dispatch` just calls `tool.block(**args)`.

## Run Example

```bash
./week1_baseline/bin/python/02_the_registry
```

Or directly:

```bash
cd week1_baseline/python/02_the_registry
uv run python examples/example.py
```

## Considerations

We now register tools with the Registry but our code still has direct
registration and tools living on the context. This likely should have been
reworked.

Checking the final baseline example, we did correct the issue.
The context should have a reference to the tool[] it's currently using, and
the full table of tools registered should live on the Registry.

We'll correct this manually in a future step and we will leave things in
place.

## Tests

```bash
cd week1_baseline/python/02_the_registry
make test    # uv run pytest -v
make lint    # uv run isort --check-only / ruff check / ty check
```
