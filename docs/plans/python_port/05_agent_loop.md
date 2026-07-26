# Python Port Plan · 05 · The Agent Loop

Status: DONE — open questions answered (recommendations accepted) and implementation applied.
`uv run pytest -v` (114 passed), `isort --check-only`, `ruff check`, and `ty check` all pass in
`week1_baseline/python/05_agent_loop/`. One addition beyond this plan's original delta table:
`ty check` surfaced that `boukensha/backends/base.py` also needed the `tools:` parameter and a
`parse_response` stub added to its `NotImplementedError`-raising interface — that file is a
Python-only addition from an earlier step (Ruby's `backends/base.rb` has no equivalent duck-typed
stubs at all, so it never needed to change), and the same "Ruby unchanged doesn't mean Python
unchanged" pattern flagged for `message.py`/`context.py` applied to it too once the type checker
was actually run. Like `04_api_client`, the example was **not** run live — it makes real
multi-turn network calls to `api.anthropic.com`, and `.boukensha/.env`'s provider keys are still
empty, so live-launcher verification is deferred until the user supplies a real key and asks for
it explicitly.

## Goal

Turn `week1_baseline/python/05_agent_loop/` (currently an exact clone of `python/04_api_client`,
still describing "Step 4: API Client" throughout) into a correct port of
`@week1_baseline/ruby/05_agent_loop/`, by applying only the delta Ruby itself made going from
`04_api_client` to `05_agent_loop` — same copy-prior-step-then-apply-delta workflow used for every
step so far.

This is the biggest step since `03_prompt_builder`: it's not just a new `Agent` class. All five
backends gain a `parse_response` method (normalizing five different provider response shapes into
one common shape) and, for four of the five, an `assistant_message`/`assistant_parts` inverse
helper, `to_payload` grows a `tools:` override parameter (so the wind-down call can disable tools),
and `Client`/`PromptBuilder` thread that `tools:` parameter through. It also surfaces a real gap in
the Python port's existing type modeling — see "Discovered issue" below — that the Ruby side never
had to deal with, because Ruby structs don't enforce field types.

## How this plan was created

1. Confirmed `week1_baseline/python/05_agent_loop/` is byte-identical to
   `week1_baseline/python/04_api_client/` (`diff -rq`, excluding
   `.venv`/`__pycache__`/`.ruff_cache`/`.pytest_cache`/`uv.lock`) — the user already did the
   copy-forward step, only the delta needs applying.
2. Diffed every non-vendored file between `@week1_baseline/ruby/04_api_client/` and
   `@week1_baseline/ruby/05_agent_loop/` (`diff -rq`, excluding `vendor/`, `.bundle/`,
   `Gemfile.lock`, `.gitignore`) to get the exact delta: `README.md`, `examples/example.rb`,
   every file under `lib/boukensha/backends/` (all 5 concrete backends, **not** `base.rb`),
   `lib/boukensha/client.rb`, `lib/boukensha/config.rb`, `lib/boukensha/errors.rb`,
   `lib/boukensha/prompt_builder.rb`, `lib/boukensha/tasks/base.rb`, `lib/boukensha.rb` changed;
   `lib/boukensha/agent.rb` is new; `Gemfile`, `lib/boukensha/backends/base.rb`,
   `lib/boukensha/context.rb`, `lib/boukensha/message.rb`, `lib/boukensha/registry.rb`,
   `lib/boukensha/tasks/player.rb`, `lib/boukensha/tool.rb`, `prompts/system.md` are all
   byte-identical, unchanged.
3. Read the new Ruby step's `README.md` in full (the user flagged this as the most useful single
   read) — it documents the common normalized response shape, the provider round-trip
   (`parse_response` / `assistant_message` inverse), the new `max_iterations`/`max_output_tokens`
   task settings, and the wind-down/wrap-up behavior.
4. Read every changed/new Ruby file in full, with precise `diff -u` (not just prose) on each
   changed file: `lib/boukensha/agent.rb` (new), `lib/boukensha.rb`, `lib/boukensha/errors.rb`,
   `lib/boukensha/config.rb`, `lib/boukensha/tasks/base.rb`, `lib/boukensha/prompt_builder.rb`,
   `lib/boukensha/client.rb`, all 5 `lib/boukensha/backends/*.rb`, `examples/example.rb`.
5. Cross-checked the README's "New Files"/"Updated Files" tables against the actual `diff -rq`
   output and found several stale/copy-pasted entries — see "README table is unreliable" below.
6. Read the current Python scaffold in full to confirm what's reusable as-is and to pull exact
   conventions already established: `boukensha/config.py`, `boukensha/context.py`,
   `boukensha/message.py`, `boukensha/client.py`, `boukensha/prompt_builder.py`,
   `boukensha/tasks/base.py`, `boukensha/registry.py`, `boukensha/tool.py`, `boukensha/__init__.py`,
   `boukensha/backends/{anthropic,ollama,ollama_cloud,openai,gemini}.py`, `examples/example.py`,
   and the existing `tests/` (`test_client.py`, `test_backends.py`, `test_tasks.py`, etc.) to match
   established test style for `test_agent.py` and the extensions the other test files need.
7. Confirmed `week1_baseline/bin/python/05_agent_loop` does not exist yet (only `bin/python/00`
   through `04` do), same gap pattern filled in every previous port.
8. Confirmed (from the prior `04_api_client` port) that `.boukensha/.env`'s provider API keys are
   present but empty on this machine — relevant to the live-API-verification open question below,
   which applies here even more directly since the whole point of this step is a multi-turn loop
   of real API calls, not a single one.

## Starting point (what's already in place, unchanged)

`week1_baseline/python/05_agent_loop/` is currently byte-identical to
`week1_baseline/python/04_api_client/`. These files need **no changes** because their Ruby
originals are identical between the two steps:

- `boukensha/backends/base.py`
- `boukensha/registry.py`, `boukensha/tool.py`
- `boukensha/tasks/player.py`, `boukensha/tasks/__init__.py`
- `prompts/system.md`
- `tests/test_registry.py`, `tests/test_tool.py`
- `.gitignore`, `Makefile`, `.python-version`

**Not** in this list, despite their Ruby originals being unchanged: `boukensha/context.py` and
`boukensha/message.py`. See "Discovered issue" below — they need Python-only changes that have no
Ruby-side delta to point to.

### README table is unreliable — verified against the actual diff, not trusted at face value

`@week1_baseline/ruby/05_agent_loop/README.md`'s "New Files" table lists `backends/base.rb`,
`tasks/base.rb`, `tasks/player.rb`, and `prompts/system.md` as new. All four are confirmed
byte-identical to `04_api_client` (`diff -rq` and `diff -u` both show zero differences) — they
already existed since earlier steps. This looks like a copy-pasted table from the `04_api_client`
README that wasn't fully edited for this step (same phenomenon flagged in the `02_the_registry`
and `04_api_client` plans for other README inaccuracies). The "Updated Files" table's claim that
`context.rb` changed is also false — `context.rb` is untouched on the Ruby side; the *Python* port
needs to touch `context.py` anyway, but for a reason the README doesn't mention (see below). Ground
truth for this plan is the actual `diff -rq`/`diff -u` output, not the README tables.

## The exact delta (from `diff -u` between the two Ruby steps)

`@week1_baseline/ruby/04_api_client/lib/boukensha.rb` → `.../05_agent_loop/lib/boukensha.rb`: adds
`require_relative "boukensha/agent"`.

New file `@week1_baseline/ruby/05_agent_loop/lib/boukensha/agent.rb`: `Boukensha::Agent` — see
"The Agent" section below for full behavior.

`@week1_baseline/ruby/04_api_client/lib/boukensha/errors.rb` → `.../05_agent_loop/.../errors.rb`:
adds `class LoopError < StandardError; end`. **Nothing in `agent.rb` (or anywhere else in this
step) actually raises `LoopError`** — grepped the whole step's `lib/` and `examples/`, zero hits
outside the class definition itself. Porting it anyway (it's public API surface Ruby ships), but
flagging that it's currently dead/aspirational code, not a design decision this plan needs to
justify further.

`@week1_baseline/ruby/04_api_client/lib/boukensha/config.rb` → `.../05_agent_loop/.../config.rb`:
converts `mud_host`/`mud_port`/`mud_username`/`mud_password` from multi-line `def...end` bodies to
Ruby's one-line "endless method" syntax (`def mud_host = dig(:mud, :host) || "localhost"`). Pure
Ruby syntax sugar, zero behavior change — nothing to port.

`@week1_baseline/ruby/04_api_client/lib/boukensha/tasks/base.rb` →
`.../05_agent_loop/.../tasks/base.rb`: adds `DEFAULT_MAX_ITERATIONS = 25` and
`DEFAULT_MAX_OUTPUT_TOKENS = 1024` constants, and two new class methods, `max_iterations(settings)`
/ `max_output_tokens(settings)`, both built on a new private `integer_setting(settings, key,
default)` helper: fetches the key via the existing `fetch` helper, returns `default` if the value
is `nil`, otherwise coerces via `Integer(value)`.

`@week1_baseline/ruby/04_api_client/lib/boukensha/prompt_builder.rb` →
`.../05_agent_loop/.../prompt_builder.rb`: `to_api_payload` gains a `tools:` keyword (default
`nil`), forwarded to `@backend.to_payload`; adds `parse_response(response)`, delegating to
`@backend.parse_response(response)`.

`@week1_baseline/ruby/04_api_client/lib/boukensha/client.rb` → `.../05_agent_loop/.../client.rb`:
`call` gains a `tools:` keyword (default `nil`), forwarded to `@builder.to_api_payload`. Nothing
else in `Client` changes — the retry/backoff/error logic from `04_api_client` is untouched.

All 5 `@week1_baseline/ruby/05_agent_loop/lib/boukensha/backends/*.rb` (not `base.rb`) changed:

- **Every backend**: `to_payload` gains a `tools:` keyword (default `nil`); when given, it's used
  verbatim instead of calling `to_tools(context.tools)` — this is what lets `Agent`'s wind-down
  call pass `tools: []` to disable tool use for exactly one call without touching the registry.
- **Every backend**: gains `parse_response(response)`, normalizing that provider's raw response
  into `{ stop_reason: "tool_use" | "end_turn", content: [...] }` — see "The normalized response
  shape" below for the exact per-provider mapping.
- **Ollama, Ollama Cloud, OpenAI, Gemini** (not Anthropic): gain a private inverse helper
  (`assistant_message` for Ollama/Ollama Cloud/OpenAI, `assistant_parts` for Gemini) that rebuilds
  a provider-specific assistant message from the normalized `content` blocks, and their
  `to_messages` now calls it for `role == :assistant`. **Anthropic needs no such helper** — its
  wire format already *is* the normalized shape, so its existing `to_messages` `else` branch
  (`{ role: msg.role, content: msg.content }`) already does the right thing whether `msg.content`
  is a plain string or the raw block array, unchanged.
- OpenAI's file gains `require "json"` (needed because `parse_response` does
  `JSON.parse(tc.dig("function", "arguments") || "{}")` — OpenAI's wire format encodes tool-call
  arguments as a JSON *string*, unlike every other provider which nests them as a JSON object
  directly).

`@week1_baseline/ruby/04_api_client/examples/example.rb` → `.../05_agent_loop/.../example.rb`:
rewritten — see "The example script" below.

`@week1_baseline/ruby/04_api_client/README.md` → `.../05_agent_loop/README.md`: rewritten from
"The API Client" to "The Agent Loop".

`Gemfile`, `lib/boukensha/backends/base.rb`, `lib/boukensha/context.rb`,
`lib/boukensha/message.rb`, `lib/boukensha/registry.rb`, `lib/boukensha/tasks/player.rb`,
`lib/boukensha/tool.rb`, `prompts/system.md`: unchanged, byte-identical between the two Ruby steps.

## Discovered issue: `Message.content`/`Context.add_message` are typed too narrowly for this step

This is the one place in this port so far where **the Ruby source needing zero changes doesn't
mean the Python port needs zero changes.** Ruby's `Message` is a `Struct` with no field types —
`content` has always been able to hold a `String` *or* an `Array` of content blocks, and
`content.to_s` in `Message#to_s`/the truncated-preview code has always coerced whatever's there
into a displayable string. That flexibility was simply never exercised until this step, because
until `Agent#handle_tool_calls` existed, nothing ever stored anything but a plain string as message
content:

```ruby
# agent.rb — stores the RAW block array, not a string, as an assistant message's content
def handle_tool_calls(content)
  @context.add_message(:assistant, content)
  ...
```

The Python port's `Message` is a `@dataclass` with `content: str`, and `Context.add_message`'s
signature is `content: str`. Both are now inaccurate — an assistant message that made tool calls
needs to store `content: list[dict[str, Any]]` (the parsed `content` blocks), not a string. This
needs fixing in `boukensha/message.py` and `boukensha/context.py` even though **their Ruby
counterparts (`message.rb`, `context.rb`) are byte-identical to `04_api_client` and require no
changes at all.** Concretely:

- `Message.content` type widens to `str | list[dict[str, Any]]`.
- `Message.__str__`'s truncation (`self.content[:61]`) needs to become
  `str(self.content)[:61]` — slicing a `list` takes the first 61 *items*, not characters, which
  silently does the wrong thing for anything longer than 61 tool-call blocks (unlikely to ever
  trigger in practice, but still the wrong operation) and produces a different (Python
  `repr`-style) string than Ruby's `Array#to_s`/inspect would, which is expected and fine — this
  is cosmetic debug-print output, not wire-format data, so exact byte-parity with Ruby's inspect
  format isn't a goal, matching cosmetic-only precedent elsewhere in this port (e.g. `Tool.__str__`'s
  `params=[...]` already renders as a Python list, not Ruby's `[:direction]` symbol-array format,
  accepted back in the `01_struct_skeleton` port).
- `Context.add_message`'s `content` parameter type widens to match.

## The normalized response shape

Every backend's `parse_response` converts its raw response into the same shape:

```python
{"stop_reason": "tool_use" | "end_turn", "content": [{"type": "text", "text": "..."}, ...]}
```

| Provider | Raw shape | Normalization |
|---|---|---|
| Anthropic | `stop_reason` field is directly `"tool_use"` or something else; `content` is already a list of `{"type": "text", ...}` / `{"type": "tool_use", "id", "name", "input"}` blocks | `stop_reason = "tool_use" if response["stop_reason"] == "tool_use" else "end_turn"`; `content = response.get("content") or []` — this **is** the normalized shape already, no block-level conversion needed |
| Gemini | `candidates[0].content.parts`, each part either `{"functionCall": {"name", "args"}}` or `{"text": ...}` | walk `parts`; a `functionCall` part becomes `{"type": "tool_use", "id": name, "name": name, "input": args or {}}` (Gemini has no call-id concept — the function *name* doubles as the id, and Gemini matches `functionResponse` back to a call by name too); a `text` part becomes `{"type": "text", "text": ...}`; `stop_reason` is `"tool_use"` iff any `functionCall` part was seen |
| Ollama / Ollama Cloud | `message.content` (string, possibly empty) + `message.tool_calls` (list of `{"function": {"name", "arguments"}}`) | non-empty `message["content"]` becomes one `{"type": "text", ...}` block; each tool call becomes `{"type": "tool_use", "id": name, "name": name, "input": arguments or {}}` — same "no call id, reuse the name" pattern as Gemini; `stop_reason` is `"tool_use"` iff `tool_calls` is non-empty |
| OpenAI | `choices[0].message.content` (string or `None`) + `message.tool_calls` (list of `{"id", "function": {"name", "arguments"}}`, where **`arguments` is a JSON-encoded string, not an object**) | truthy `message["content"]` becomes a `{"type": "text", ...}` block; each tool call becomes `{"type": "tool_use", "id": tc["id"], "name": ..., "input": json.loads(tc["function"]["arguments"] or "{}")}` — OpenAI is the only provider that assigns real call ids *and* JSON-encodes arguments as a string |

And the inverse (`assistant_message`/`assistant_parts`), used when replaying conversation history
on the *next* request — needed by every backend except Anthropic:

| Provider | Rebuild logic |
|---|---|
| Ollama / Ollama Cloud | `{"role": "assistant", "content": "".join(text blocks)}`, plus a `tool_calls` key (list of `{"function": {"name", "arguments"}}`) only if there were any tool-use blocks |
| OpenAI | same shape, but each rebuilt tool call is `{"id": ..., "type": "function", "function": {"name": ..., "arguments": json.dumps(input)}}` — re-encoding `input` back into a JSON string, the inverse of `parse_response`'s `json.loads` |
| Gemini | `[{"functionCall": {"name": ..., "args": input}}]` for tool-use blocks, `[{"text": ...}]` for text blocks — returns a list of *parts*, not a full message dict, since Gemini's `to_messages` wraps it as `{"role": "model", "parts": assistant_parts(msg.content)}` |

Every one of these rebuild helpers needs the same guard at the top: `msg.content` might still be a
plain `str` (an assistant message that never called a tool) or the `list[dict]` block form. Ruby's
`blocks = content.is_a?(String) ? [{ "type" => "text", "text" => content }] : content` pattern
ports directly: `blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content`.

## The Agent

`Boukensha::Agent` → `boukensha/agent.py`, `Agent` class:

| Ruby | Python | Notes |
|---|---|---|
| `MAX_ITERATIONS = 25`, `WRAP_UP_OUTPUT_TOKENS = 400`, `WRAP_UP_DIRECTIVE` (heredoc, `.strip`) | same as class attributes; `WRAP_UP_DIRECTIVE` as a plain triple-quoted string, `.strip()`ped | copy the directive text verbatim |
| `initialize(context:, registry:, builder:, client:, task_settings: nil, max_iterations: nil, max_output_tokens: nil)` | `__init__(self, *, context, registry, builder, client, task_settings=None, max_iterations=None, max_output_tokens=None)` | keyword-only, matching every other constructor in this port |
| `resolve_max_iterations`: `explicit.to_i` if given, else `@context.task.max_iterations(task_settings)` if `task_settings` is present and `@context.task.respond_to?(:max_iterations)`, else the constant | `int(explicit)` if given, else `self.context.task.max_iterations(task_settings)` if `task_settings` and `hasattr(self.context.task, "max_iterations")`, else `self.MAX_ITERATIONS` | `respond_to?` on a possibly-`nil` `@context.task` returns `false` in Ruby the same way `hasattr(None, "max_iterations")` returns `False` in Python — no extra `is None` guard needed, the pattern ports directly |
| `resolve_max_output_tokens`: same shape, no `.to_i` coercion, falls back to `nil` not a constant | mirror exactly — falls back to `None`, not `Agent.MAX_ITERATIONS`-style constant (there is no default output-token constant on `Agent`, only on `Tasks::Base`) | |
| `iteration_limit_reached?`: `@max_iterations.positive? && @iteration >= @max_iterations` | `self._max_iterations > 0 and self._iteration >= self._max_iterations` | |
| `call_opts`: `@max_output_tokens ? {...} : {}` | `{"max_output_tokens": self._max_output_tokens} if self._max_output_tokens else {}` | called as `self.client.call(**self._call_opts())` |
| `run`: loop — check limit → `wrap_up`; increment `@iteration`; print `[iteration N/max]`; call client; parse; branch on `stop_reason` | direct port, `while True:` | |
| `wrap_up(reason)`: seeds a `:user` message with `WRAP_UP_DIRECTIVE`, calls `@client.call(tools: [], max_output_tokens: WRAP_UP_OUTPUT_TOKENS)` (bypasses `call_opts` — always uses the fixed wind-down token budget, not the configured one), extracts text, falls back to `fallback_message` if blank; `rescue ApiError` also falls back | direct port; `try`/`except ApiError` around the wind-down call | |
| `fallback_message(reason)` | direct port, f-string | |
| `extract_text(content)`: `content.select { type == "text" }.map { text }.join` | `"".join(b["text"] for b in content if b.get("type") == "text")` | |
| `handle_tool_calls(content)`: stores `content` **as-is** (the raw block list, not a string) as the assistant message; for each `tool_use` block, dispatches via `@registry.dispatch(name, args)`, prints a **61-char-truncated preview** of `result.to_s`, but stores the **full untruncated** `result.to_s` as the `tool_result` message content | `self.context.add_message("assistant", content)` (relying on the widened `Message.content` type from the "Discovered issue" section above); `str(result)[:61]` only in the `print(...)` line; `self.context.add_message("tool_result", str(result), tool_use_id=use_id)` with the full string | the print/store asymmetry is easy to collapse into one variable by accident — keep them separate, matching Ruby exactly |

## The example script

`@week1_baseline/ruby/05_agent_loop/examples/example.rb` changes, relative to `04_api_client`'s:

- Drops `require "json"` (no longer pretty-printing a raw payload).
- Adds `base_dir = File.expand_path("..", __dir__)` — the step's root directory, computed once.
  Both tool blocks now resolve their `path:` argument against `base_dir` via
  `File.expand_path(path, base_dir)` instead of using the path as-is. This makes path resolution
  independent of the process's current working directory (previously it only worked because the
  launcher `cd`s into the step directory first) — a deliberate hardening, port it exactly as
  `Path(base_dir, path).resolve()` (pathlib's multi-arg constructor already has the same
  "later absolute component wins" semantics as `File.expand_path(path, base)`, so this is a direct,
  not approximate, translation).
- `read_file`'s block becomes `File.read(File.expand_path(path, base_dir))`.
- `list_directory`'s **description text** changes ("List files in a directory" →
  "List the files in a directory") and its **join separator** changes (`"\n"` → `", "`) — both
  easy to miss since they're a one-word and one-character diff respectively; block becomes
  `Dir.entries(File.expand_path(path, base_dir)).reject { |f| f.start_with?(".") }.join(", ")`.
- The registered tools now come *after* `agent = Boukensha::Agent.new(...)` is constructed
  (`Agent` doesn't need the tools to exist yet at construction time, only at dispatch time, so
  order here is presentation, not a dependency) — the Python port should still register tools
  before constructing `Context`'s first message the way `04_api_client` did structurally, but the
  registration calls themselves move to after `agent = Agent(...)` to mirror the Ruby file's
  reading order line-for-line.
- The seeded message changes from `"What files are in the current directory?"` to
  `"Read the README.md file and summarise what this MUD player assistant framework can do."`
  (British spelling — copy verbatim, it's example content not code).
- Drops the direct `client.call()`/raw-JSON-dump ending; instead builds
  `agent = Boukensha::Agent.new(context:, registry:, builder:, client:, task_settings: player_settings)`,
  prints `Max iterations: #{Tasks::Player.max_iterations(player_settings)}` and
  `Max output tokens: #{Tasks::Player.max_output_tokens(player_settings)}` alongside the existing
  `Config:`/`Provider:`/`Model:` lines, then calls `result = agent.run` and prints it under an
  `=== FINAL RESPONSE ===` banner. Top banner becomes `=== BOUKENSHA Step 5: Agent Loop ===`.

## Existing test file this step must also update, not just extend

`tests/test_client.py` (copied forward from `04_api_client`) has
`test_call_sends_the_builder_payload_as_the_request_body`, which asserts
`builder.to_api_payload.assert_called_once_with(max_output_tokens=2048)`. Once `Client.call` always
forwards a `tools=` keyword to `to_api_payload` (default `None`), that exact assertion **starts
failing** — the mock now receives `max_output_tokens=2048, tools=None`, not just
`max_output_tokens=2048`. This is a real regression risk if `tools:` is only added to `client.py`
and `test_client.py` isn't touched; flagging explicitly so it isn't the thing that ends up making
`pytest` red after the rest of the port looks done.

## Decisions carried over (no longer open)

- **Copy-forward-then-delta workflow**, `uv` + `hatchling`, flat `boukensha/` layout,
  `.python-version` = 3.14, `ruff`/`isort`/`ty` via `uv run`, `pytest` in `tests/` — unchanged.
- **`dict.get`-only lookups, non-dict-`settings` guard via `_fetch`** — settled in `00_config`/
  `04_api_client`; `max_iterations`/`max_output_tokens` should route through the same `_fetch`
  helper already on `Base`, matching Ruby's `integer_setting` building on its own private `fetch`.
- **`urllib.request`-based `Client`, retry/backoff logic** — settled in `04_api_client`, untouched
  by this step (only the new `tools:` passthrough parameter is added).
- **No live-API execution without an explicit key + explicit ask** — settled in `04_api_client`
  (open question 2 there); applies again, see the open question below.

## Open questions (please answer before implementation)

1. **Live-API verification** — same situation as `04_api_client`, more acutely: this step's
   example runs a *multi-turn loop* of real API calls (not one), so a live run is both more
   expensive and slower to fail/succeed than `04_api_client`'s single call. `.boukensha/.env`'s
   provider keys are still empty on this machine. *Recommendation: same as `04_api_client` —
   verify structurally via mocked `pytest` coverage of `Agent` (iteration limits, wind-down
   fallback, tool-call dispatch and message-history bookkeeping, the normalized-shape
   round-trip for each backend) with `Client.call` mocked out entirely; don't run the real
   launcher unless you supply a real key and explicitly ask for it.*
   Use the recommendation that was provided for this question.
2. **`Message.content`'s widened type** — confirmed above as a necessary Python-only change
   (`str | list[dict[str, Any]]`) with no Ruby-side delta driving it. Flagging for explicit
   sign-off since it's a type-contract change to an already-shipped, tested class from
   `00_config`, not something this step's Ruby delta table can point to directly.
   - Use best judgement for this question.
3. **`LoopError`** — port it (matches Ruby's public error surface) even though nothing currently
   raises it, per the "Discovered issue" note above? *Recommendation: yes, port it for parity —
   it's a one-line addition and future steps may start using it; just don't invent a use for it
   that Ruby itself doesn't have yet.*
   Use the recommendation for this step.
4. **Test coverage shape for `Agent`** — following the precedent set in every prior step, add
   `tests/test_agent.py` with mocked `Client`/`Registry` covering: normal tool-call round-trip
   (assistant message stored with the raw block list, tool dispatched, tool_result message
   stored untruncated while the printed preview is truncated), reaching `max_iterations` and
   getting a wind-down call, wind-down succeeding vs. returning the fallback message on blank
   text vs. on `ApiError`, and `max_iterations=0`/`None` disabling the ceiling. *Recommendation:
   yes, same as every prior step.* Also extend `tests/test_backends.py` with `parse_response`
   and `assistant_message`/`assistant_parts` coverage per provider (at minimum: a text-only
   response, a tool-call response, and — for OpenAI specifically — the JSON-string argument
   round-trip), and `tests/test_tasks.py` with `max_iterations`/`max_output_tokens` default and
   override cases. *Recommendation: yes to all three.*
   - Use the recommendation that was provided.

## Implementation steps (once questions above are answered)

1. Widen `Message.content` to `str | list[dict[str, Any]]` in `boukensha/message.py`; fix
   `__str__`'s truncation to `str(self.content)[:61]`.
2. Widen `Context.add_message`'s `content` parameter to match in `boukensha/context.py`.
3. Add `LoopError` to `boukensha/errors.py`.
4. Add `DEFAULT_MAX_ITERATIONS`/`DEFAULT_MAX_OUTPUT_TOKENS` and `max_iterations`/
   `max_output_tokens` classmethods (built on the existing `_fetch` helper, matching Ruby's
   `integer_setting`) to `boukensha/tasks/base.py`.
5. Add a `tools: list[dict[str, Any]] | None = None` parameter to `PromptBuilder.to_api_payload`
   and `Client.call`, threading it through to the backend; add `PromptBuilder.parse_response`.
6. For each of `boukensha/backends/{anthropic,gemini,ollama,ollama_cloud,openai}.py`: add the
   `tools:` override parameter to `to_payload`; add `parse_response` per the normalized-shape
   table above; for all but `anthropic.py`, add the `assistant_message`/`assistant_parts` inverse
   helper and call it from `to_messages` for `role == "assistant"`.
7. Add `boukensha/agent.py` with `Agent`, per the mapping table above.
8. Update `boukensha/__init__.py` to export `Agent` and `LoopError`.
9. Rewrite `examples/example.py` per "The example script" above.
10. Add `week1_baseline/bin/python/05_agent_loop` launcher, mirroring
    `@week1_baseline/bin/python/04_api_client`'s shape.
11. Rewrite `week1_baseline/python/05_agent_loop/README.md` adapted from
    `@week1_baseline/ruby/05_agent_loop/README.md` — don't propagate its stale New/Updated Files
    tables (see above); do carry over the normalized-response-shape explanation and the
    Considerations section (assistant-message-before-tool-result ordering, multi-tool-per-turn,
    the iteration ceiling being a trigger threshold not a hard cap, the agent never
    self-terminating).
12. Update `pyproject.toml`'s `description` field to `"— 05: agent loop"`.
13. Fix `tests/test_client.py`'s `test_call_sends_the_builder_payload_as_the_request_body`
    assertion to account for the new `tools=None` kwarg (see the callout above) — don't let this
    slip through as a "pre-existing passing test," it will start failing the moment step 5's
    `tools:` parameter lands.
14. Add `tests/test_agent.py`; extend `tests/test_backends.py` and `tests/test_tasks.py` per open
    question 4.
15. Verify: `uv run pytest -v && make lint` (isort/ruff/ty) in
    `week1_baseline/python/05_agent_loop/`. Only run the actual launchers
    (`week1_baseline/bin/python/05_agent_loop` / `week1_baseline/bin/ruby/05_agent_loop`) against
    a live API if the user has supplied a real key and explicitly asked for that comparison.
