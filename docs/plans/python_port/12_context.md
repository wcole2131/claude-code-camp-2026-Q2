# Python Port Plan · 12 · Context Management

Status: implemented. All three open questions were answered with the recommended options
(thorough shape/round-trip fixture tests for the OpenAI Responses-API rewrite with no separate
live-call note, `models.py` as plain module-level functions, and dropping Ruby's `!`/`?` method-name
suffixes). `week1_baseline/python/12_context/` now has context/compaction tracking, the `Tasks`
removal, the normalized reasoning-block contract across all five backends, the OpenAI Responses-API
rewrite, `/compact`, TUI colour coding, tests, launcher, and README described below. Verified against
the real Anthropic API and a live MUD server on both languages side-by-side (bypassing a pre-existing,
unrelated Ruby-side `bundle exec`/`BUNDLE_GEMFILE` subprocess-inheritance issue in `mcp.rb` — not
something this port touched or needed to fix) — the JSONL session logs match field-for-field.

## Goal

Turn `week1_baseline/python/12_context/` into a behavioral port of `week1_baseline/ruby/12_context/`
(`@week1_baseline/ruby/12_context/README.md` is the spec), copied forward from
`week1_baseline/python/11_tui/`. This is by far the largest delta since the MCP migration (step
10): Ruby's step 12 (a) adds real context-window accounting, colour-coded warnings, and
auto/manual compaction, (b) removes the `Tasks::Player` abstraction entirely in favor of `Config`
reading agent settings directly, and (c) introduces a normalized `"reasoning"` content-block
contract across all five backends (Anthropic thinking, OpenAI Responses-API reasoning, Gemini
`thought`, Ollama/OllamaCloud `thinking`) plus a full API-surface switch for the OpenAI backend
(chat completions → Responses API). None of these three threads is optional — they all show up in
the same Ruby diff — so this plan treats them as one step, not three.

## How this plan was created

1. Confirmed `week1_baseline/python/12_context/` already exists as an untouched copy of
   `python/11_tui/` (per the user) — step 3 of the copy-forward workflow is done; this plan covers
   step 4 only.
2. `diff -rq week1_baseline/ruby/11_tui/ week1_baseline/ruby/12_context/` (excluding `vendor`,
   `.bundle`, `Gemfile.lock`, `.gitignore`, `*.gem`) to find the file-level delta.
3. `diff -u` on every changed file (`agent.rb`, all five `backends/*.rb`, `config.rb`,
   `context.rb`, `errors.rb`, `logger.rb`, `prompt_builder.rb`, `repl.rb`, `tui.rb`, `version.rb`,
   `boukensha.rb`, `examples/example.rb`) plus a full read of both new files (`lib/boukensha/models.rb`,
   `lib/boukensha/mcp/server.rb`) and the removed `lib/boukensha/tasks/` directory (`base.rb`,
   `player.rb`, read from `11_tui` for reference since `12_context` deletes it).
4. Read the new `README.md` in full — it documents context tracking, colour coding,
   auto-compaction, `/compact`, `Logger#compaction`, and `context_window:`, but does **not**
   mention the `Tasks` removal or the backend reasoning-block contract at all (those are described
   only in the "inherited from step 10/11" sections as if unchanged) — that's a documentation gap
   in the Ruby README, not evidence those changes are out of scope. Trusting the code over the
   README here per this project's established practice.
5. Grepped for `system_override?` (a `Config` method the new `config.rb` adds) across all of
   `ruby/12_context` — it has zero callers anywhere in that step. Confirmed this is dead code in
   Ruby itself, not a Python-porting gap.
6. Confirmed via `ruby/12_context/lib/boukensha/mcp/server.rb`'s doc comment and
   `mud_manager_mcp/bin/mud_manager_server` (which requires it via a Bundler path dependency) that
   `Boukensha::MCP::Server` is consumed only by the three standalone Ruby MCP server repos
   (`mud_manager_mcp/`, `file_system_mcp/`, `shell_mcp/`), which this project has never ported to
   Python (`docs/plans/python_port/10_standard_tools.md`: "there is no per-language server" —
   Python only ever acts as an MCP *client*, spawning the Ruby servers as subprocesses via
   `MCPClient.mud_manager_server`/etc.). `lib/boukensha/mcp.rb` itself (the client) is byte-identical
   between `11_tui` and `12_context`.
7. Read the current `python/12_context/boukensha/` source in full for every file the Ruby diff
   touches (`config.py`, `context.py`, `agent.py`, `repl.py`, `logger.py`, `__init__.py`, `mcp.py`,
   `errors.py`, `tui.py`, all five `backends/*.py`, `backends/base.py`, `tasks/base.py`,
   `tasks/player.py`, `examples/example.py`) to establish exactly what's reusable vs. what changes.
8. Grepped `tests/` for `Context(task=`, `task_settings`, `Player`, `Tasks` to scope which test
   files need updates beyond the ones obviously about to be deleted (`test_tasks.py`).

## Starting point (what's already in place, unchanged)

Everything under `python/11_tui/` not listed in the delta table below carries forward untouched,
because its Ruby source is byte-identical between `11_tui` and `12_context`:

- `boukensha/client.py`, `message.py`, `tool.py`, `run_dsl.py`, `registry.py` — no Ruby counterpart
  changed.
- `boukensha/mcp.py` — **no change**. `lib/boukensha/mcp.rb` (the client) is byte-identical between
  the two Ruby steps; only the sibling `lib/boukensha/mcp/server.rb` is new, and it has no Python
  consumer (see "How this plan was created" #6) — **not ported**.
- `boukensha/tui.py` — the layout/widget/worker/tick machinery is unchanged; only the
  progress/status rendering and the event-handling `match` need edits (see delta table).
- `boukensha/errors.py` — Ruby's `errors.rb` diff is alignment-only (extra spaces before `<`), no
  new exception types.
- `tests/*` other than the ones listed in the delta table.

## The exact delta (from `diff -u` between `ruby/11_tui` and `ruby/12_context`)

| Ruby file | Change | Python-relevant? |
|---|---|---|
| `lib/boukensha/version.rb` | `0.11.0` → `0.12.0` | Yes — bump `version.py`. |
| `lib/boukensha/context.rb` | `task:` param removed entirely. New: `context_window:` (default 200,000), `compaction_threshold:` (default 0.85), `current_tokens` (accessor, was cumulative-session sum, now "last API response's `input_tokens`"), `turn_tokens` (per-turn spend counter), `update_tokens`, `reset_turn_tokens`, `add_turn_tokens`, `usage_fraction`, `usage_pct`, `needs_compaction?`, `compact_messages!` (drops oldest 40%, keeps ≥2, resets `current_tokens`). `to_s` drops `task=`, adds `window=`/`current=`. | Yes — core of this step. |
| `lib/boukensha/agent.rb` | Constructor: `task_settings:` removed, `max_turn_tokens:` added (0/nil = disabled). `run`: calls `@context.reset_turn_tokens` + `compact_if_needed` at turn start; loop now checks *two* ceilings (`iteration_limit_reached?` and new `token_limit_reached?`); `record_usage` updates both `turn_tokens` (cumulative spend) and `current_tokens` (window pressure) after every call, including mid-turn tool-use calls; new `log_reasoning` emits one `logger.reasoning` event per reasoning content block; `extract_text` joins with `"\n"` instead of `""`; tool-call preamble text now logged via new `logger.plan` instead of being folded into `response`; `log_response`/`normalize_usage` helpers deleted (moved into `Logger#response`'s simpler signature — see below). | Yes. |
| `lib/boukensha/config.rb` | `tasks(name=nil)`/`user_prompts_dir` removed. New: `provider_type` (`dig(:tasks,:player,:provider) \|\| "anthropic"`), `model` (`dig(:tasks,:player,:model) \|\| "claude-haiku-4-5"`), `system_override?` (dead code — zero callers, see above), `agent_max_iterations`/`agent_max_output_tokens`/`agent_max_turn_tokens`/`agent_compaction_threshold` (each `dig(:agent, key)` with a default: 25 / 1024 / 60\_000 / 0.85), `load_system_prompt` (reads `tasks.player.prompt_override.system` to pick between a task-scoped override file and the flat `prompts/system.md`, replacing `Tasks::Player.system_prompt`). `to_s` updated. Note the YAML key path `tasks.player.*` is preserved even though the `Tasks::Player` *class* is gone — only the Ruby-side lookup mechanism changed, not the `settings.yaml` schema. | Yes. |
| `lib/boukensha/errors.rb` | Alignment whitespace only. | No functional change. |
| `lib/boukensha/logger.rb` | `prompt(messages:, tools:)` gains `context_window:`. New `compaction(before:, dropped:, context_window:)` and `plan(text:)` events. `response(...)` signature shrinks to `(text:, usage: nil, stop_reason: nil)` — `task:`/`backend:` params and the entire `execution_metadata`/cost-estimation/`task_name`/`provider_name`/`usage_tokens`/`estimate_cost` private-method cluster are **deleted outright**, not just unused. New `reasoning(text:, redacted: false)` event. | Yes — this removes real functionality (cost estimation), not just plumbing; call it out explicitly in the README rewrite too. |
| `lib/boukensha/repl.rb` | New `/compact` command (`context.compact_messages!` + message), added to `HELP` and the banner. Constructor gains `max_turn_tokens:`, drops `task_settings:` (both just pass through to `Agent.new`). | Yes. |
| `lib/boukensha/tui.rb` | Two new palette colours (`yellow`, `red`). `@session_input_tokens`/`@session_output_tokens` (session-cumulative, tracked in `Tui` itself) **removed** — idle progress line and status line now read `@context.current_tokens`/`@context.context_window`/`usage_pct` directly instead. New `ctx_color(pct)` (grey/yellow/red at 70%/85%). Status line gains a `⚠` at ≥85%. New `"compaction"` event case appends a `[context compacted — N messages dropped to free space]` line to the conversation. Textarea width now tracks terminal width minus prompt length (cosmetic, was previously unset/default). | Yes. |
| `lib/boukensha/backends/base.rb` | Comment-only: documents the new normalized content-block contract (`"reasoning"` blocks, `text`/`signature`/`redacted` fields, ordering). | Docs only, no code — but the contract itself is real and every backend below implements it. |
| `lib/boukensha/backends/anthropic.rb` | Model table: dropped the redundant `claude-haiku-4-5-20251001` alias entry (kept `claude-haiku-4-5`). `to_messages`: assistant-role messages now route through new `assistant_content` (was falling through to the generic `else` branch). New `normalize_block`/`denormalize_block`: Anthropic's native `thinking`/`redacted_thinking` blocks ↔ the common `"reasoning"` shape, preserving `signature`/`data` for exact round-trip (the API rejects a modified thinking block on the next call). | Yes. |
| `lib/boukensha/backends/openai.rb` | **Full API switch**: `BASE_URL` chat-completions → `/v1/responses`. `to_messages`→`to_input` (messages become `input` items; system prompt becomes top-level `instructions`; tool results become `function_call_output` items keyed by `call_id` instead of `{role:"tool"}`). `to_tools`: flat `{type,name,description,parameters}`, no `function:` wrapper. `to_payload`: `messages`→`input`, `max_completion_tokens`→`max_output_tokens`, adds `instructions`, adds `reasoning: {effort: "none"}`. `parse_response`: reads `response["output"]` array (`"reasoning"`/`"message"`/`"function_call"` item types) instead of `choices[0].message`. `assistant_message`→`assistant_items` (drops reasoning blocks when rebuilding — gpt-5.x doesn't need them echoed back at `effort: "none"`). Model table: dropped `gpt-5.4` (no replacement), added `gpt-5.4-nano`. | Yes — the single largest/riskiest file in this step. |
| `lib/boukensha/backends/gemini.rb` | Model table trimmed to `gemini-3.5-flash` + `gemini-3.1-flash-lite` (dropped `gemini-2.5-*` entirely; a commented-out `gemini-3.1-pro-preview-customtools` entry is explanatory, not live). New `thinking_config` (disables thinking: `thinkingBudget: 0`, or `thinkingLevel: "LOW"` for the one model that can't fully disable it) wired into `to_payload`'s `generationConfig`. `parse_response`: `part["thought"]` → `"reasoning"` block; tool-call blocks gain `signature` from `part["thoughtSignature"]`. `assistant_parts`: reasoning blocks re-emitted as `{text:, thought:true, thoughtSignature:}`; tool-use blocks carry `thoughtSignature` through if present. | Yes. |
| `lib/boukensha/backends/ollama.rb` | Model table trimmed to just `gemma4:e4b` (dropped 8 other entries). `to_payload` adds `think: false`. `parse_response`: non-empty `message["thinking"]` → `"reasoning"` block (prepended before any text block). | Yes. |
| `lib/boukensha/backends/ollama_cloud.rb` | Same `think: false` + `"reasoning"`-from-`thinking` treatment as `ollama.rb`. Model table: `kimi-k2.5:cloud` and `minimax-m3:cloud` reordered (no content change). | Yes. |
| `lib/boukensha/prompt_builder.rb` | Comment-only (documents the delegated normalized-response shape). | No code change. |
| **`lib/boukensha/models.rb`** (new) | `Boukensha::Models.context_window(model)` — a small static model→context-window lookup (3 Anthropic entries, all 200,000) with `DEFAULT_CONTEXT_WINDOW = 32_000` for unrecognized model ids. Deliberately *not* the same table as each backend's own `MODELS` (which has cost/usage-unit data too) — this is a separate, minimal, cross-backend table used only to default `context_window:` when the caller doesn't supply one. | Yes — new `models.py`. |
| `lib/boukensha/mcp/server.rb` (new) | Generic MCP server-side JSON-RPC loop (`initialize`/`tools/list`/`tools/call`), used by the three standalone Ruby MCP server repos. | **No** — no Python consumer exists or is planned (see #6 above). |
| `lib/boukensha.rb` | Both `run`/`repl`: drop `require_relative "boukensha/tasks/player"`; add `require_relative "boukensha/mcp/server"` and `require_relative "boukensha/models"`. Replace `task_class`/`cfg.tasks(...)`/`Tasks::Player.*` calls with direct `cfg.system_prompt`/`cfg.model`/`cfg.provider_type`. New `context_window:` keyword (default `nil` → `Models.context_window(model)`). `Context.new` call gains `context_window:`, `working_dir:` (previously never passed!), `compaction_threshold: cfg.agent_compaction_threshold`. `effective_max_iterations`/`effective_max_output_tokens` now come from `cfg.agent_max_iterations`/`cfg.agent_max_output_tokens` instead of `task_class.max_iterations(task_settings)`. `Logger.new` snapshot gains `max_turn_tokens:`/`context_window:`, drops `task:`. `Agent.new`/`Repl.new` gain `max_turn_tokens: cfg.agent_max_turn_tokens`, drop `task_settings:`. | Yes — `boukensha/__init__.py`'s `run()`/`repl()`. |
| `examples/example.rb` | Drops unused `result =` / trailing `puts result`. | No Python action — Python's `example.py` already calls `boukensha.repl(...)` (not `.run`), a pre-existing, already-audited divergence from step 11; nothing here changes that. |
| `README.md` | Full rewrite: context tracking, colour coding, auto-compaction, `/compact`, `Logger#compaction`, `context_window:` keyword, version bump in run instructions. | Yes — Python README rewrite. |

## Delta to apply to `python/12_context`

| Change | File(s) | Action |
|---|---|---|
| Version bump | `boukensha/version.py` | `VERSION = "0.12.0"` |
| Context accounting | `boukensha/context.py` | Drop `task` param/attribute entirely (and the `TYPE_CHECKING` import of `tasks.base.Base`). Add `context_window: int = 200_000`, `compaction_threshold: float = 0.85` (constructor kwargs), `current_tokens: int = 0`, `turn_tokens: int = 0`. Add `update_tokens(n)`, `reset_turn_tokens()`, `add_turn_tokens(input, output)`, `usage_fraction` (property), `usage_pct` (property, `round(usage_fraction * 100)`), `needs_compaction(threshold=None)`, `compact_messages(target_fraction=0.60)` (drop `min(ceil(len*0.4), len-2)` oldest messages, floor at 0, reset `current_tokens`, return dropped count). `clear_messages` also resets `current_tokens` to 0 (new — wasn't in `clear_messages!` before this step in Ruby either, so this is genuinely new behavior, not a pre-existing Python gap). Update `__str__`. |
| Agent limits + compaction | `boukensha/agent.py` | Drop `task_settings`/`_resolve_max_iterations`/`_resolve_max_output_tokens` (replace with plain `max_iterations: int \| None = None` defaulting to `self.MAX_ITERATIONS`, `max_output_tokens: int \| None = None` with no fallback — matches Ruby's simplified constructor). Add `max_turn_tokens: int \| None = None` (0 when `None`, matches Ruby's `.to_i` behavior with no default constant). **Keep** the existing `interrupt: threading.Event \| None` param and its cooperative-cancellation check at the top of `run()` — this is a Python-only addition from step 11 (Ruby uses unsafe `Thread#raise`) with no Ruby equivalent to remove. At the top of `run()`, after the interrupt check: call `self.context.reset_turn_tokens()` then `self._compact_if_needed()`. Add `_token_limit_reached()` (mirrors `_iteration_limit_reached`). Loop checks both ceilings, in Ruby's order (iterations first, then tokens). Add `_record_usage(response)` (updates both `turn_tokens` and `current_tokens` from `response["usage"]`) and `_compact_if_needed()` (calls `logger.compaction` around `context.compact_messages()`). Add `_log_reasoning(content)` iterating reasoning blocks, skipping empty non-redacted ones. Replace `_log_response`/`_normalized_usage` with direct `self.logger.response(text=..., usage=response.get("usage"), stop_reason=...)` calls (drop `task=`/`backend=` args — no longer accepted by `Logger.response`). `_extract_text` joins with `"\n"` not `""`. `_handle_tool_calls`: log any non-empty preamble via new `self.logger.plan(text=...)`, then always log the `"(tool use — N calls)"` placeholder via `self.logger.response(...)` (drop the reasoning/placeholder branching that used to pick one or the other). |
| Config surface | `boukensha/config.py` | Drop `tasks()`/`user_prompts_dir`. Add `provider_type` (`self.dig("tasks","player","provider") or "anthropic"`), `model` (`self.dig("tasks","player","model") or "claude-haiku-4-5"`), `system_override` (`self.dig("system","override") is True` — port for parity even though it's unused in Ruby too), `agent_max_iterations`/`agent_max_output_tokens`/`agent_max_turn_tokens`/`agent_compaction_threshold` (properties over `self.dig("agent", key)` with defaults 25/1024/60000/0.85, `int()`/`float()` conversion). Add `system_prompt` property (`load_system_prompt` logic: if `dig("tasks","player","prompt_override","system") is True` and a task-scoped override file exists under `self.dir/"prompts"/"player"/"system.md"`, use it; else fall back to `self.dir/"prompts"/"system.md"`; `None` if neither exists). Update `__str__`. |
| Reasoning contract (docs) | `boukensha/backends/base.py` | Add a module/class docstring documenting the normalized `"reasoning"`/`"text"`/`"tool_use"` content-block contract (mirrors Ruby's new comment in `backends/base.rb` — no code change otherwise). |
| Anthropic backend | `boukensha/backends/anthropic.py` | Drop the redundant `"claude-haiku-4-5-20251001"` MODELS entry. `to_messages`: route `msg.role == "assistant"` through new `_assistant_content` instead of falling into the generic branch. Add `_normalize_block`/`_denormalize_block` for `thinking`/`redacted_thinking` ↔ `"reasoning"` (preserve `signature`/`data`). `parse_response` maps every content block through `_normalize_block`. |
| OpenAI backend rewrite | `boukensha/backends/openai.py` | Full rewrite per the Ruby delta row above: `BASE_URL` → `.../v1/responses`; `to_messages`→`to_input` (function_call_output items, assistant items via new `_assistant_items`); `to_tools` flattened (no `function:` wrapper); `to_payload` → `instructions`/`input`/`max_output_tokens`/`reasoning={"effort":"none"}`; `parse_response` reads `response["output"]` (`"reasoning"`/`"message"`/`"function_call"` items); drop `gpt-5.4`, add `gpt-5.4-nano`. |
| Gemini backend | `boukensha/backends/gemini.py` | Trim MODELS to `gemini-3.5-flash`/`gemini-3.1-flash-lite`. Add `_thinking_config()` wired into `to_payload`'s `generationConfig`. `parse_response`: `part["thought"]` → `"reasoning"` block; tool-use blocks carry `signature` from `part["thoughtSignature"]`. `_assistant_parts`: reasoning blocks → `{"text":..., "thought": True, "thoughtSignature":...}`; tool-use blocks re-attach `thoughtSignature` when present. |
| Ollama backend | `boukensha/backends/ollama.py` | Trim MODELS to just `"gemma4:e4b"`. `to_payload` adds `"think": False`. `parse_response`: non-empty `message["thinking"]` prepended as a `"reasoning"` block. |
| Ollama Cloud backend | `boukensha/backends/ollama_cloud.py` | Same `"think": False` + `"reasoning"`-from-`thinking` treatment as `ollama.py`. |
| New model table | `boukensha/models.py` (new) | `context_window(model: str) -> int`: 3-entry table (`claude-opus-4-8`/`claude-sonnet-4-6`/`claude-haiku-4-5`, all 200,000), `DEFAULT_CONTEXT_WINDOW = 32_000` fallback. Module-level function or small class — match whatever this project's existing flat-module style favors (`errors.py`/`version.py` use bare module contents, not a class wrapper). |
| Remove Tasks | `boukensha/tasks/` (delete `base.py`, `player.py`, `__init__.py`, the directory) | Entire subpackage removed — no Python code references it once `context.py`/`agent.py`/`repl.py`/`__init__.py` are updated. |
| Logger rewrite | `boukensha/logger.py` | `prompt(...)` gains `context_window: int`. Add `compaction(before, dropped, context_window)` and `plan(text)`. Simplify `response(...)` to `(text, usage=None, stop_reason=None)` — delete `task=`/`backend=` params and the entire `_execution_metadata`/`_task_name`/`_provider_name`/`_usage_tokens`/`_first_integer`/`_estimate_cost` cluster (dead once nothing calls it with `task=`/`backend=`). Add `reasoning(text, redacted=False)`. |
| Repl `/compact` | `boukensha/repl.py` | Add `"/compact"` case to `handle_command` (call `self._context.compact_messages()`, output `f"(compacted context — {dropped} messages dropped)"`) and to `HELP`/banner text. Constructor: drop `task_settings`, add `max_turn_tokens: int \| None = None`, pass through to `Agent(...)` in `run_turn`. |
| TUI context display | `boukensha/tui.py` | Add `"yellow"`/`"red"` to `ANSI_COLORS`. Remove `_session_input_tokens`/`_session_output_tokens` tracking in `__init__`/`_handle_event`'s `"response"` branch. Add `_ctx_color(pct)` (grey <70%, yellow 70–84%, red ≥85%, matching `Tui.CTX_WARN_PCT`/`CTX_ALERT_PCT` constants). `_render_progress`'s idle branch and `_render_status` both read `self._repl.context.current_tokens`/`.context_window`/`.usage_pct` instead of the deleted session counters, and format as `"used/max (pct%)"`; status line adds a `" ⚠"` suffix at ≥85%. Add a `"compaction"` case in `_handle_event` that writes `f"[context compacted — {dropped} messages dropped to free space]"` to the viewport. |
| MCP: no change | `boukensha/mcp.py` | **No action** — Ruby's `mcp.rb` is byte-identical this step; `mcp/server.rb` has no Python consumer (see above). |
| Dependency / description bump | `pyproject.toml` | `description` → `"— 12: context management"`. No new dependency — every new capability (YAML config, `dataclass`/plain-dict tracking, `textual` rendering) is already covered by existing deps. |
| Tests: delete | `tests/test_tasks.py` | Delete outright — no `Tasks` module left to test. |
| Tests: `Context` | `tests/test_context.py` | Drop `task=None`/`task=Player` kwargs from every `Context(...)` call (and the `from boukensha.tasks.player import Player` import if nothing else in the file needs it). Add coverage for `context_window`/`current_tokens`/`turn_tokens`/`usage_fraction`/`usage_pct`/`needs_compaction`/`compact_messages`/the `clear_messages` token reset. |
| Tests: `Agent` | `tests/test_agent.py` | Drop `task_settings=`-based tests (`test_task_settings_resolution_delegates_to_the_task_class`, `test_explicit_max_iterations_wins_over_task_settings` — rewrite the latter without `task_settings`). Add coverage for `max_turn_tokens` (ceiling triggers `_wrap_up("max_tokens")`), `_record_usage` updating both counters, `_compact_if_needed` triggering at the configured threshold, `_log_reasoning` emitting one event per reasoning block and skipping empty non-redacted ones, and the new `logger.plan`/`logger.response` split in `_handle_tool_calls`. |
| Tests: `Config` | `tests/test_config.py` | Add coverage for `provider_type`/`model` defaults and overrides, `agent_max_*`/`agent_compaction_threshold` defaults and overrides, `system_prompt` (both the flat and task-override-file paths), `system_override`. Remove/replace any `tasks(...)`/`user_prompts_dir`-based tests. |
| Tests: `Logger` | `tests/test_logger.py` | Remove tests for `_execution_metadata`/cost estimation/`task=`/`backend=` params on `response(...)`. Add coverage for `compaction(...)`, `plan(...)`, `reasoning(...)`, and `prompt(...)`'s new `context_window` field. |
| Tests: backends | `tests/test_backends.py` | Add reasoning-block round-trip coverage per backend (Anthropic `thinking`/`redacted_thinking` ↔ `"reasoning"` with signature preserved; Gemini `thought`/`thoughtSignature`; Ollama/OllamaCloud `thinking` string). Add full OpenAI Responses-API coverage: `to_payload` shape (`instructions`/`input`/`reasoning`), `parse_response` against a sample `output[]` array with `reasoning`/`message`/`function_call` items, and `_assistant_items` round-trip. This is the highest-risk file in the whole step — see open question 1. |
| Tests: `boukensha.run`/`repl` | `tests/test_boukensha_run.py`, `tests/test_boukensha_repl.py` | Replace `task_settings`-based assertions (`test_run_selects_backend_from_task_settings_and_returns_agent_result`, etc.) with `cfg.provider_type`/`cfg.model`-based ones. Add coverage for `context_window:` keyword defaulting via `Models.context_window` and for the new `Context(..., working_dir=..., compaction_threshold=...)` wiring. |
| Tests: `Repl` | `tests/test_repl.py` | Add `/compact` coverage; drop `task_settings` from `Repl(...)` construction in existing tests. |
| Tests: `Tui` | `tests/test_tui.py` | Update any assertions referencing session-cumulative token counters to instead assert against `context.current_tokens`/`.context_window`; add a `"compaction"` event coverage case. |
| Tests: MCP round-trip fixtures | `tests/test_tools_mud.py`, `tests/test_tools_file_system.py`, `tests/test_tools_shell.py` | Drop the now-invalid `task=None` kwarg from their `Context(...)` calls (2 lines each) — `system=` is unaffected since these were already passing a task placeholder, not relying on `task` for anything real. |
| README | `README.md` | Rewrite adapted from `ruby/12_context/README.md`: context tracking, colour coding thresholds, auto-compaction, `/compact`, `Logger.compaction`, `context_window:` keyword — same content/shape as the "Tool library"/"Terminal UI" inherited sections already written for steps 10/11, updated run instructions (`week1_baseline/bin/python/12_context`, version 0.12.0), and a note that `Boukensha::MCP::Server` (Ruby-only) has no Python counterpart, mirroring how prior READMEs already explain the client-only MCP story. |

## Ruby → Python behavior mapping

| Ruby | Python equivalent | Notes |
|---|---|---|
| `@messages.drop(drop_count)` where `drop_count = [(@messages.size * 0.40).ceil, @messages.size - 2].min.clamp(min: 0)` | `drop_count = max(0, min(math.ceil(len(self.messages) * 0.40), len(self.messages) - 2)); self.messages = self.messages[drop_count:]` | `Array#drop` is a plain slice from the front; the two-way `min` (40%-of-total vs. "leave at least 2") then floored at 0 needs `math.ceil` since Python has no `.ceil` on floats. |
| `usage_fraction`/`usage_pct` computed from `@current_tokens.to_f / @context_window` | `self.current_tokens / self.context_window if self.context_window > 0 else 0.0`; `round(usage_fraction * 100)` | Ruby's `Integer#round` and Python's `round()` both round-half-to-even on ties, but at typical usage percentages this never matters — plain `round()` is fine. |
| `Boukensha::MCP::Server` (`initialize`/`tools/list`/`tools/call` JSON-RPC loop over stdio) | *(not ported)* | Zero Python consumers; see "How this plan was created" #6 and the delta table. If a future step ever needs Python to *host* an MCP server (not just connect to one), start a fresh design rather than resurrecting this row's assumption. |
| OpenAI Responses API `output[]` array with `"reasoning"`/`"message"`/`"function_call"` item `type`s | `response.get("output") or []`, filtered/mapped by `item["type"]` | Direct structural port of Ruby's `filter_map` — Python has no single-pass filter+map, so this becomes a plain loop building `content`/`function_calls` lists (mirrors Ruby's own two-pass `content << ...; function_calls << ...` structure, not a comprehension, since the reasoning/message branches need `continue`-like skipping). |
| Anthropic `thinking`/`redacted_thinking` blocks' `signature`/`data` fields, echoed back unmodified | Preserve the raw string values in the normalized dict (`block["signature"]`) and re-emit unchanged in `_denormalize_block` | These are opaque provider tokens — never parse, validate, or transform them, just carry them through, same as Ruby's comment says. |

## Decisions carried over (no longer open)

- Copy-forward-then-delta workflow, `uv` + `hatchling`, flat `boukensha/` layout, `.python-version`
  = 3.14, `ruff`/`isort`/`ty` via `uv run`, `pytest` in `tests/`, `dict.get`-only lookups, plain
  mutable dataclasses/classes, duck-typed `NotImplementedError` abstract methods.
- Port observed Ruby behavior faithfully rather than silently improving on it — reapplied here as:
  port the dead-code `system_override?`/`system_override` even though nothing calls it, and default
  unrecognized models to a flat 32,000-token context window even though that's wrong for e.g.
  `gpt-5.5` (1M) — that mismatch is Ruby's behavior to mirror, not a bug to fix in the port.
  Similarly, `context.working_dir` is threaded through from `boukensha.rb`'s `Context.new` call for
  the first time this step even though nothing currently reads it back off `Context` — port the
  wiring anyway, matching Ruby exactly.
- Cooperative-cancellation via `threading.Event` on `Agent` (this project's Python-only substitute
  for Ruby's unsafe `Thread#raise(Interrupt)`, decided in the step-11 plan) stays exactly as-is;
  this step only adds `max_turn_tokens` alongside it, it doesn't touch interrupt handling.
- MCP is client-only in Python; the three standalone MCP servers remain Ruby-only subprocesses
  spawned by `MCPClient`, per the step-10 plan's explicit "no per-language server" decision.

## Open questions (please answer before implementation)

1. **How much test coverage for the OpenAI Responses-API rewrite?** This is the riskiest single
   file in the step — a full endpoint/payload/response-shape change with no way to exercise it
   against the real API in this environment (no `OPENAI_API_KEY` assumed available, same as every
   other backend test in this project). Recommendation: unit-test `to_payload`/`to_input`/`to_tools`
   shape and `parse_response`/`_assistant_items` round-tripping against hand-built fixture
   dicts shaped like real `output[]` arrays (mirroring how `test_backends.py` already tests the
   other backends purely structurally, no live calls) — thorough on shape, no live-API smoke test.
   Say so if you'd rather this get lighter (shape-only, skip round-trip) or heavier (add a
   `docs/plans/.../openai_responses_verification.md`-style live-call note for manual follow-up,
   similar to `mcp_integration_verification.md`).

2. **`models.py`'s shape: bare module functions, or a class like Ruby's `Boukensha::Models`?**
   Recommendation: a plain module-level dict + function (`TABLE = {...}`; `def context_window(model:
   str) -> int: return TABLE.get(model, {}).get("context_window", DEFAULT_CONTEXT_WINDOW)`),
   matching `errors.py`/`version.py`'s existing bare-module style rather than introducing a
   classmethod-only class purely to mirror Ruby's `module Models ... def self.context_window`
   idiom, which Python has no equivalent ceremony for.

3. **`Context.compact_messages`/`needs_compaction` naming: keep Ruby's `!`/`?` suffixes as
   docstring-only conventions, or drop them entirely (as this project already does for every prior
   bang/predicate method)?** Recommendation: drop them — `compact_messages`/`needs_compaction`,
   consistent with the existing `clear_messages` (not `clear_messages!`) and every other
   Ruby-bang-method already ported without a trailing underscore or naming gimmick in this
   codebase.

## Implementation steps (once questions above are answered)

1. `boukensha/version.py` → `"0.12.0"`.
2. `boukensha/context.py`: drop `task`, add context-window/compaction fields and methods.
3. `boukensha/models.py` (new): `context_window(model)` lookup per open question 2.
4. `boukensha/config.py`: drop `tasks()`/`user_prompts_dir`; add `provider_type`, `model`,
   `system_override`, `agent_max_*`, `system_prompt`.
5. `boukensha/logger.py`: simplify `response(...)`, delete the cost/metadata cluster, add
   `compaction`, `plan`, `reasoning`, extend `prompt(...)`.
6. `boukensha/agent.py`: drop `task_settings`, add `max_turn_tokens`, wire
   `reset_turn_tokens`/`compact_if_needed`/`_record_usage`/`_log_reasoning`, update
   `_handle_tool_calls`'s plan/response logging split, keep `interrupt` untouched.
7. `boukensha/backends/base.py`: docstring only.
8. `boukensha/backends/anthropic.py`: model table trim, `_assistant_content`,
   `_normalize_block`/`_denormalize_block`.
9. `boukensha/backends/openai.py`: full rewrite to the Responses API per the delta table.
10. `boukensha/backends/gemini.py`: model table trim, `_thinking_config`, reasoning/signature
    handling.
11. `boukensha/backends/ollama.py`, `ollama_cloud.py`: `think: false`, `thinking`→`reasoning`.
12. Delete `boukensha/tasks/` (`base.py`, `player.py`, `__init__.py`).
13. `boukensha/repl.py`: `/compact` command, `max_turn_tokens` passthrough, drop `task_settings`.
14. `boukensha/tui.py`: colour coding, drop session token counters, `"compaction"` event handling.
15. `boukensha/__init__.py`: drop `Player`/`Tasks` import and every `task_class`/`task_settings`
    reference in `run()`/`repl()`; wire `cfg.system_prompt`/`cfg.model`/`cfg.provider_type`,
    `context_window:` (default via `Models.context_window`), `Context(..., working_dir=...,
    compaction_threshold=...)`, `cfg.agent_max_*`, `Logger`/`Agent`/`Repl` snapshot/kwargs updates.
16. `pyproject.toml`: description bump only.
17. Update/add tests per the delta table (`test_tasks.py` deleted; `test_context.py`,
    `test_agent.py`, `test_config.py`, `test_logger.py`, `test_backends.py`,
    `test_boukensha_run.py`, `test_boukensha_repl.py`, `test_repl.py`, `test_tui.py`,
    `test_tools_mud.py`, `test_tools_file_system.py`, `test_tools_shell.py`).
18. `week1_baseline/bin/python/12_context` launcher (new, standard shape identical to every other
    step's).
19. `README.md` rewrite.
20. Run `week1_baseline/bin/ruby/12_context` and `week1_baseline/bin/python/12_context` side by
    side (build+install the gem per the Ruby README first if needed). Verify: context usage
    numbers track real `input_tokens` from responses (not a growing session sum), colour
    thresholds fire at 70%/85%, `/compact` and auto-compaction both drop the right message count
    and reset `current_tokens`, and the status/progress lines' formatting matches. Also run
    `cd week1_baseline/python/12_context && uv run pytest -v && make lint`.
