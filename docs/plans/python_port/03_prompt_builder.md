# Python Port Plan · 03 · The Prompt Builder

Status: DRAFT — open questions below must be answered before implementation
starts.

## Goal

Turn `week1_baseline/python/03_prompt_builder/` (currently an exact clone of
`python/02_the_registry`, still describing "Step 2: Tool Registry"
throughout) into a correct port of
`@week1_baseline/ruby/03_prompt_builder/`, by applying only the delta Ruby
itself made going from `02_the_registry` to `03_prompt_builder` — same
copy-prior-step-then-apply-delta workflow used for `01_struct_skeleton` and
`02_the_registry`, which is the standing pattern for every `NN_*` step.

This is the biggest step so far: it adds a `PromptBuilder`, five LLM
backends (Anthropic, Gemini, Ollama, OllamaCloud, OpenAI), model-metadata
tables with cost estimation, and a new `UnsupportedModelError`.

## How this plan was created

1. Read the target file (`docs/plans/python_port/03_prompt_builder.md`) — it
   existed but was empty.
2. Confirmed `week1_baseline/python/03_prompt_builder/` is a byte-identical
   copy of `week1_baseline/python/02_the_registry/` (`diff -rq`, excluding
   `.venv`/`.ruff_cache`/`.pytest_cache`/`__pycache__`/`uv.lock`, returned no
   differences).
3. Diffed every non-vendored file between
   `@week1_baseline/ruby/02_the_registry/` and
   `@week1_baseline/ruby/03_prompt_builder/` (`diff -rq`, excluding
   `vendor/`, `.bundle/`, `Gemfile.lock`, `.gitignore`) to get the exact
   delta: `lib/boukensha.rb`, `examples/example.rb`, `README.md`,
   `lib/boukensha/config.rb`, `lib/boukensha/errors.rb` changed;
   `lib/boukensha/context.rb` changed only by a trailing-newline fix (no
   behavior change); `lib/boukensha/backends/` (6 files) and
   `lib/boukensha/prompt_builder.rb` and `prompts/system.md` are new;
   `Gemfile`, `lib/boukensha/registry.rb`, `lib/boukensha/tool.rb`,
   `lib/boukensha/message.rb`, `lib/boukensha/tasks/base.rb`,
   `lib/boukensha/tasks/player.rb` are byte-identical, unchanged.
4. Read every changed/new Ruby file in full: `lib/boukensha.rb`,
   `lib/boukensha/config.rb`, `lib/boukensha/context.rb`,
   `lib/boukensha/errors.rb`, `lib/boukensha/prompt_builder.rb`,
   `lib/boukensha/backends/base.rb`, `.../anthropic.rb`, `.../gemini.rb`,
   `.../ollama.rb`, `.../ollama_cloud.rb`, `.../openai.rb`,
   `examples/example.rb`, `README.md`, `prompts/system.md`.
5. Ran `./week1_baseline/bin/ruby/03_prompt_builder` to capture real output
   (safe to run — this step only builds and pretty-prints the API payload
   dict; it never actually calls out to an LLM API).
6. Read the current Python scaffold in full to confirm what's reusable
   as-is and to pull exact conventions already established:
   `boukensha/config.py`, `boukensha/context.py`, `boukensha/errors.py`,
   `boukensha/tool.py`, `boukensha/message.py`, `boukensha/registry.py`,
   `boukensha/tasks/base.py` (already supports `default_prompts_dir` —
   ahead of where Ruby's own `tasks/base.rb` needed it until this step),
   `boukensha/tasks/player.py`, `boukensha/tasks/__init__.py` (empty package
   marker), `boukensha/__init__.py`, `examples/example.py`,
   `pyproject.toml`, `README.md`, and existing tests
   (`tests/test_tasks.py`, `tests/test_registry.py`) to match established
   test style.
7. Confirmed `week1_baseline/bin/python/03_prompt_builder` does not exist
   yet (only `bin/python/00_config`, `01_struct_skeleton`,
   `02_the_registry` do), same gap pattern filled in the two previous
   ports. `week1_baseline/bin/ruby/03_prompt_builder` already exists.
8. Confirmed `Gemfile`/`pyproject.toml` dependencies need **no** new
   entries — this step only builds payload dicts in memory; it never makes
   an HTTP call, so no HTTP client gem/package is needed on either side.

## Starting point (what's already in place, unchanged)

`week1_baseline/python/03_prompt_builder/` is currently byte-identical to
`week1_baseline/python/02_the_registry/`. These files need **no changes**
because their Ruby originals are identical between the two steps:

- `boukensha/context.py` — Ruby's `context.rb` only picked up a
  trailing-newline fix, no behavior change
- `boukensha/tool.py`, `boukensha/message.py`
- `boukensha/registry.py`
- `boukensha/tasks/base.py`, `boukensha/tasks/player.py`,
  `boukensha/tasks/__init__.py`
- `tests/test_config.py`, `tests/test_context.py`, `tests/test_message.py`,
  `tests/test_tasks.py`, `tests/test_registry.py`, `tests/test_tool.py`
- `.gitignore`, `Makefile`, `.python-version`

## The exact delta (from `diff -u` between the two Ruby steps)

`@week1_baseline/ruby/02_the_registry/lib/boukensha.rb` →
`@week1_baseline/ruby/03_prompt_builder/lib/boukensha.rb`: adds 7 new
`require_relative`s — `boukensha/prompt_builder`, `boukensha/backends/base`,
`.../anthropic`, `.../gemini`, `.../ollama`, `.../ollama_cloud`,
`.../openai`.

`@week1_baseline/ruby/02_the_registry/lib/boukensha/config.rb` →
`@week1_baseline/ruby/03_prompt_builder/lib/boukensha/config.rb`: adds one
new constant, `PROMPTS_DIR = File.expand_path("../../prompts", __dir__).freeze`
— the default system prompt shipped with this step, resolved relative to
`lib/boukensha/config.rb`'s own directory (two levels up to
`ruby/03_prompt_builder/`, then into `prompts/`). Nothing else in
`config.rb` changed.

`@week1_baseline/ruby/02_the_registry/lib/boukensha/context.rb` →
`@week1_baseline/ruby/03_prompt_builder/lib/boukensha/context.rb`: no
functional change (source file just gained a trailing newline).

`@week1_baseline/ruby/02_the_registry/lib/boukensha/errors.rb` →
`@week1_baseline/ruby/03_prompt_builder/lib/boukensha/errors.rb`: adds
`class UnsupportedModelError < StandardError; end` alongside the existing
`UnknownToolError`.

New file `lib/boukensha/prompt_builder.rb`: `Boukensha::PromptBuilder`,
wrapping a `Context` and a backend:
- `initialize(context, backend)` stores both
- `to_messages` → `@backend.to_messages(@context.messages)`
- `to_tools` → `@backend.to_tools(@context.tools)`
- `to_api_payload(max_output_tokens: 1024)` → `@backend.to_payload(@context, max_output_tokens: max_output_tokens)`
- `headers` → `@backend.headers`
- `url` → `@backend.url`

New file `lib/boukensha/backends/base.rb`: `Boukensha::Backends::Base`,
the shared contract every concrete backend inherits:
- `self.models` → `const_get(:MODELS)`, raising `NotImplementedError` if
  the subclass didn't define a `MODELS` constant
- `self.model_info(model)` → `models[model.to_s]`
- `self.validate_model!(model)` → returns the model string if known,
  otherwise raises `UnsupportedModelError` naming the class and listing
  supported models (sorted)
- instance `model_info` (no args) → `@model_info`
- `context_window`, `input_token_cost_per_million`,
  `output_token_cost_per_million`, `usage_unit`, `usage_level` — all read
  through `model_info`
- `estimate_cost(input_tokens:, output_tokens:)` → `nil` unless both costs
  are present (Ruby truthiness: `0.0 && 0.0` is truthy — only actual `nil`
  costs, as in OllamaCloud, short-circuit this), otherwise
  `(input_tokens * input_cost + output_tokens * output_cost) / 1_000_000.0`
- private `configure_model(model)` → validates and sets `@model`/`@model_info`; called by each subclass's `initialize`

New file `lib/boukensha/backends/anthropic.rb`: `Boukensha::Backends::Anthropic < Base`.
`BASE_URL = "https://api.anthropic.com/v1/messages"`. `MODELS` table with 4
entries (`claude-haiku-4-5`, `claude-haiku-4-5-20251001`,
`claude-sonnet-4-6`, `claude-opus-4-8`), each with `context_window`,
`cost_per_million: {input, output}`, `usage_unit: :tokens`.
`initialize(api_key:, model:)`. `to_messages(messages)`: maps `:tool_result`
role to a `user` message wrapping a `tool_result` content block
(`tool_use_id`, `content`); everything else passes through as
`{role: msg.role.to_s, content: msg.content}`. `to_tools(tools)`: each tool
→ `{name, description, input_schema: {type: "object", properties: tool.parameters, required: tool.parameters.keys.map(&:to_s)}}`.
`to_payload(context, max_output_tokens: 1024)` → top-level `system` field
plus `model`/`max_tokens`/`tools`/`messages`. `headers` sets
`x-api-key`/`anthropic-version`. `url` → `BASE_URL`.

New file `lib/boukensha/backends/gemini.rb`: `Boukensha::Backends::Gemini < Base`.
`BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"`.
`MODELS` table with 5 entries (`gemini-3.5-flash`, `gemini-3.1-flash-lite`,
`gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`).
`initialize(api_key:, model:)`. `to_messages(messages)`: `:assistant` role
renamed to `"model"`; `:tool_result` becomes a `user`-role message with a
`functionResponse` part (`name: tool_use_id`, `response: {content}`);
everything else → `{role: msg.role.to_s, parts: [{text: msg.content}]}`.
`to_tools(tools)`: `[]` if no tools, else one entry wrapping a
`functionDeclarations` array (`name`/`description`/`parameters` in the same
`type: "object"` shape as Anthropic's `input_schema`). `to_payload`:
top-level `systemInstruction: {parts: [{text: context.system}]}`,
`contents` (not `messages`), `tools`, `generationConfig: {maxOutputTokens: ...}`.
`headers` sets `x-goog-api-key`. `url` interpolates `@model` into
`BASE_URL/{model}:generateContent`.

New file `lib/boukensha/backends/ollama.rb`: `Boukensha::Backends::Ollama < Base`.
No `BASE_URL` constant — `initialize(host: "http://localhost:11434", model:)`
stores `@host` (no API key). `MODELS` table with 9 local entries
(`gemma4` variants, `qwen3:30b`, `qwen3:8b`, `deepseek-r1:8b`), all
`cost_per_million: {input: 0.0, output: 0.0}`, `usage_unit: :local_compute`.
`to_messages(system, messages)` — **note the two-argument signature**,
unlike Anthropic/Gemini's single-argument `to_messages(messages)`: prepends
a `{role: "system", content: system}` message, then maps `:tool_result` to
`{role: "tool", tool_name: tool_use_id, content}`, else passthrough.
`to_tools(tools)`: OpenAI-style `{type: "function", function: {name, description, parameters: {...}}}`
wrapper. `to_payload(context, max_output_tokens: 1024)`: `model`,
`stream: false`, `messages: to_messages(context.system, context.messages)`,
`tools` (no `max_output_tokens` field sent at all — Ollama's local API
doesn't take one here). `headers` → just `Content-Type`. `url` →
`"#{@host}/api/chat"`.

New file `lib/boukensha/backends/ollama_cloud.rb`: `Boukensha::Backends::OllamaCloud < Base`.
`BASE_URL = "https://ollama.com"`. `MODELS` table with 3 entries
(`gemma4:31b-cloud`, `minimax-m3:cloud` — which also carries an
`advertised_context_window: 1_000_000` alongside its real
`context_window: 512_000`, `kimi-k2.5:cloud`), all with
`cost_per_million: {input: nil, output: nil}` (genuinely unknown/plan-based
pricing, not zero) and `usage_unit: :ollama_cloud_usage` plus a per-model
`usage_level` (`:medium`/`:high`). `initialize(api_key:, model:)`.
`to_messages`/`to_tools`/`to_payload` are structurally identical to
Ollama's (same `to_messages(system, messages)` two-arg shape, same
`function`-wrapped tool schema, same `stream: false` payload, no
`max_output_tokens` field). `headers` adds `Authorization: Bearer`. `url` →
`"#{BASE_URL}/api/chat"`.

New file `lib/boukensha/backends/openai.rb`: `Boukensha::Backends::OpenAI < Base`.
`BASE_URL = "https://api.openai.com/v1/chat/completions"`. `MODELS` table
with 3 entries (`gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`), `usage_unit: :tokens`.
`initialize(api_key:, model:)`. `to_messages(system, messages)` — same
two-arg shape as Ollama, but `:tool_result` maps to
`{role: "tool", tool_call_id: tool_use_id, content}` (different key name
than Ollama's `tool_name`). `to_tools` — same `function`-wrapped shape as
Ollama/OllamaCloud. `to_payload` — `model`, `messages`, `tools`,
`max_completion_tokens: max_output_tokens` (OpenAI **does** send a token
cap, under a different key name than Anthropic's `max_tokens`). `headers`
adds `Authorization: Bearer`. `url` → `BASE_URL`.

New file `prompts/system.md`: one line, `"You are a MUD player assistant. Use the tools available to you to help the player explore, fight, and interact with the world.\n"` — the default system prompt used when a task doesn't have (or doesn't enable) a user override. (Your live `.boukensha/prompts/player/system.md` override is what actually printed in the captured output below — this file is only the fallback shipped alongside the code.)

`@week1_baseline/ruby/02_the_registry/examples/example.rb` →
`@week1_baseline/ruby/03_prompt_builder/examples/example.rb`: rewritten.
Still builds `Config`/`player_settings`/`Context` the same way, but now:
passes `default_prompts_dir: Boukensha::Config::PROMPTS_DIR` into
`system_prompt` (new — Ruby's `tasks/base.rb` already supported this
parameter since `01_struct_skeleton`; this is the first step that actually
supplies a value for it); registers `look` (no params) and `move` tools
directly via `Registry#tool` (no longer registers a `shout` tool from
`02_the_registry`'s example); seeds three messages (`user`, `assistant`,
`tool_result` with `tool_use_id: "toolu_01X"`); prints a `=== BOUKENSHA
Step 3: Prompt Builder ===` banner; reads `provider`/`model` off
`Boukensha::Tasks::Player.provider`/`.model`; a `case/when` selects and
constructs one of the five backends by provider name, reading the
matching `*_API_KEY` env var via `ENV.fetch` (raises if missing — no
default given) for every provider except `ollama` (no key needed,
local-only); raises `ArgumentError` for an unrecognized provider; builds a
`PromptBuilder`; prints `Config:`/`Provider:`/`Model:` then
`JSON.pretty_generate(builder.to_api_payload)`. No more direct
`ctx.tools.each_value`/dispatch demo from the `02_the_registry` example.

`@week1_baseline/ruby/02_the_registry/README.md` →
`@week1_baseline/ruby/03_prompt_builder/README.md`: fully rewritten from
"The Tool Registry" to "The Prompt Builder" — new sections: intro
paragraph on multi-provider support, "New Files", "How It Works" (ASCII
pipeline diagram), "Boukensha::PromptBuilder" (method table), "Backends"
(shared model-metadata-table explanation plus one subsection per backend
naming its endpoint/required env var/`MODELS` constant), "System Prompt",
"Tool Results", "Tool Definitions", "Message Roles" (each with a
Anthropic/Gemini/Ollama-OpenAI JSON comparison block), "Considerations"
(stateless conversation; tool results as user messages on Anthropic; the
agent only ever sees tool schemas, never the underlying block), and "Run
Example". Unlike `02_the_registry`'s README, there is **no** "Expected
Output" section and **no** duplicate/second "Considerations" section this
time. The "Run Example" snippet has the same missing-`ruby/`-segment typo
as before (`./week1_baseline/bin/03_prompt_builder`) — same known-typo
pattern already handled in the `02_the_registry` port; don't propagate it.

`Gemfile`, `lib/boukensha/registry.rb`, `lib/boukensha/tool.rb`,
`lib/boukensha/message.rb`, `lib/boukensha/tasks/base.rb`,
`lib/boukensha/tasks/player.rb`: unchanged, byte-identical between the two
Ruby steps.

## A real issue found in the Ruby source (needs your call, see open question 6)

`PromptBuilder#to_messages` calls `@backend.to_messages(@context.messages)`
— always exactly **one** argument. That matches Anthropic's and Gemini's
`to_messages(messages)` signature, but **not** Ollama's, OllamaCloud's, or
OpenAI's `to_messages(system, messages)` signature (those three need the
system prompt to prepend a `role: system`/`role: "system"` message). Calling
`PromptBuilder#to_messages` standalone with one of those three backends
would raise Ruby's `ArgumentError: wrong number of arguments (given 1,
expected 2)`.

This never surfaces in the example — `example.rb` only calls
`builder.to_api_payload`, which calls the backend's own `to_payload`
directly, and each backend's `to_payload` calls its own `to_messages` with
the correct arity internally. The bug is real but latent, only reachable
if someone calls `PromptBuilder#to_messages` directly with a
non-Anthropic/Gemini backend. See open question 6 for how to handle this
in the port.

## Delta to apply to `python/03_prompt_builder`

| Change | File(s) | Action |
|---|---|---|
| Add prompts dir constant | `boukensha/config.py` | add `PROMPTS_DIR: ClassVar[Path] = Path(__file__).resolve().parent.parent / "prompts"` — see path-depth note below |
| Add error type | `boukensha/errors.py` | add `class UnsupportedModelError(Exception): pass` alongside existing `UnknownToolError` |
| Add default prompt | `prompts/system.md` (new) | verbatim copy of the Ruby file's one line |
| Add backends package | `boukensha/backends/__init__.py` (new, empty) | package marker only, mirroring `boukensha/tasks/__init__.py` |
| Add shared backend base | `boukensha/backends/base.py` (new) | port `Base` per the mapping table below |
| Add each backend | `boukensha/backends/anthropic.py`, `gemini.py`, `ollama.py`, `ollama_cloud.py`, `openai.py` (all new) | port per the mapping table + per-backend notes above |
| Add prompt builder | `boukensha/prompt_builder.py` (new) | port `PromptBuilder` per the mapping table |
| Export new symbols | `boukensha/__init__.py` | add `Anthropic`, `Gemini`, `Ollama`, `OllamaCloud`, `OpenAI`, `PromptBuilder`, `UnsupportedModelError` — flattened to top level, matching the existing `Player` precedent (`Boukensha::Tasks::Player` → `boukensha.Player`), **not** nested as `boukensha.backends.Anthropic` |
| Rewrite the example | `examples/example.py` | replace the `02_the_registry`-style dispatch demo with the prompt-builder/backend-selection demo — see script below |
| Add the launcher | `week1_baseline/bin/python/03_prompt_builder` (new — doesn't exist yet) | mirror `bin/python/02_the_registry`'s shape |
| Rewrite docs | `README.md` | currently a verbatim copy of the `02_the_registry` README — replace with content adapted from `@week1_baseline/ruby/03_prompt_builder/README.md`, using the real captured output below and the corrected Run Example path |
| Update package metadata | `pyproject.toml` | `description` still reads "— 02: the registry" — update to "— 03: prompt builder" |
| Nothing to do | see "Starting point" above | already correct, Ruby originals didn't change (or changed with no behavioral effect) |

**Path-depth note for `PROMPTS_DIR`:** Ruby's `config.rb` lives at
`lib/boukensha/config.rb` (two directories below the project root), so
`File.expand_path("../../prompts", __dir__)` needs two `".."` to climb out.
Python's `config.py` lives at `boukensha/config.py` (only **one** directory
below the project root), so reaching the same destination
(`<project_root>/prompts`) takes `Path(__file__).resolve().parent.parent`
— two `.parent` calls counted from the *file itself*, which is equivalent
to "one `.parent` past the file's own containing directory." Same
destination, different traversal count, purely because the Python package
layout is one level shallower than Ruby's `lib/`-nested layout.

## Ruby → Python behavior mapping

### `errors.py`

| Ruby | Python | Notes |
|---|---|---|
| `class UnsupportedModelError < StandardError; end` | `class UnsupportedModelError(Exception): pass` | same shape as the existing `UnknownToolError` |

### `backends/base.py`

| Ruby | Python | Notes |
|---|---|---|
| `self.models` (class method, `const_get(:MODELS)` rescue `NameError`) | `models(cls)` classmethod: `try: return cls.MODELS; except AttributeError: raise NotImplementedError(...)` | |
| `self.model_info(model)` (class method, 1 arg) | `_model_info_for(cls, model)` (private classmethod) | **Python cannot give a classmethod and an instance property the same name in one class body** — Ruby overloads `model_info` by arity (class method takes an arg, instance method takes none); Python needs two different names. The instance-level, no-arg, *public* one keeps the name `model_info` (see below) since that's the one an external caller would actually reach for; the class-level lookup-by-name helper is renamed and treated as private. |
| `self.validate_model!(model)` | `validate_model(cls, model)` classmethod | drops the `!` — no bang-method convention in Python. Raises `UnsupportedModelError` |
| instance `model_info` (no args) → `@model_info` | `model_info` — public read-only property → `self._model_info` | |
| `context_window` | property → `self._model_info["context_window"]` | |
| `input_token_cost_per_million` / `output_token_cost_per_million` | properties → `self._model_info["cost_per_million"]["input"/"output"]` | |
| `usage_unit` | property → `self._model_info["usage_unit"]` | |
| `usage_level` | property → `self._model_info.get("usage_level")` | Ruby's `model_info[:usage_level]` is a bare hash lookup (nil if absent) → Python `.get()` |
| `estimate_cost(input_tokens:, output_tokens:)` | `estimate_cost(self, *, input_tokens: int, output_tokens: int) -> float \| None` | **pitfall:** must guard with `is None`, not truthiness — `if not in_cost or not out_cost: return None` would be wrong in Python, since `0.0` is falsy in Python but *truthy* in Ruby (`0.0 && 0.0` passes Ruby's guard). Local Ollama models have real `0.0` costs and must estimate to `0.0`, not `None`; only OllamaCloud's actual `None` costs should short-circuit. |
| private `configure_model(model)` | private `_configure_model(self, model)` | called from each subclass's `__init__`, not from `Base` itself (`Base` has no `__init__` of its own — subclasses' constructors differ too much, see below) |

### Each concrete backend (`anthropic.py`, `gemini.py`, `ollama.py`, `ollama_cloud.py`, `openai.py`)

| Ruby | Python | Notes |
|---|---|---|
| `initialize(api_key:, model:)` / `initialize(host: "http://localhost:11434", model:)` | `def __init__(self, *, api_key: str, model: str) -> None` / `def __init__(self, *, host: str = "http://localhost:11434", model: str) -> None` | stores the connection detail as an attribute, then calls `self._configure_model(model)` |
| `to_messages(messages)` (Anthropic, Gemini) | `def to_messages(self, messages: list[Message]) -> list[dict[str, Any]]` | |
| `to_messages(system, messages)` (Ollama, OllamaCloud, OpenAI) | `def to_messages(self, system: str \| None, messages: list[Message]) -> list[dict[str, Any]]` | keep the asymmetric arity — see open question 6 |
| `case msg.role when :tool_result ... else {role: msg.role.to_s, ...}` | `if msg.role == "tool_result": ... else: {"role": msg.role, ...}` | `msg.role` is already a plain `str` in the Python `Message` dataclass (unlike Ruby's `Symbol`), so no `.to_s`/`to_sym` translation is needed anywhere in these backends |
| `to_tools(tools)` | `def to_tools(self, tools: dict[str, Tool]) -> list[dict[str, Any]]` | `tool.parameters.keys.map(&:to_s)` → `list(tool.parameters)` (keys are already `str`) |
| `to_payload(context, max_output_tokens: 1024)` | `def to_payload(self, context: Context, *, max_output_tokens: int = 1024) -> dict[str, Any]` | |
| `headers` | `headers` property → `dict[str, str]` | |
| `url` | `url` property → `str` | |
| `MODELS = {...}.freeze` (symbol keys, e.g. `context_window:`) | `MODELS: ClassVar[dict[str, dict[str, Any]]] = {...}` (plain string keys) | numeric literals with `_` grouping (`1_000_000`) transliterate as-is — Python supports the same underscore grouping; `nil` → `None`; `:tokens`/`:local_compute`/`:ollama_cloud_usage`/`:medium`/`:high` symbols → plain strings, same no-symbol-duality simplification used everywhere else in this port series |

### `prompt_builder.py`

| Ruby | Python | Notes |
|---|---|---|
| `PromptBuilder.new(context, backend)` / `@context`/`@backend` | `def __init__(self, context: Context, backend: Base) -> None` | plain attribute storage, same shape as `Registry.__init__` |
| `to_messages` | `def to_messages(self) -> list[dict[str, Any]]: return self.backend.to_messages(self.context.messages)` | reproduces the arity bug for Ollama/OllamaCloud/OpenAI backends — see open question 6 |
| `to_tools` | `def to_tools(self) -> list[dict[str, Any]]: return self.backend.to_tools(self.context.tools)` | no arity issue here — every backend's `to_tools` takes exactly one arg |
| `to_api_payload(max_output_tokens: 1024)` | `def to_api_payload(self, *, max_output_tokens: int = 1024) -> dict[str, Any]: return self.backend.to_payload(self.context, max_output_tokens=max_output_tokens)` | the only method the example actually calls |
| `headers` | property or plain method → `self.backend.headers` | |
| `url` | property or plain method → `self.backend.url` | |

### Provider dispatch (in `examples/example.py`)

| Ruby | Python | Notes |
|---|---|---|
| `case provider when "anthropic" ... end` | `match provider: case "anthropic": ...` | Python 3.10+ structural pattern matching is the natural analogue of `case/when`; `pyproject.toml` already requires `>=3.14` |
| `ENV.fetch("ANTHROPIC_API_KEY")` (no default → raises if missing) | `os.environ["ANTHROPIC_API_KEY"]` (raises `KeyError` if missing) | different from `Config._resolve_dir`'s `ENV.fetch("BOUKENSHA_DIR", nil)` → `os.environ.get(...)`, which *does* have a Ruby-side default and maps to `.get()` instead |
| `raise ArgumentError, "Unsupported provider for player task: #{provider}"` | `raise ValueError(f"Unsupported provider for player task: {provider}")` | same mapping as `tasks/base.py`'s existing `ArgumentError` → `ValueError` convention |

## Example script (`examples/example.py`)

```python
import json
import os
from pathlib import Path

from boukensha import (
    Anthropic,
    Config,
    Context,
    Gemini,
    Ollama,
    OllamaCloud,
    OpenAI,
    Player,
    PromptBuilder,
    Registry,
)

repo_root = Path(__file__).resolve().parents[4]
os.environ.setdefault("BOUKENSHA_DIR", str(repo_root / ".boukensha"))

config = Config()
player_settings = config.tasks("player")
system_prompt = Player.system_prompt(
    player_settings,
    user_prompts_dir=config.user_prompts_dir,
    default_prompts_dir=Config.PROMPTS_DIR,
)

ctx = Context(task=Player, system=system_prompt)
registry = Registry(ctx)

registry.tool(
    "look",
    description="Look around the current room for details",
    parameters={},
    block=lambda: "A damp stone corridor stretches north. Torches flicker on the walls.",
)

registry.tool(
    "move",
    description="Move the player in a direction (north, south, east, west, up, down)",
    parameters={"direction": {"type": "string", "description": "The direction to move"}},
    block=lambda *, direction: f"You move {direction} into a torch-lit corridor.",
)

ctx.add_message("user", "I just arrived in the dungeon. What's around me, and can you move north?")
ctx.add_message("assistant", "Let me take a look around first.")
ctx.add_message(
    "tool_result",
    "A damp stone corridor stretches north. Torches flicker on the walls.",
    tool_use_id="toolu_01X",
)

print("=== BOUKENSHA Step 3: Prompt Builder ===")
provider = Player.provider(player_settings)
model = Player.model(player_settings)

match provider:
    case "anthropic":
        backend = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], model=model)
    case "ollama":
        backend = Ollama(model=model)
    case "ollama_cloud":
        backend = OllamaCloud(api_key=os.environ["OLLAMA_API_KEY"], model=model)
    case "openai":
        backend = OpenAI(api_key=os.environ["OPENAI_API_KEY"], model=model)
    case "gemini":
        backend = Gemini(api_key=os.environ["GEMINI_API_KEY"], model=model)
    case _:
        raise ValueError(f"Unsupported provider for player task: {provider}")

builder = PromptBuilder(ctx, backend)

print()
print(f"Config: {config}")
print(f"Provider: {provider}")
print(f"Model: {model}")
print(json.dumps(builder.to_api_payload(), indent=2))
```

Captured real output from `./week1_baseline/bin/ruby/03_prompt_builder`
(authoritative — the Ruby README has no "Expected Output" block to compare
against this time) that the Python port should match in **structure**
(same keys, same values, same nesting) — not necessarily in exact
whitespace, see the formatting note below:

```
=== BOUKENSHA Step 3: Prompt Builder ===

Config: #<Boukensha::Config dir=<repo>/.boukensha tasks=player>
Provider: anthropic
Model: claude-haiku-4-5
{
  "model": "claude-haiku-4-5",
  "system": "<your configured player system prompt>",
  "max_tokens": 1024,
  "tools": [
    {
      "name": "look",
      "description": "Look around the current room for details",
      "input_schema": { "type": "object", "properties": {}, "required": [] }
    },
    {
      "name": "move",
      "description": "Move the player in a direction (north, south, east, west, up, down)",
      "input_schema": {
        "type": "object",
        "properties": { "direction": { "type": "string", "description": "The direction to move" } },
        "required": ["direction"]
      }
    }
  ],
  "messages": [
    { "role": "user", "content": "I just arrived in the dungeon. What's around me, and can you move north?" },
    { "role": "assistant", "content": "Let me take a look around first." },
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "toolu_01X",
          "content": "A damp stone corridor stretches north. Torches flicker on the walls."
        }
      ]
    }
  ]
}
```

**Formatting note:** Ruby's `JSON.pretty_generate` renders empty
hashes/arrays with odd internal newlines (e.g. `"properties": {\n  },`).
Python's `json.dumps(..., indent=2)` renders them compactly as `{}`/`[]`
with no internal newlines. This is a cosmetic-only divergence in how empty
containers are pretty-printed — the data is identical — and is not worth
reproducing; accept Python's cleaner default rather than hand-rolling a
custom encoder to match Ruby's quirk.

## Decisions carried over (no longer open)

- **Copy-forward-then-delta workflow** — settled by the `01_struct_skeleton`
  port; applied again here.
- **`dict.get`-only lookups, no symbol/string duality** — settled in
  `00_config`; applies throughout the backends (roles, `usage_unit`,
  `usage_level`, MODELS keys all become plain strings).
- **Flatten nested Ruby modules to top-level Python exports** — settled
  implicitly by the existing `Boukensha::Tasks::Player` → `boukensha.Player`
  precedent already in `boukensha/__init__.py`. Applied here identically:
  `Boukensha::Backends::Anthropic` (and its four siblings) →
  top-level `boukensha.Anthropic`, not `boukensha.backends.Anthropic`.
  `Boukensha::Backends::Base` stays unexported at the top level, matching
  `Boukensha::Tasks::Base` also being unexported (only the concrete
  subclasses are).
- **Plain/mutable `@dataclass`es for `Tool`/`Message`, `dict[str, Any]` for
  settings/parameters** — settled in `01_struct_skeleton`; this step's
  `MODELS` tables follow the same plain-`dict` convention rather than
  introducing `TypedDict` machinery Ruby has no equivalent of.

## Open questions (please answer before implementation)

1. **`Base.model_info` naming collision** — confirmed above as a forced
   Python constraint, not a real choice: the public no-arg instance
   property keeps the name `model_info`; the class-level by-name lookup
   is renamed to a private `_model_info_for`. Flagging for sign-off since
   it's a rename away from a literal 1:1 method-name port.
2. **`Base.__init__`** — Ruby's `Base` class has no `initialize` of its
   own; each subclass defines its own (differing in whether it takes
   `api_key:` or `host:`) and calls the shared private `configure_model`.
   *Recommendation:* mirror this exactly — no `Base.__init__` in Python
   either, just the shared `_configure_model` helper, to avoid inventing a
   constructor shape Ruby doesn't have.
3. **`MODELS` typing** — plain `dict[str, Any]` (per "Decisions carried
   over" above) vs. introducing a `TypedDict` for model-info entries.
   *Recommendation:* plain `dict[str, Any]`, consistent with how
   `Config.settings`/`Tool.parameters` are already typed in this codebase.
4. **PromptBuilder's `headers`/`url`** — plain methods (`def headers(self)`)
   vs. `@property`. Ruby's `attr_reader`-less `def headers; @backend.headers; end`
   reads like a property (no-arg, value-returning). *Recommendation:*
   `@property` for both, matching how `Context.tool_count`/`turn_count` and
   `Config.dir`/`settings` are already exposed as properties elsewhere in
   this port.
5. **Automated tests** — following the precedent set by every prior step,
   should this add `tests/test_backends.py` (parametrized/shared coverage
   across all 5 concrete backends: model validation success/failure,
   `estimate_cost`'s `0.0`-vs-`None` distinction, `to_tools`/`to_messages`
   shape per backend, the Gemini `assistant`→`model` rename, the
   Ollama/OpenAI/OllamaCloud `tool_name` vs `tool_call_id` key difference)
   and `tests/test_prompt_builder.py` (delegation to the backend for
   `to_api_payload`, `headers`, `url`)? *Recommendation:* yes to both —
   this step's surface area (6 new files, cost math, 3 divergent wire
   formats) is large enough that skipping tests would leave the riskiest
   part of the port (the `0.0`/`None` cost pitfall, the role-mapping
   differences) unverified.
6. **The `PromptBuilder#to_messages`/backend arity mismatch** (see "A real
   issue found in the Ruby source" above) — reproduce Ruby's latent bug
   faithfully (Anthropic/Gemini `to_messages(self, messages)`, the other
   three `to_messages(self, system, messages)`, so calling
   `PromptBuilder.to_messages()` with one of those three raises a
   `TypeError` for missing argument, exactly mirroring Ruby's
   `ArgumentError`), or silently fix it in Python by normalizing all five
   backends to the same `to_messages(self, system, messages)` shape (with
   Anthropic/Gemini ignoring the unused `system` param)? *Recommendation:*
   reproduce faithfully — `to_api_payload` (the only method the example
   ever calls) works correctly for all 5 backends regardless, and silently
   "fixing" an interface Ruby itself hasn't fixed yet would contradict this
   port series' established practice of carrying forward source quirks
   rather than opportunistically redesigning them.
7. **Ruby README's broken `Run Example` path** — same typo pattern as
   `02_the_registry` (`./week1_baseline/bin/03_prompt_builder`, missing the
   `ruby/` segment). *Recommendation:* don't propagate it; use
   `./week1_baseline/bin/python/03_prompt_builder` in the Python README.

## Implementation steps (once questions above are answered)

1. Add `boukensha/config.py`'s `PROMPTS_DIR` class attribute.
2. Add `UnsupportedModelError` to `boukensha/errors.py`.
3. Add `prompts/system.md` (verbatim copy of the Ruby default).
4. Add `boukensha/backends/__init__.py` (empty) and `backends/base.py`
   (`Base` per the mapping table).
5. Add `backends/anthropic.py`, `gemini.py`, `ollama.py`,
   `ollama_cloud.py`, `openai.py`, each with its `MODELS` table and
   `to_messages`/`to_tools`/`to_payload`/`headers`/`url`.
6. Add `boukensha/prompt_builder.py` with `PromptBuilder`.
7. Update `boukensha/__init__.py` to export the 5 backend classes,
   `PromptBuilder`, and `UnsupportedModelError` (flattened, per "Decisions
   carried over").
8. Rewrite `examples/example.py` per the script above.
9. Add `week1_baseline/bin/python/03_prompt_builder` launcher.
10. Rewrite `week1_baseline/python/03_prompt_builder/README.md` from the
    `02_the_registry`-copied placeholder to content adapted from
    `@week1_baseline/ruby/03_prompt_builder/README.md`, using the real
    captured output above and the corrected Run Example path.
11. Update `pyproject.toml`'s `description` field to "— 03: prompt
    builder".
12. If automated tests are in scope (open question 5): add
    `tests/test_backends.py` and `tests/test_prompt_builder.py`.
13. Verify: run `week1_baseline/bin/python/03_prompt_builder` and compare
    its JSON payload structurally against
    `week1_baseline/bin/ruby/03_prompt_builder`'s actual output — same
    keys/values/nesting for the `anthropic` provider path (the one your
    `settings.yaml` currently selects), modulo the accepted empty-container
    pretty-printing difference noted above.
