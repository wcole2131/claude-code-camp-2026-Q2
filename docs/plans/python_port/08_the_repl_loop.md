Status: DRAFT — open questions below must be answered before implementation starts.

## Goal

Turn `week1_baseline/python/08_the_relp_loop/` (currently an exact clone of
`python/07_the_run_dsl`, still describing "Step 7" throughout) into a correct port of
`@week1_baseline/ruby/08_the_repl_loop/`, by applying only the delta Ruby itself made going from
`07_the_run_dsl` to `08_the_repl_loop` — same copy-prior-step-then-apply-delta workflow used for
every step so far.

This step adds `Boukensha.repl`/`Boukensha::Repl`, an interactive stdin loop that registers tools
once (via the same `configure`-callback pattern `07_the_run_dsl` established for `Boukensha.run`)
and then reads tasks from the user, runs the agent, and prints replies until `/exit`/`/quit`/EOF.
Conversation history now accumulates across turns because `Agent#run` starts persisting the
assistant's final reply into `Context` (a real, small behavior change, not REPL-only — it also
affects `Boukensha.run`, though one-shot callers never notice since they throw the context away
after one turn). Two smaller additions ride along: `Config`'s directory resolution gains a
`./.boukensha` project-local override between the env-var and home-directory defaults, and
`Client` gets a specific error message for HTTP 401 responses. A new `Boukensha::VERSION` constant
is introduced solely to print in the REPL banner.

**Naming note:** the copy-forward directory already in the tree is `python/08_the_relp_loop`
(transposed letters) rather than `08_the_repl_loop`, and `bin/python/08_the_repl_loop` (which does
already exist, unlike every previous step) currently `cd`s into `07_the_run_dsl`, not the new step
at all. See "Open questions" below — this needs to be fixed as part of this step, not carried
forward.

## How this plan was created

1. Confirmed `week1_baseline/python/08_the_relp_loop/` is byte-identical to
   `week1_baseline/python/07_the_run_dsl/` (`diff -rq`, excluding `.venv/`, `__pycache__/`,
   `.ruff_cache/`, `.pytest_cache/`).
2. Diffed every non-vendored file between `@week1_baseline/ruby/07_the_run_dsl/` and
   `@week1_baseline/ruby/08_the_repl_loop/` (`diff -rq`, excluding `vendor/`, `.bundle/`,
   `Gemfile.lock`, `.gitignore`): `README.md`, `examples/example.rb`, `lib/boukensha.rb`,
   `lib/boukensha/agent.rb`, `lib/boukensha/client.rb`, `lib/boukensha/config.rb`,
   `lib/boukensha/context.rb` changed; `lib/boukensha/repl.rb` and `lib/boukensha/version.rb` are
   new. `lib/boukensha/errors.rb`, `lib/boukensha/logger.rb`, `Gemfile`, `registry.rb`, `tool.rb`,
   `message.rb`, every `backends/*.rb`, `tasks/base.rb`, `tasks/player.rb`, `run_dsl.rb` are
   byte-identical, unchanged. (One correction mid-analysis: an earlier pass of this diff silently
   dropped due to a shell error and wrongly concluded `context.rb` was unchanged; re-ran it
   cleanly and confirmed it does change — see below.)
3. Read every changed/new Ruby file in full with precise `diff -u`: `lib/boukensha.rb` (new
   `self.repl` method), `lib/boukensha/repl.rb` (new, read whole), `lib/boukensha/version.rb` (new,
   read whole), `lib/boukensha/config.rb`, `lib/boukensha/context.rb`, `lib/boukensha/agent.rb`,
   `lib/boukensha/client.rb`, `examples/example.rb`.
4. Read the new Ruby step's `README.md` in full — found several stale/aspirational bits (see
   below); the README itself has a "Technical Considerations" section flagging two of its own
   unresolved questions, which is unusual (prior steps' READMEs didn't self-flag issues) and worth
   preserving in spirit in the Python README.
5. Grepped the whole `ruby/08_the_repl_loop/` tree (excluding `vendor/`) for `quiet?`, `debug?`,
   and `subscribe` to determine what's actually wired up: `Boukensha.quiet?` is defined but never
   read anywhere (confirms the README's own uncertainty about whether `/quiet` does anything);
   `Logger#subscribe` is still dead code (as it was in `07_the_run_dsl`); `Logger#turn` is **no
   longer dead** — `Repl#run_turn` now calls `@logger.turn(n: @turn)` every turn, though it only
   writes a JSONL line (`write_log`only ever writes to the log file/subscribers, never
   stdout — the README's claim of a printed "`╔══ turn N ══╗`" header does not match the actual
   code; see below).
6. Ran `week1_baseline/bin/ruby/08_the_repl_loop` live, piping `/exit` in immediately (no agent
   turns triggered, so no real API spend) to capture real ground-truth banner/output structure —
   see "Real captured output" below.
7. Read the current Python scaffold in full — `boukensha/__init__.py`, `boukensha/config.py`,
   `boukensha/context.py`, `boukensha/agent.py`, `boukensha/client.py`, `boukensha/errors.py`,
   `boukensha/logger.py`, `examples/example.py`, and `tests/` — to confirm exact existing
   signatures/conventions this step's new code must plug into. Confirmed `Context.clear_messages`
   does **not** yet exist in Python (it's a genuinely new method for this step, matching Ruby's own
   new `clear_messages!`, not something skipped from a prior step).
8. Confirmed `week1_baseline/bin/python/08_the_repl_loop` already exists (unusual — every prior
   step's plan noted the launcher was missing) but points at the wrong directory
   (`07_the_run_dsl`); `week1_baseline/bin/ruby/08_the_repl_loop` already exists and is correct.

## Starting point (what's already in place, unchanged)

`week1_baseline/python/08_the_relp_loop/` is currently byte-identical to
`week1_baseline/python/07_the_run_dsl/`. These files need **no changes** because their Ruby
originals are identical between the two steps:

- `boukensha/registry.py`, `boukensha/tool.py`, `boukensha/message.py`, `boukensha/run_dsl.py`
- `boukensha/errors.py`, `boukensha/logger.py`
- `boukensha/client.py` — *except* the one-line 401 special case, see below (everything else in
  the file is unchanged)
- `boukensha/backends/base.py`, `.../anthropic.py`, `.../gemini.py`, `.../ollama.py`,
  `.../ollama_cloud.py`, `.../openai.py`
- `boukensha/tasks/base.py`, `boukensha/tasks/player.py`, `boukensha/tasks/__init__.py`
- `boukensha/prompt_builder.py`, `boukensha/message.py`
- `prompts/system.md`
- `tests/test_backends.py`, `tests/test_tasks.py`, `tests/test_registry.py`, `tests/test_tool.py`,
  `tests/test_message.py`, `tests/test_prompt_builder.py`, `tests/test_run_dsl.py`
- `.gitignore`, `Makefile`, `.python-version`

## The exact delta (from `diff -u` between the two Ruby steps)

New file `@.../08_the_repl_loop/lib/boukensha/version.rb`: `Boukensha::VERSION = "0.8.0"`.

New file `@.../08_the_repl_loop/lib/boukensha/repl.rb`: `Boukensha::Repl` — the interactive loop
class. See "The `Repl` primitive" below.

`@.../07_the_run_dsl/lib/boukensha.rb` → `.../08_the_repl_loop/lib/boukensha.rb`: adds
`require_relative "boukensha/version"` (top of file) and `require_relative "boukensha/repl"`
(bottom); trims `self.run`'s doc comment down to one line ("See step 6 for full documentation" —
no behavior change, nothing to port); adds `self.repl(...)`, the new entry point — see
"`Boukensha.repl`" below.

`@.../07_the_run_dsl/lib/boukensha/config.rb` → `.../08_the_repl_loop/.../config.rb`:
`resolve_dir` gains a middle tier — env var override, then `./.boukensha` (current working
directory) if that directory exists, then the `~/.boukensha` default. Previously it was just
env-var-or-default.

`@.../07_the_run_dsl/lib/boukensha/context.rb` → `.../08_the_repl_loop/.../context.rb`: adds
`clear_messages!` (`@messages = []`), used by the REPL's `/clear` command. Genuinely new — Python's
`Context` has no equivalent method yet.

`@.../07_the_run_dsl/lib/boukensha/agent.rb` → `.../08_the_repl_loop/.../agent.rb`: `Agent#run`
now calls `@context.add_message(:assistant, text)` (or `msg`) at all three points where it returns
final text — the normal completion path, the wrap-up success path, and the wrap-up
`rescue ApiError` fallback path. Before this step the final reply was returned but never recorded
in `Context`, which didn't matter for one-shot `Boukensha.run` calls (the whole `Context` is
discarded after) but breaks multi-turn conversations, since the agent would never see its own
prior replies.

`@.../07_the_run_dsl/lib/boukensha/client.rb` → `.../08_the_repl_loop/.../client.rb`: adds a
specific `ApiError` message ("authentication failed (401) — check your API key") when the response
status is exactly 401, checked before the existing generic non-2xx `ApiError` raise. Not
retried — 401 was never in `RETRYABLE_STATUS_CODES` either before or after.

`@.../07_the_run_dsl/examples/example.rb` → `.../08_the_repl_loop/examples/example.rb`: rewritten
to call `Boukensha.repl do ... end` instead of `Boukensha.run(task: ...) do ... end`; drops the
step-banner `puts` lines (config line is now the only thing example.rb itself prints — the REPL
banner takes over from there); changes `base_dir` to point at `../../07_the_run_dsl` (a
directory with real files to browse) instead of the step's own directory; `list_directory`'s
result is now `.sort`ed before joining.

`Gemfile`, `lib/boukensha/errors.rb`, `lib/boukensha/logger.rb`, `lib/boukensha/registry.rb`,
`lib/boukensha/tool.rb`, `lib/boukensha/message.rb`, `lib/boukensha/run_dsl.rb`, every
`backends/*.rb`, `tasks/base.rb`, `tasks/player.rb`: unchanged, byte-identical between the two
Ruby steps.

### README is unreliable in several places — verified against the actual code and a live run

Same phenomenon flagged in every prior step's plan, worth listing precisely since this README has
unusually many mismatches:

- "Running it" section says `cd 07_the_repl_loop` (wrong step number, should be 8) and
  `ruby examples/step7.rb` (no such file exists — the real launcher is
  `bin/ruby/08_the_repl_loop` running `examples/example.rb`).
- The banner shown in the README (`BOUKENSHA REPL — MUD assistant` / `type a command and press
  Enter`) does not match the real banner `Repl#banner` renders, which is a box titled
  `BOUKENSHA MUD Assistant (v0.8.0)` followed by `config:`/`provider:` lines and a command-hint
  block. Real captured output (piping `/exit` immediately, no API call triggered):
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

  boukensha> Goodbye.
  ```
- The README's own "Technical Considerations" section admits uncertainty about whether
  `/quiet`/`/loud` do anything real, and whether re-instantiating `Agent` every turn (rather than
  once) is correct. Both are confirmed here: `quiet?`/`loud!` toggle a module-level flag that
  **nothing reads** (`grep` across the whole tree, only `debug?` gates anything, one `Logger`
  call), so `/quiet`/`/loud` are currently inert; and yes, `Repl#run_turn` really does construct a
  fresh `Agent` on every turn (cheap — `Agent.new` does no I/O). Port both exactly as observed —
  this is Ruby's own acknowledged, unresolved state, not something to "fix" in the port.
- The `Logger#turn` header the README describes printing to the terminal is not real —
  `write_log` only ever writes JSONL to the log file (and to `subscribe`rs, of which there are
  none). Document the real behavior (a log-only phase entry) instead.

## The `Repl` primitive

`Boukensha::Repl` → `boukensha/repl.py`, `Repl` class.

| Ruby | Python | Notes |
|---|---|---|
| `PROMPT = "boukensha> "` | `PROMPT = "boukensha> "` (class attr) | |
| `HELP = <<~HELP ... HELP` (squiggly heredoc) | plain triple-quoted class attr string | no heredoc-indent-stripping needed in Python; write it pre-dedented |
| `initialize(context:, registry:, builder:, client:, logger:, config_dir: nil, provider: nil, model: nil, version: nil, api_key: nil, task_settings: nil, max_iterations: nil, max_output_tokens: nil)` | `def __init__(self, *, context: Context, registry: Registry, builder: PromptBuilder, client: Client, logger: Logger, config_dir: Path \| None = None, provider: str \| None = None, model: str \| None = None, version: str \| None = None, api_key: str \| None = None, task_settings: dict[str, Any] \| None = None, max_iterations: int \| None = None, max_output_tokens: int \| None = None) -> None` | store each as `self._*`; `@turn = 0` → `self._turn = 0` |
| `start` — `loop do ... end`, `print PROMPT; $stdout.flush`, `input = $stdin.gets`, `break unless input` (EOF) | `def start(self) -> None:` — `while True:` loop; `try: line = input(self.PROMPT)` / `except EOFError: break` | Python's `input(prompt)` writes the prompt and reads a line in one call — no separate `print`+`flush` needed; EOF surfaces as `EOFError`, the direct analog of `gets` returning `nil` |
| `input.chomp.strip`, `next if input.empty?` | `line = line.strip()`; `if not line: continue` | Python's `input()` already strips the trailing newline, so only `.strip()` is needed (no `.chomp` equivalent required) |
| `case input when "/exit", "/quit" ... when "/help" ... when "/quiet" ... when "/loud" ... when "/clear" ...` | `match line: case "/exit" | "/quit": ... case "/help": ... case "/quiet": ... case "/loud": ... case "/clear": ...` | direct port; default falls through to `run_turn` exactly like Ruby's `case` with no matching `when` |
| `Boukensha.quiet!` / `Boukensha.loud!` | `boukensha.quiet()` / `boukensha.loud()` | module-level functions already exist (`00`-established), just need to be imported into `repl.py` |
| `@context.clear_messages!; @turn = 0` | `self._context.clear_messages(); self._turn = 0` | |
| `private def banner` — string interpolation building the box | `def _banner(self) -> str:` — f-string / `"\n".join([...])` | `" " * (9 - ver.length)` padding trick ports directly as `" " * (9 - len(ver))` |
| `key_status = (@api_key.nil? \|\| @api_key.strip.empty?) ? "✗ ..." : "✓ ..."` | `key_status = "✗ API key not set" if not self._api_key or not self._api_key.strip() else "✓ API key set"` | |
| `config_exists = @config_dir && Dir.exist?(@config_dir)` | `config_exists = self._config_dir is not None and self._config_dir.is_dir()` | |
| `private def run_turn(input)` — `@turn += 1`; `@logger.turn(n: @turn)`; `@context.add_message(:user, input)`; builds a fresh `Agent`; `result = agent.run`; `puts; puts result`; `rescue LoopError`/`rescue ApiError` | `def _run_turn(self, line: str) -> None:` — increments `self._turn`; calls `self._logger.turn(n=self._turn)`; `self._context.add_message("user", line)`; constructs `Agent(...)`; `result = agent.run()`; `print(); print(result)`; `except LoopError as e: print(f"\n[error] {e}")` / `except ApiError as e: print(f"\n[error] API call failed: {e}")` | a fresh `Agent` really is constructed every turn — port faithfully, see README-inaccuracy note above |

## `Boukensha.repl`

`Boukensha.repl` → a module-level `repl` function in `boukensha/__init__.py`, alongside `run` (no
name collision — same file `07_the_run_dsl` already put `run` in).

| Ruby | Python | Notes |
|---|---|---|
| `self.repl(system: nil, model: nil, backend: nil, api_key: nil, ollama_host: "http://localhost:11434", log: nil, max_output_tokens: nil, &block)` | `def repl(*, system: str \| None = None, model: str \| None = None, backend: str \| None = None, api_key: str \| None = None, ollama_host: str = "http://localhost:11434", log: str \| Path \| None = None, max_output_tokens: int \| None = None, configure: Callable[[RunDSL], None] \| None = None) -> None` | same `configure` naming/shape decided for `run()` in `07_the_run_dsl` — reused verbatim, not re-litigated |
| Body through `RunDSL.new(registry).instance_eval(&block) if block` | identical to `run()`'s equivalent lines | copy-paste from the existing `run()` implementation, not re-derived |
| `be = case backend ... end` (5 branches + `else raise ArgumentError`) | same `match backend: ... case _: raise ValueError(...)` block `run()` already has | |
| `Repl.new(context:, registry:, builder:, client:, logger:, task_settings:, max_iterations:, max_output_tokens:, config_dir: cfg.dir, provider: backend, model:, version: VERSION, api_key:).start` | `Repl(context=ctx, registry=registry, builder=builder, client=client, logger=logger, task_settings=task_settings, max_iterations=effective_max_iterations, max_output_tokens=effective_max_output_tokens, config_dir=cfg.dir, provider=backend, model=model, version=VERSION, api_key=api_key).start()` | `VERSION` imported from `.version` |
| `rescue Interrupt; puts "\nInterrupted."` (wraps the whole method body, including `Repl#start`) | `except KeyboardInterrupt: print("\nInterrupted.")` wrapping the `Repl(...).start()` call | Ctrl-C during a turn (including mid-`agent.run()`) propagates up through `start()` to here, exactly like Ruby's `Interrupt` — do not catch `KeyboardInterrupt` inside `Repl.start` itself |
| `ensure logger&.close` | `finally: if logger is not None: logger.close()` | identical pattern to `run()`; `logger` must be pre-declared `logger: Logger | None = None` before the `try`, same reasoning as `run()` (an unknown-backend `ValueError` can fire before `Logger(...)` is constructed) |

`repl()` returns `None` (Ruby's method has no meaningful return value either — `Repl#start`'s
`loop` just runs until `break`).

## `boukensha/version.py`

New file. `VERSION = "0.8.0"`. Exported from `boukensha/__init__.py`'s `__all__` (Ruby's constant
is public on the `Boukensha` module, so the Python port makes it public too, even though nothing
outside `repl()` currently reads it — same "port the surface, not just the call site" treatment as
`RunDSL` in `07_the_run_dsl`).

## `boukensha/config.py` — `_resolve_dir` change

| Ruby | Python | Notes |
|---|---|---|
| `return Pathname.new(ENV["BOUKENSHA_DIR"]).expand_path.to_s if ENV["BOUKENSHA_DIR"]` | `env_dir = os.environ.get("BOUKENSHA_DIR")` / `if env_dir: return Path(env_dir).expanduser().resolve()` | same as before, just restructured as an early return instead of `or`-chained into a single `raw` |
| `cwd_dir = Pathname.new(Dir.pwd).join(".boukensha"); return cwd_dir.to_s if cwd_dir.directory?` | `cwd_dir = Path.cwd() / ".boukensha"` / `if cwd_dir.is_dir(): return cwd_dir.resolve()` | new tier — checks the current *process* working directory only, no walking up parent directories the way `git` does |
| `Pathname.new(DEFAULT_DIR).expand_path.to_s` | `return DEFAULT_DIR.expanduser().resolve()` | `DEFAULT_DIR` is already `Path.home() / ".boukensha"`, an absolute path — `expanduser()` is a no-op here but kept for symmetry with the other two branches |

## `boukensha/agent.py` — `Agent.run`/`_wrap_up` change

Three call sites gain `self.context.add_message("assistant", text)` (or `msg`) immediately before
their `return`:

1. In `run()`'s main loop, right after `self.logger.turn_end(reason="completed", ...)`, before
   `return text`.
2. In `_wrap_up()`'s success path, right after `self.logger.turn_end(reason=reason, ...)`, before
   the final `return text`.
3. In `_wrap_up()`'s `except ApiError` fallback, right after `self.logger.turn_end(reason=reason,
   ...)`, before `return msg`.

`tests/test_agent.py` mocks `context`, so existing assertions (`context.add_message.assert_any_call(...)`)
are unaffected — they check specific calls occurred, not an exhaustive call list.

## `boukensha/client.py` — 401 handling

Immediately before the existing generic non-2xx raise (`if status is None or not (200 <= status <
300): raise ApiError(...)`), add a status-401-specific branch:

```python
if status == 401:
    raise ApiError("authentication failed (401) — check your API key")
```

## `boukensha/context.py` — `clear_messages`

```python
def clear_messages(self) -> None:
    self.messages = []
```

Ruby's bang-suffix (`clear_messages!`) has no Python naming equivalent (established convention —
Ruby's mutating-method-naming convention doesn't carry over; see `Config`/`Context`'s existing
non-bang methods throughout this port).

## Delta to apply to `python/08_the_repl_loop`

| Change | File(s) | Action |
|---|---|---|
| Fix directory typo | `python/08_the_relp_loop/` → `python/08_the_repl_loop/` | `git mv` (see open question 1) |
| Fix launcher target | `bin/python/08_the_repl_loop` | edit `cd` target from `07_the_run_dsl` to `08_the_repl_loop` |
| New version constant | `boukensha/version.py` | create, `VERSION = "0.8.0"` |
| New `Repl` class | `boukensha/repl.py` | create, per "The `Repl` primitive" above |
| New `repl()` entry point + version export | `boukensha/__init__.py` | add `repl()`, import/export `VERSION` and `Repl`, add both to `__all__` |
| `_resolve_dir` cwd tier | `boukensha/config.py` | edit, per mapping above |
| Persist assistant replies | `boukensha/agent.py` | edit, 3 call sites, per mapping above |
| 401-specific error | `boukensha/client.py` | edit, per mapping above |
| `clear_messages` | `boukensha/context.py` | add method |
| Rewritten example | `examples/example.py` | rewrite to call `boukensha.repl(configure=configure)`, `base_dir` pointed at `../../07_the_run_dsl`, `list_directory` result sorted |
| Bump description | `pyproject.toml` | `description` → `"— 08: the repl loop"` |
| Rewritten README | `README.md` | rewrite from Ruby's, correcting the stale bits found above (real banner, real running instructions, real `/quiet`-`/loud` caveat, real per-turn-`Agent`-construction caveat) |
| New tests | `tests/test_repl.py` | create — see open question 3 |
| New tests | `tests/test_boukensha_repl.py` | create, mirroring `tests/test_boukensha_run.py`'s shape for `run()` |
| Extended tests | `tests/test_config.py` | add cwd-tier `_resolve_dir` test(s) |
| Extended tests | `tests/test_agent.py` | add assertions that `context.add_message("assistant", ...)` fires on all 3 return paths |
| Extended tests | `tests/test_client.py` | add a 401-specific `ApiError` message test |
| Extended tests | `tests/test_context.py` | add `clear_messages` test |

## Decisions carried over (no longer open)

- **Copy-forward-then-delta workflow**, `uv` + `hatchling`, flat `boukensha/` layout,
  `.python-version` = 3.14, `ruff`/`isort`/`ty` via `uv run`, `pytest` in `tests/` — unchanged.
- **Port observed Ruby quirks/dead code faithfully rather than silently correcting or omitting
  them** — established by `02_the_registry`/`04_api_client`, reapplied here to `/quiet`+`/loud`
  being currently inert and to a fresh `Agent` being constructed every REPL turn (both things the
  Ruby README itself flags as open questions, not resolved here either).
- **No symbol/string key duality to port** — plain `str`/`dict.get` throughout, per `00_config`.
- **`except Exception`/`ValueError` as the direct analogs of Ruby's `StandardError`/`ArgumentError`**
  — established in `06_the_logger`/`tasks/base.py`.
- **The `configure: Callable[[RunDSL], None] | None` parameter name/shape**, decided in
  `07_the_run_dsl`'s plan for `run()` — reused verbatim for `repl()`, not re-litigated.
- **Never trust a Ruby README's example/output block at face value** — verify against actual code
  and a live run, per `02_the_registry` onward; reapplied extensively here given how many mismatches
  this particular README has.

## Open questions (please answer before implementation)

1. **Directory/launcher naming.** `python/08_the_relp_loop` (typo: transposed "rel"/"rep") is the
   directory already sitting in the tree, copied forward from `07_the_run_dsl`; the correct name,
   matching Ruby and every other step's convention, is `08_the_repl_loop`. Separately,
   `bin/python/08_the_repl_loop` already exists (unlike every prior step, where the launcher was
   the last thing added) but currently `cd`s into `07_the_run_dsl`, not any `08_*` directory.
   *Recommendation:* `git mv python/08_the_relp_loop python/08_the_repl_loop`, and fix the
   launcher's `cd` target to `08_the_repl_loop`, as the first implementation step — before touching
   any Python source, so nothing gets edited in a directory that's about to be renamed out from
   under it.
2. **Live-API verification depth.** A working Anthropic key is configured (used to capture the
   banner-only ground truth above, at no real cost — a piped `/exit` triggers no agent turn).
   *Recommendation:* once implemented, run `week1_baseline/bin/python/08_the_repl_loop` for real
   with a couple of piped lines (e.g. a real question, then `/clear`, then a follow-up that
   requires the pre-`/clear` context to answer correctly, then `/exit`) and compare against an
   equivalent live Ruby run, same "run both, diff the output" method as every prior step. This does
   spend a small amount of real API budget (a few short Haiku turns), same order of magnitude as
   `07_the_run_dsl`'s verification.
3. **Testing an interactive `input()` loop.** This is a genuinely new shape of thing to test in
   this port — no prior step has an actual blocking-read loop. *Recommendation:* in
   `tests/test_repl.py`, construct `Repl` with mocked `context`/`registry`/`builder`/`client`/
   `logger`, then patch `builtins.input` (via `monkeypatch.setattr` or `unittest.mock.patch`) with a
   `side_effect` list of canned lines terminated by raising `EOFError` (or a literal `"/exit"`), and
   assert on: `/help` prints `Repl.HELP` and doesn't call `agent.run`; `/quiet`/`/loud` call
   `boukensha.quiet()`/`loud()` (mocked/monkeypatched module functions) and don't call `agent.run`;
   `/clear` calls `context.clear_messages()` and resets the internal turn counter (assert the next
   `_logger.turn(n=...)` call after a `/clear` restarts at 1); an ordinary line calls
   `context.add_message("user", line)` then constructs an `Agent` and prints its `run()` result;
   `LoopError`/`ApiError` raised from a mocked `Agent.run()` are caught and printed as
   `[error] ...` without propagating out of `start()`; EOF (`side_effect` raising `EOFError`) and
   `"/exit"`/`"/quit"` both end the loop cleanly. `Agent` itself should be patched
   (`monkeypatch.setattr(repl_module, "Agent", ...)`) so `_run_turn` never does any real
   construction/network work.
4. **`tests/test_boukensha_repl.py` scope.** Mirroring `tests/test_boukensha_run.py`'s coverage of
   `run()` for the new `repl()` function is straightforward for everything through backend/API-key
   resolution and `configure` invocation (identical logic, copy-pasted), but `repl()`'s tail calls
   `Repl(...).start()`, which blocks on `input()` forever in a real terminal. *Recommendation:*
   patch `boukensha.Repl` itself (not `builtins.input`) in these tests, asserting `repl()`
   constructs it with the right resolved `backend`/`model`/`config_dir`/`version`/etc. and calls
   `.start()` once, plus that `logger.close()` fires via `finally` (including when `Repl()` or
   `.start()` raises) and that `KeyboardInterrupt` raised from `.start()` is caught and printed as
   `"\nInterrupted."` rather than propagating. Leave `input()`-level behavior entirely to
   `test_repl.py` (open question 3) — these two test files should not overlap in what they mock.
   - Use the recommendations for all four questions to execute the plan.

## Implementation steps (once questions above are answered)

1. `git mv python/08_the_relp_loop python/08_the_repl_loop`; fix `bin/python/08_the_repl_loop`'s
   `cd` target (open question 1).
2. Add `boukensha/version.py` with `VERSION = "0.8.0"`.
3. Add `clear_messages` to `boukensha/context.py`.
4. Add the cwd tier to `boukensha/config.py`'s `_resolve_dir`.
5. Add `context.add_message("assistant", ...)` at the three return points in `boukensha/agent.py`.
6. Add the 401-specific `ApiError` branch to `boukensha/client.py`.
7. Add `boukensha/repl.py` with `Repl`, per "The `Repl` primitive" above.
8. Add `repl()` to `boukensha/__init__.py`, per "`Boukensha.repl`" above; export `repl`, `Repl`,
   and `VERSION` via `__all__`.
9. Rewrite `examples/example.py` to call `boukensha.repl(configure=configure)`, update `base_dir`
   to point at `../../07_the_run_dsl`, sort `list_directory`'s result.
10. Rewrite `week1_baseline/python/08_the_repl_loop/README.md`, adapted from
    `@week1_baseline/ruby/08_the_repl_loop/README.md` but correcting the stale bits found above
    (running instructions, real banner, real `/quiet`+`/loud` and per-turn-`Agent` caveats, real
    `Logger#turn` behavior).
11. Update `pyproject.toml`'s `description` field to `"— 08: the repl loop"`.
12. Add `tests/test_repl.py` (open question 3); add `tests/test_boukensha_repl.py` (open
    question 4); extend `tests/test_config.py`, `tests/test_agent.py`, `tests/test_client.py`,
    `tests/test_context.py` per the table above.
13. Verify: `uv run pytest -v && make lint` (isort/ruff/ty) in
    `week1_baseline/python/08_the_repl_loop/`. Per open question 2, also run
    `week1_baseline/bin/python/08_the_repl_loop` and `week1_baseline/bin/ruby/08_the_repl_loop`
    live with matching piped input and compare actual output.
