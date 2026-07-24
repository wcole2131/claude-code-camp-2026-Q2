# Python Port Plan · 02 · The Registry

Status: DRAFT — open questions below must be answered before implementation
starts.

## Goal

Turn `week1_baseline/python/02_the_registry/` (currently an exact clone of
`python/01_struct_skeleton`, still describing "Step 1: Struct Skeleton"
throughout) into a correct port of `@week1_baseline/ruby/02_the_registry/`,
by applying only the delta Ruby itself made going from `01_struct_skeleton`
to `02_the_registry` — same workflow as the `01_struct_skeleton` port
(copy prior step, apply that step's Ruby delta), which is now the standing
pattern for every `NN_*` step.

## How this plan was created

1. Read the target file (`docs/plans/python_port/02_the_registry.md`) — it
   existed but was empty.
2. Confirmed `week1_baseline/python/02_the_registry/` is a byte-identical
   copy of `week1_baseline/python/01_struct_skeleton/` (`diff -rq`, excluding
   `.venv`/`.ruff_cache`/`.pytest_cache`/`__pycache__`/`uv.lock`, returned no
   differences) — the user's own description matches: the code is there, but
   it doesn't have this step's changes yet.
3. Diffed every non-vendored file between `@week1_baseline/ruby/01_struct_skeleton/`
   and `@week1_baseline/ruby/02_the_registry/` (`diff -rq`, excluding
   `vendor/`, `.bundle/`, `Gemfile.lock`, `.gitignore`) to get the exact,
   authoritative delta: `lib/boukensha.rb`, `examples/example.rb`, and
   `README.md` changed; `lib/boukensha/registry.rb` and
   `lib/boukensha/errors.rb` are new; `lib/boukensha/config.rb`,
   `lib/boukensha/context.rb`, `lib/boukensha/tool.rb`,
   `lib/boukensha/message.rb`, `lib/boukensha/tasks/base.rb`,
   `lib/boukensha/tasks/player.rb`, and `Gemfile` are all unchanged.
4. Read every changed/new Ruby file in full:
   `@week1_baseline/ruby/02_the_registry/lib/boukensha/registry.rb`,
   `@week1_baseline/ruby/02_the_registry/lib/boukensha/errors.rb`,
   `@week1_baseline/ruby/02_the_registry/lib/boukensha.rb`,
   `@week1_baseline/ruby/02_the_registry/examples/example.rb`,
   `@week1_baseline/ruby/02_the_registry/README.md` (also re-read
   `lib/boukensha/context.rb` and `lib/boukensha/tool.rb` to confirm they're
   untouched and to pull exact `to_s` formats into the mapping table).
5. Actually ran `./week1_baseline/bin/ruby/02_the_registry` to capture real
   output (not just the README's "Expected Output" block, which contains a
   stale `budget=8192` field left over from an earlier draft — `Context` has
   no `token_budget` attribute; the real output is `task=`/`turns=`/`tools=`
   only, matching `context.rb`'s actual `to_s`).
6. Read the current Python scaffold in full to confirm what's reusable
   as-is: `boukensha/__init__.py`, `boukensha/context.py`, `boukensha/tool.py`,
   `boukensha/message.py`, `examples/example.py`, `pyproject.toml`,
   `README.md`, and the existing `tests/test_tool.py`/`tests/test_context.py`
   (to match established test style/naming for the two new test files this
   step needs).
7. Confirmed `week1_baseline/bin/python/02_the_registry` does not exist yet
   (only `bin/python/00_config` and `bin/python/01_struct_skeleton` do),
   mirroring the same gap found and filled in the `01_struct_skeleton` plan.

## Starting point (what's already in place, unchanged)

`week1_baseline/python/02_the_registry/` is currently byte-identical to
`week1_baseline/python/01_struct_skeleton/`. These files need **no changes**
because their Ruby originals are identical between the two steps:

- `boukensha/config.py`
- `boukensha/context.py`
- `boukensha/tool.py`
- `boukensha/message.py`
- `boukensha/tasks/base.py`, `boukensha/tasks/player.py`
- `tests/test_config.py`, `tests/test_context.py`, `tests/test_message.py`,
  `tests/test_tasks.py`, `tests/test_tool.py`
- `.gitignore`, `Makefile`, `.python-version`

## The exact delta (from `diff -u` between the two Ruby steps)

`@week1_baseline/ruby/01_struct_skeleton/lib/boukensha.rb` →
`@week1_baseline/ruby/02_the_registry/lib/boukensha.rb`: adds two new
`require_relative`s — `boukensha/errors`, `boukensha/registry`.

New file `@week1_baseline/ruby/02_the_registry/lib/boukensha/errors.rb`:
defines `Boukensha::UnknownToolError < StandardError`, empty body.

New file `@week1_baseline/ruby/02_the_registry/lib/boukensha/registry.rb`:
`Boukensha::Registry`, wrapping a `Context`:
- `initialize(context)` stores `@context`
- `tool(name, description:, parameters: {}, &block)` builds a `Tool.new(name.to_s, description, parameters, block)`, calls `@context.register_tool(tool)`, returns the tool
- `dispatch(name, args = {})` looks up `@context.tools[name.to_s]`, raises `UnknownToolError, "No tool registered as '#{name}'"` if missing, otherwise calls `tool.block.call(**args.transform_keys(&:to_sym))`

`@week1_baseline/ruby/01_struct_skeleton/examples/example.rb` →
`@week1_baseline/ruby/02_the_registry/examples/example.rb`: rewritten.
Still builds `Config`/`player_settings`/`system_prompt`/`Context` the same
way, but now also builds a `Registry.new(ctx)` and registers **two** tools
through it (`move` and a new `shout` tool that upcases its message) instead
of registering one tool directly on the context. Prints a `=== BOUKENSHA
Step 2: Tool Registry ===` banner, `Config:`/`Context:`/`Tools:` (iterating
`ctx.tools.each_value`), then dispatches `"shout"` and `"move"` through the
registry with string-keyed arg hashes and prints each result, then
dispatches `"flee"` (unregistered) inside a `begin/rescue
Boukensha::UnknownToolError` and prints the caught message. No more direct
`ctx.add_message` calls — this step's example doesn't seed conversation
history.

`@week1_baseline/ruby/01_struct_skeleton/README.md` →
`@week1_baseline/ruby/02_the_registry/README.md`: fully rewritten from
"The Struct Skeleton" to "The Tool Registry" — new sections: "New Files",
"How It Works", "Boukensha::Registry" (method table), "Boukensha::
UnknownToolError", "Expected Output", "Considerations" (on the
string→symbol key transform), "Run Example", and a **second** "Considerations"
section noting the design is intentionally left slightly inconsistent
(`Context` still holds the tools table directly rather than the `Registry`
owning it) and will be corrected in a later step. This duplicate-heading
oddity and the "leave it in place for now" framing are part of the source
material's pedagogy, not an authoring bug — carry it over into the Python
README rather than silently fixing it.

`Gemfile`, `lib/boukensha/config.rb`, `lib/boukensha/context.rb`,
`lib/boukensha/tool.rb`, `lib/boukensha/message.rb`,
`lib/boukensha/tasks/base.rb`, `lib/boukensha/tasks/player.rb`: unchanged,
byte-identical between the two Ruby steps.

## Delta to apply to `python/02_the_registry`

| Change | File(s) | Action |
|---|---|---|
| Add error type | `boukensha/errors.py` (new) | `class UnknownToolError(Exception): pass`, per `errors.rb` |
| Add registry | `boukensha/registry.py` (new) | port `Registry` per the mapping table below |
| Export new symbols | `boukensha/__init__.py` | add `Registry`, `UnknownToolError` to imports/`__all__`, mirroring the two new `require_relative`s in `lib/boukensha.rb` |
| Rewrite the example | `examples/example.py` | replace the `01_struct_skeleton`-style dump with the `Registry`/dispatch demo per `@week1_baseline/ruby/02_the_registry/examples/example.rb` — see script below |
| Add the launcher | `week1_baseline/bin/python/02_the_registry` (new — doesn't exist yet) | mirror `@week1_baseline/bin/python/01_struct_skeleton`'s shape (`cd .../python/02_the_registry && uv run python examples/example.py`) |
| Rewrite docs | `README.md` | currently a verbatim copy of the `01_struct_skeleton` README — replace with content adapted from `@week1_baseline/ruby/02_the_registry/README.md` (Registry/error tables, real captured output, both "Considerations" sections preserved) |
| Update package metadata | `pyproject.toml` | `description` still reads "— 01: struct skeleton" — update to "— 02: the registry" |
| Nothing to do | see "Starting point" above | already correct, Ruby originals didn't change |

## Ruby → Python behavior mapping (for `registry.py`/`errors.py`)

| Ruby | Python equivalent | Notes |
|---|---|---|
| `class UnknownToolError < StandardError; end` | `class UnknownToolError(Exception): pass` | plain exception, no custom `__init__` needed — message passed positionally at raise time, same as Ruby's `raise UnknownToolError, "..."` |
| `Registry.new(context)` / `@context` | `Registry.__init__(self, context: Context) -> None: self.context = context` | |
| `tool(name, description:, parameters: {}, &block)` | `def tool(self, name: str, *, description: str, parameters: dict[str, Any] \| None = None, block: Callable[..., Any]) -> Tool:` | `parameters` defaults to `None` → `parameters or {}` internally (avoids the Python mutable-default-arg pitfall; Ruby's `parameters: {}` doesn't have this problem since Ruby re-evaluates default literals per call) |
| `Tool.new(name.to_s, description, parameters, block)` then `@context.register_tool(tool)`, returns `tool` | `tool = Tool(name, description, parameters or {}, block); self.context.register_tool(tool); return tool` | `name.to_s` has no Python equivalent needed — `name` is already a plain `str` |
| `dispatch(name, args = {})` | `def dispatch(self, name: str, args: dict[str, Any] \| None = None) -> Any:` | `args` defaults to `None` → `{}` internally, same reasoning as `parameters` above |
| `@context.tools[name.to_s]` | `self.context.tools.get(name)` | |
| `raise UnknownToolError, "No tool registered as '#{name}'" unless tool` | `if tool is None: raise UnknownToolError(f"No tool registered as '{name}'")` | |
| `tool.block.call(**args.transform_keys(&:to_sym))` | `tool.block(**(args or {}))` | **simplification**: Ruby needs the string→symbol transform because Ruby keyword-arg blocks require symbol keys; Python's `**kwargs` call accepts plain `str` keys directly, so there's nothing to transform — same "no symbol equivalent" simplification already applied to `dig`/`fetch` in the `00_config` port |
| `do \|direction:\|` / `do \|message:\|` (keyword-only block params) | `lambda *, direction: ...` / `lambda *, message: ...` | keyword-only lambda params mirror Ruby's blocks, which only accept keyword calling here — see open question 3 |
| `e.message` (in `rescue ... => e`) | `str(e)` (in `except UnknownToolError as e:`) | |
| `ctx.tools.each_value { \|t\| puts "  #{t}" }` | `for t in ctx.tools.values(): print(f"  {t}")` | |
| `{ "message" => "dragon spotted" }` (string-keyed hash arg) | `{"message": "dragon spotted"}` | no key-type translation needed, unlike the Ruby side |

## Example script (`examples/example.py`)

Direct port of `@week1_baseline/ruby/02_the_registry/examples/example.rb`,
applying the mapping table above and keeping the `Config`/`Context`
construction identical to `01_struct_skeleton`'s (unchanged in this step):

```python
import os
from pathlib import Path

from boukensha import Config, Context, Player, Registry, UnknownToolError

repo_root = Path(__file__).resolve().parents[4]
os.environ.setdefault("BOUKENSHA_DIR", str(repo_root / ".boukensha"))

config = Config()
player_settings = config.tasks("player")
system_prompt = Player.system_prompt(
    player_settings,
    user_prompts_dir=config.user_prompts_dir,
)

ctx = Context(task=Player, system=system_prompt)
registry = Registry(ctx)

registry.tool(
    "move",
    description="Move the player in a direction (north, south, east, west, up, down)",
    parameters={"direction": {"type": "string"}},
    block=lambda *, direction: f"You move {direction} into a torch-lit corridor.",
)

registry.tool(
    "shout",
    description="Shout a message so everyone in the zone can hear it",
    parameters={"message": {"type": "string"}},
    block=lambda *, message: message.upper(),
)

print("=== BOUKENSHA Step 2: Tool Registry ===")
print()
print(f"Config:  {config}")
print(f"Context: {ctx}")
print("Tools:")
for t in ctx.tools.values():
    print(f"  {t}")
print()

print("Dispatching 'shout' with message='dragon spotted'...")
result = registry.dispatch("shout", {"message": "dragon spotted"})
print(f"Result: {result}")
print()

print("Dispatching 'move' with direction='north'...")
result = registry.dispatch("move", {"direction": "north"})
print(f"Result: {result}")
print()

try:
    registry.dispatch("flee")
except UnknownToolError as e:
    print(f"UnknownToolError caught: {e}")
```

Captured real output from `./week1_baseline/bin/ruby/02_the_registry`
(authoritative — the Ruby README's own "Expected Output" block is stale, see
step 5 above) that the Python port must match line-for-line except for the
`Config` dir path:

```
=== BOUKENSHA Step 2: Tool Registry ===

Config:  #<Boukensha::Config dir=<repo>/.boukensha tasks=player>
Context: #<Context task=player turns=0 tools=2>
Tools:
  #<Tool name=move description=Move the player in a direction (north, so params=[:direction]>
  #<Tool name=shout description=Shout a message so everyone in the zone c params=[:message]>

Dispatching 'shout' with message='dragon spotted'...
Result: DRAGON SPOTTED

Dispatching 'move' with direction='north'...
Result: You move north into a torch-lit corridor.

UnknownToolError caught: No tool registered as 'flee'
```

The Python `Tool.__str__`/`Context.__str__` already produce the same shape
(`params=[...]` uses Python list-repr instead of Ruby's `[:direction]`
symbol-array repr — that divergence already exists and was accepted in the
`01_struct_skeleton` port, not new to this step).

## Decisions carried over (no longer open)

- **Copy-forward-then-delta workflow** — settled by the `01_struct_skeleton`
  port; applied again here without re-litigating.
- **`dict.get`-only lookups, no symbol/string duality** — settled in
  `00_config`; applies again to `Registry.dispatch`'s key handling (open
  question 2 above resolves the same way).
- **Plain/mutable `@dataclass`es for `Tool`/`Message`** — settled in
  `01_struct_skeleton`; unaffected by this step (`tool.py`/`message.py`
  don't change).

## Open questions (please answer before implementation)

1. **`Registry.tool`'s block parameter** — Ruby passes the tool's callable
   implicitly via `&block` (the `do...end` after the call). Python has no
   implicit-block syntax. *Recommendation:* accept it as an explicit
   `block:` keyword argument (`registry.tool("move", description=..., parameters=..., block=lambda *, direction: ...)`), matching `Tool.block`'s field
   name and keeping the call shape a literal argument list rather than
   introducing decorator sugar (`@registry.tool(...)`) that Ruby's shape
   doesn't have.
2. **`dispatch`'s key handling** — confirmed above as a straight
   simplification (`tool.block(**(args or {}))`), no symbol transform
   needed. Flagging only for explicit sign-off since it's a behavioral
   simplification, not a literal port.
3. **Keyword-only tool blocks** — should the ported example's lambdas use
   `lambda *, direction: ...` (keyword-only, matching Ruby's `do |direction:|`
   exactly) or plain `lambda direction: ...` (looser — works identically
   here since `dispatch` always calls via `**args`, but wouldn't reject a
   stray positional call the way Ruby's block would)? *Recommendation:*
   keyword-only, for fidelity to the constraint Ruby actually enforces.
4. **Automated tests** — following the precedent set in `00_config` and
   `01_struct_skeleton`, should this step add `tests/test_registry.py`
   (tool registration returns/stores the `Tool`, `dispatch` calls the block
   with the right kwargs, `dispatch` on an unknown name raises
   `UnknownToolError` with the exact message) and `tests/test_errors.py`
   (or fold that one assertion into `test_registry.py` — it's a single
   trivial exception class)? *Recommendation:* yes, `tests/test_registry.py`
   covering both; skip a separate `test_errors.py` since `UnknownToolError`
   has no behavior of its own to test beyond what `test_registry.py`
   already exercises via `dispatch`.
5. **Ruby README's broken `Run Example` path** — the Ruby README says
   `./week1_baseline/bin/01_the_registry` (missing the `python`/`ruby`
   language segment and using the old `01_` prefix — a typo in the source).
   *Recommendation:* don't propagate the typo; use the real, correct path
   `./week1_baseline/bin/python/02_the_registry` in the Python README, same
   as the `01_struct_skeleton` port did with its own Run Example section.

## Implementation steps (once questions above are answered)

1. Add `boukensha/errors.py` with `UnknownToolError`.
2. Add `boukensha/registry.py` with `Registry` (`tool`, `dispatch`) per the
   mapping table.
3. Update `boukensha/__init__.py` to export `Registry`, `UnknownToolError`.
4. Rewrite `examples/example.py` per the script above.
5. Add `week1_baseline/bin/python/02_the_registry` launcher.
6. Rewrite `week1_baseline/python/02_the_registry/README.md` from the
   `01_struct_skeleton`-copied placeholder to content adapted from
   `@week1_baseline/ruby/02_the_registry/README.md`, using the real captured
   output (not the Ruby README's stale `budget=8192` example) and the
   corrected Run Example path.
7. Update `pyproject.toml`'s `description` field to "— 02: the registry".
8. If automated tests are in scope (open question 4): add
   `tests/test_registry.py` covering `tool()` registration/return value,
   `dispatch()` calling the block with correct kwargs, and `dispatch()` on
   an unregistered name raising `UnknownToolError` with the exact expected
   message.
9. Verify: run `week1_baseline/bin/python/02_the_registry` and diff its
   output against `week1_baseline/bin/ruby/02_the_registry`'s actual output
   (not the README's stale expected-output block) — same banner, same tool
   listing, same dispatch results, same caught-error message.
