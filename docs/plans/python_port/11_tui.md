# Python Port Plan · 11 · A Terminal UI

Status: implemented. All four open questions were answered with the recommended options
(`textual` as the TUI framework, small `Pilot`-based tests for `Tui`'s mechanical parts,
cooperative-cancellation via a `threading.Event` on `Agent`, and Ruby's exact ANSI hex palette).
`week1_baseline/python/11_tui/` now has `boukensha/tui.py`, the `Repl`/`Agent`/`boukensha.repl()`
deltas, tests, launcher, and README described below.

## Goal

Turn `week1_baseline/python/11_tui/` into a behavioral port of
`week1_baseline/ruby/11_tui/` (`@week1_baseline/ruby/11_tui/README.md` is the spec), copied
forward from `week1_baseline/python/10_standard_tool_library/`. Ruby's step wraps the existing
`Repl` in a full-screen four-zone terminal UI built on the `charm` gem (bubbletea + lipgloss +
bubbles). Python has no binding to those Go libraries, so this step is not a line-for-line port
like 00–10 were — it needs a Python TUI framework standing in for `charm`, with the *behavior*
(layout, keybindings, live progress, background turn execution) matched as closely as that
framework allows. See "Open questions" below; this is the one step so far where the porting
decision is architectural, not mechanical.

## How this plan was created

1. Confirmed `week1_baseline/python/11_tui/` does not exist yet — despite an empty
   `docs/plans/python_port/11_tui.md` already being present, no copy-forward has happened. (The
   user's initial framing — "we have a python 11_tui folder that's just a copy of the previous
   step" — doesn't match the filesystem; noting this since it means step 3 of the copy-forward
   workflow, not just the plan doc, is still pending.)
2. `diff -rq week1_baseline/ruby/10_standard_tool_library/ week1_baseline/ruby/11_tui/` (excluding
   `vendor`/`.bundle`/`Gemfile.lock`/`.gitignore`/`*.gem`) to find the exact file-level delta.
3. `diff -u` on every changed file (`Gemfile`, `boukensha.gemspec`, `version.rb`, `boukensha.rb`,
   `boukensha_loader.rb`, `lib/boukensha/mcp.rb`, `lib/boukensha/repl.rb`, `examples/example.rb`,
   `README.md`) plus a full read of the one new file, `lib/boukensha/tui.rb` (324 lines), and the
   new `patches/bubbletea/` directory.
4. Read `docs/plans/floating_artifacts/boukensharc.md` to confirm which parts of the Ruby delta
   are global-executable/gem-packaging machinery with **no Python analogue** (this port has no
   `09_global_executable` and never will), vs. which parts are real `Boukensha.repl` API surface
   that Python's `boukensha/__init__.py` must track regardless.
5. Read `docs/plans/python_port/10_standard_tools.md` as the most recent worked example, and
   confirmed against the current `python/10_standard_tool_library` source that its 2026-07-31 audit
   fixes are already in place (in particular: `boukensha/mcp.py`'s `MCPClient.__init__` already
   strips `RBENV_*`/rewrites `PATH` — the exact fix that shows up as new in
   `ruby/11_tui/lib/boukensha/mcp.rb`'s diff. That fix is **not** a step-11 delta for Python; it
   already landed early).
6. Read `python/10_standard_tool_library`'s `boukensha/repl.py`, `boukensha/logger.py`, and
   `boukensha/__init__.py` in full to see what's already public/private and what `Logger.subscribe`
   already supports (it already exists — another piece of step 11 that's a no-op for Python).
7. Confirmed no Ruby tests exist for `Tui` (none of `ruby/11_tui` has a `spec/` — full-screen
   interactive UIs aren't unit-tested there), which affects the test-scope open question below.

## Starting point (what's already in place, unchanged)

Everything under `python/10_standard_tool_library/` not listed in the delta table below carries
forward untouched, because its Ruby source is byte-identical between `10_standard_tool_library`
and `11_tui` (or, for `mcp.py`, already fixed ahead of schedule):

- `boukensha/mcp.py` — **no change**. Ruby's `mcp.rb` delta (RBENV/PATH env stripping) is already
  present in Python from the step-10 audit; confirmed by reading both files side by side.
- `boukensha/logger.py` — **no change**. `Logger.subscribe` already exists and behaves exactly like
  Ruby's new `subscribe(&block)` (broadcast every `_write_log` event to subscriber callbacks, in
  addition to writing the JSONL line).
- `boukensha/agent.py`, `context.py`, `registry.py`, `client.py`, `prompt_builder.py`,
  `message.py`, `errors.py`, `tool.py`, `config.py`, `run_dsl.py`, `tasks/`, `backends/` — no Ruby
  counterpart changed, so no Python change.
- `tests/*` other than `tests/test_repl.py` and `tests/test_boukensha_repl.py` — unaffected.
- `examples/example.py` — Ruby's `examples/example.rb` changed only its header comment (explicitly
  "carried over unchanged from step 10 — it doesn't exercise the TUI"); the actual demo logic
  (`Boukensha.run(task: "...", working_dir: false)`, MUD-only) is untouched. Python's
  `examples/example.py` needs the same treatment: no logic change. (Separately: Python's current
  `example.py` already diverges from Ruby's by calling `boukensha.repl(working_dir=base_dir)`
  instead of a one-shot `boukensha.run(...)` MUD task — that divergence predates this step, was
  already audited as "confirmed correct" in the step-10 plan, and is out of scope to fix here. It
  does have one convenient side effect for this step: once `tui=True` becomes `repl()`'s default,
  running the existing launcher will exercise the new TUI with zero code changes to `example.py`.)

## The exact delta (from `diff -u` between `ruby/10_standard_tool_library` and `ruby/11_tui`)

| Ruby file | Change | Python-relevant? |
|---|---|---|
| `.ruby-version`, `Gemfile` (+`gem "charm"`), `boukensha.gemspec` (+`charm` dependency), `patches/bubbletea/*` | Ruby-specific packaging: pins a native gem and a source-patch workflow for a C-extension bug in the `bubbletea` gem. | No — no Python equivalent exists or is needed; Python's chosen TUI library is a pure-Python (or wheel-distributed) package installed the normal `uv add` way, with no analogous native-patch problem. |
| `lib/boukensha_loader.rb` (`--no-tui` CLI flag → `repl_opts = { tui: !no_tui }`) | Global-executable CLI flag parsing. | Per `docs/plans/floating_artifacts/boukensharc.md`: the loader file itself has no Python analogue (no `09_global_executable` port), but the `Boukensha.repl(tui:)` keyword it's *reacting to* is real API surface — that part **is** a Python delta (see below). |
| `lib/boukensha/version.rb` (`0.10.0` → `0.11.0`) | Version bump. | Yes — bump `version.py` to match. |
| `lib/boukensha.rb` | Removed `@quiet`/`quiet!`/`loud!`/`quiet?` entirely (not just from the REPL). Added `tui:` keyword (default `true`) to `Boukensha.repl`; when true and `Tui` is defined, wraps the `Repl` in `Tui.new(repl).start` instead of calling `repl.start` directly. | Yes — both parts apply to `boukensha/__init__.py`. |
| `lib/boukensha/repl.rb` | Removed `/quiet`/`/loud` commands and the `HELP` lines for them. Refactored so `Repl` no longer hard-codes `puts`/`$stdin.gets`: added `on_output(&block)` (routes all output through a callback instead of stdout when set), `handle_command(input)` (returns `:quit`/`:command`/`nil`, replaces the inline `case` in `start`), and exposed `banner`, `logger`, `context`, `model`, `version` as public readers. `start` itself is now a thin loop calling `handle_command`/`run_turn` (renamed from private `run_turn` — was already public in Ruby, already public in Python too). | Yes — `boukensha/repl.py` needs the equivalent refactor. |
| `lib/boukensha/mcp.rb` | RBENV/PATH env-stripping robustness fix. | No — already present in `boukensha/mcp.py` (see Starting point). |
| **`lib/boukensha/tui.rb`** (new, 324 lines) | New `Tui` class: wraps a `Repl`, drives a bubbletea `Runner` event loop, renders a 4-zone layout (scrollable conversation viewport, live progress line, input box, status line), runs each agent turn on a background `Thread`, and uses `Repl#logger.subscribe` to update live progress (spinner/iteration/tokens/tool-call-count) without polling. | Yes — this is the actual headline content of the step; needs a new `boukensha/tui.py`, using a real Python TUI library in place of `charm`. |
| `examples/example.rb` | Comment-only change (see Starting point). | Comment-only, optional to mirror. |
| `README.md` | Full rewrite: step title, new "What's new in this step" section documenting `Tui`, the `tui:` keyword, the `Repl` refactor, `Logger#subscribe`, and updated run instructions. | Yes — `README.md` needs an equivalent rewrite adapted for Python (see below on how the TUI is actually launched, since there's no global executable). |

## Delta to apply to `python/11_tui`

| Change | File(s) | Action |
|---|---|---|
| Copy forward | `week1_baseline/python/11_tui/` | `rsync -a` from `python/10_standard_tool_library/`, excluding `.venv/`/`__pycache__/`/`.ruff_cache/`/`.pytest_cache/` (not yet done — see "How this plan was created" #1). |
| Version bump | `boukensha/version.py` | `VERSION = "0.11.0"`. |
| Remove quiet/loud | `boukensha/__init__.py` | Delete `_quiet`, `quiet()`, `loud()`, `is_quiet()`, and their `__all__` entries. Confirmed via grep that `is_quiet()` has no consumer anywhere (it never actually gated any output in either language) — safe to delete outright, not just deprecate. |
| Add `tui:` keyword | `boukensha/__init__.py` | `repl()` gains `tui: bool = True`. When true, construct `Tui(repl_instance)` and call `.start()` on it instead of calling `repl_instance.start()` directly (mirrors Ruby's `if tui && defined?(Tui)`; Python has no `defined?` — just import `Tui` unconditionally at module top like every other class here, since `tui.py` will always exist once this step lands). |
| Refactor `Repl` | `boukensha/repl.py` | Remove `/quiet`, `/loud` cases and their `HELP` lines. Extract `handle_command(self, line: str) -> str \| None` (returns `"quit"`, `"command"`, or `None`) from the inline `match` in `start()`. Add `on_output(self, callback: Callable[[str], None]) -> None` storing the callback; add a private `_output(self, s: str) -> None` helper used everywhere `print(...)` currently appears in `start`/`_run_turn`/`banner`, dispatching to the callback if set, else `print`. Rename `_banner`/`_run_turn` to public `banner`/`run_turn` (drop the leading underscore — Ruby exposes both). Add `@property` readers for `logger`, `context`, `model`, `version` (currently `_logger`/`_context`/`_model`/`_version`, all already stored, just need public accessors). |
| New TUI module | `boukensha/tui.py` (new) | Implement `Tui`, matching `lib/boukensha/tui.rb`'s behavior using the chosen framework (see open question 1). See "Ruby → Python behavior mapping" for the per-concept translation. |
| Export `Tui` | `boukensha/__init__.py` | Add `from .tui import Tui`; add `"Tui"` to `__all__`. |
| Dependency | `pyproject.toml` | `description` → `"— 11: a terminal UI"`. Add the chosen TUI framework via `uv add <package>` (adds it to `[project.dependencies]` with whatever version `uv` resolves — don't hand-pick a version number). |
| Tests | `tests/test_repl.py` | Delete `test_quiet_and_loud_toggle_module_state_without_running_agent`. Add coverage for `on_output` (callback receives banner/turn output/goodbye instead of stdout), `handle_command` (all four cases + non-command passthrough returning `None`), and the public `logger`/`context`/`model`/`version` readers. Existing stdout-based tests (`capsys`) should still pass unchanged since `Repl()` with no `on_output` registered still prints. |
| Tests | `tests/test_boukensha_repl.py` | Add a test that `repl(tui=False, ...)` calls `Repl.start()` directly (no `Tui` involved) — the one `boukensha.repl()`-level behavior this step actually changes. Whether to also test the `tui=True` default path is open question 2. |
| Tests | `tests/test_tui.py` (new) | Scope depends on open question 2. |
| Launcher | `week1_baseline/bin/python/11_tui` (new) | Standard shape, identical to every other step's launcher (`cd .../python/11_tui && uv run python examples/example.py`). |
| README | `README.md` | Rewrite adapted from `ruby/11_tui/README.md`: same "what's new" content (Tui, `tui:` keyword, `Repl` refactor, `Logger.subscribe`), but Python run instructions. Since there's no Python global executable, "run it" instructions point at `week1_baseline/bin/python/11_tui` (which now launches the TUI by default via `example.py`'s existing `boukensha.repl(...)` call) rather than Ruby's `gem install` + `boukensha`/`boukensha --no-tui` instructions — call out that `boukensha.repl(tui=False, ...)` is the Python equivalent of `--no-tui` for anyone embedding this in their own script. |

## Ruby → Python behavior mapping

| Ruby (`charm`: bubbletea + lipgloss + bubbles) | Python equivalent | Notes |
|---|---|---|
| `Bubbletea::Runner.new(self, alt_screen: true, input_timeout: 50, fps: 30).run` — an Elm-architecture (`init`/`update`/`view`) full-screen event loop | A `textual.app.App` subclass's `run()` (see open question 1 for why `textual` is the recommendation) | Textual's reactive/widget-driven model isn't identical to bubbletea's Elm architecture, but it's the closest thing Python has to "a full-screen terminal framework with a real event loop, alt-screen, and a built-in widget library," which is what `charm` provides as a bundle. |
| `Bubbles::Viewport` (scrollable pane, `.content=`, `.goto_bottom`) | Textual's `RichLog` (or a `VerticalScroll` containing a `Static`) | `RichLog.write(...)` + `auto_scroll=True` covers "append text, keep pinned to bottom" directly. |
| `Bubbles::TextArea` used at `height = 1` (effectively a single-line input, not a real multi-line editor) | Textual's `Input` widget | Ruby reaches for `TextArea` only because `charm`'s `bubbles` binding doesn't expose a plainer single-line widget; Python's `Input` is the direct, simpler match for what's actually used (single line, `Enter` submits, no multi-line editing exercised anywhere in `tui.rb`). |
| `Lipgloss::Style.new.foreground(...).background(...).bold(true)` | Rich `Style`/`Text` objects (`rich.style.Style(color=..., bgcolor=..., bold=True)`), or Textual CSS (`.tcss`) classes for the always-on status/progress bars | Textual ships Rich under the hood, so both are "native" — Rich `Style` for one-off inline coloring (mirrors `lip(...)` being called ad hoc), Textual CSS for the persistent full-width bars (status line, progress line), since those map naturally onto styled `Static` widgets. |
| `Bubbletea.tick(TICK_MS / 1000.0) { TickMsg.new }`, re-armed each `update` | `textual.timer` via `self.set_interval(TICK_MS / 1000, self._on_tick)` | Textual's interval timer is the direct analog; no need to hand-roll a message type and re-arm it — `set_interval` is self-repeating. |
| `Thread.new { @repl.run_turn(input) }` (turn runs on a background OS thread so the UI stays responsive) | Textual's `self.run_worker(self._run_turn_blocking, thread=True)` | Textual workers with `thread=True` run a sync function on a worker thread, same shape as Ruby's `Thread.new` — `Repl.run_turn` is blocking, synchronous, unchanged. |
| `@events = Queue.new`; `Repl#logger.subscribe { |event| @events << event }`; drained on every `TickMsg` | Python `queue.Queue`, same `logger.subscribe(lambda event: events.put(event))`, drained in the tick callback | Direct port — `Logger.subscribe` already exists on the Python side (see Starting point). |
| `@turn_thread.raise(Interrupt)` on `Esc` — Ruby can (unsafely but pragmatically) inject an exception into a running thread at any point, including mid-HTTP-call | **No direct Python equivalent** — `threading.Thread` cannot be asynchronously interrupted. | This is the one real behavior gap; see open question 3 for the two options and a recommendation. |
| `handle_key(msg)` on `Bubbletea::KeyMessage`, matching `msg.name` (`"ctrl+c"`, `"esc"`, `"pgup"`, ...) | Textual's `on_key(self, event: events.Key)`, matching `event.key` (Textual's key names: `"ctrl+c"`, `"escape"`, `"pageup"`, ...) | Naming differs slightly (`"esc"` vs `"escape"`, `"pgup"` vs `"pageup"`) — use Textual's actual names, don't copy Ruby's strings verbatim. |

## Decisions carried over (no longer open)

- Copy-forward-then-delta workflow, `uv` + `hatchling`, flat `boukensha/` layout, `.python-version`
  = 3.14, `ruff`/`isort`/`ty` via `uv run`, `pytest` in `tests/`.
- Port observed Ruby behavior faithfully rather than silently improving on it — reapplied here as:
  match the *4-zone layout and keybinding set*, not necessarily every internal implementation
  detail of `charm`, since there is no line-for-line equivalent to port.
- Tools/backends/agent loop are all unaffected by this step; nothing there changes.
- `Logger.subscribe` and `mcp.py`'s RBENV env-stripping fix are already in place from step 10's
  audit — do not re-add them.

## Open questions (please answer before implementation)

1. **Which Python TUI library replaces `charm`?** Recommendation: **`textual`**. It's the closest
   Python analogue to the bubbletea+lipgloss+bubbles bundle — a real full-screen async event loop,
   a built-in widget library (`RichLog`, `Input`, etc.), and CSS-based styling — actively maintained
   and installable as a normal pure-Python(-ish) wheel via `uv add textual`, with none of the
   native-extension patching Ruby's `bubbletea` gem needs. Alternatives considered: `urwid` (older,
   more low-level, no built-in styling language as ergonomic as lipgloss/Textual CSS) and
   `prompt_toolkit` (better suited to single-line/REPL-style prompts than a 4-zone full-screen
   layout with live-updating regions). If you'd rather use one of these — or something else —
   say so; the "Ruby → Python behavior mapping" table above would need corresponding edits.

2. **Test scope for `Tui` itself.** Ruby ships zero tests for `Tui` (nothing under `ruby/11_tui`
   tests it — full-screen interactive UIs aren't part of this project's Ruby test posture).
   Textual, unlike `charm`, ships a first-class headless test harness (`App.run_test()` /
   `Pilot`, which can simulate keypresses and assert on screen state without a real terminal).
   Recommendation: add a **small** `tests/test_tui.py` using `run_test()`/`Pilot` for the
   mechanical, low-risk parts only — e.g. "Enter with non-empty input clears the input box and
   appends to the conversation log," "Ctrl+L clears history," "Ctrl+C quits" — but skip trying to
   assert on exact rendered styling/layout pixels, since that's high-maintenance and Ruby sets no
   precedent for testing it at all. If you'd rather match Ruby exactly (zero `Tui` tests, only test
   the refactored `Repl` methods it depends on), that's a smaller and equally defensible scope —
   your call.

3. **How to handle `Esc`-to-interrupt given Python threads can't be asynchronously raised into.**
   Two options:
   - **(a) Cooperative cancellation (recommended).** Add a small `threading.Event`-based interrupt
     flag; `Agent.run()`'s existing `while True` loop (one clean iteration boundary already exists,
     `agent.py`'s `run()`) checks it at the top of each iteration and raises a
     `KeyboardInterrupt`-equivalent to unwind cleanly. This requires a small, optional constructor
     argument on `Agent` (e.g. `interrupt: threading.Event | None = None`), which is a step outside
     "only touch `tui.py`/`repl.py`" but keeps the *user-visible* behavior faithful: pressing `Esc`
     actually stops the agent loop, just at the next iteration boundary instead of instantly
     mid-HTTP-call the way Ruby's unsafe `Thread#raise` can.
   - **(b) Cosmetic-only interrupt.** `Esc` immediately hides the progress line and appends
     `[interrupted]` to the conversation in the UI, but the background thread keeps running to
     completion in the background and its eventual result is discarded when it finishes. No
     `Agent` changes needed at all, but the interrupt is UI-only — the underlying turn isn't
     actually stopped early, which is a real behavior gap from Ruby.

   Recommendation: **(a)** — it's a small, well-scoped addition to `Agent` and preserves the actual
   guarantee ("Esc stops the running turn"), not just its appearance.

4. **Whether to mirror Ruby's exact ANSI hex palette (`ANSI_COLORS`) or use Textual's named
   theme colors.** Recommendation: port the hex values (`cyan`/`bright_black`/`green`/`white`)
   as-is — they're arbitrary but Ruby is explicit about them, and reusing the same values keeps the
   two TUIs visually equivalent rather than merely functionally equivalent.
   - Please use all recommendations that were provided in each question.

## Implementation steps (once questions above are answered)

1. `rsync -a --exclude='.venv/' --exclude='__pycache__/' --exclude='.ruff_cache/' --exclude='.pytest_cache/' week1_baseline/python/10_standard_tool_library/ week1_baseline/python/11_tui/`
2. `boukensha/version.py` → `"0.11.0"`.
3. `boukensha/__init__.py`: remove `quiet`/`loud`/`is_quiet`/`_quiet`; add `tui: bool = True` to
   `repl()`; import and dispatch to `Tui`.
4. `boukensha/repl.py`: remove `/quiet`/`/loud`; add `on_output`, `handle_command`, public
   `banner`/`run_turn`/`logger`/`context`/`model`/`version`.
5. `boukensha/tui.py`: implement `Tui` per the mapping table and whichever answers open questions
   1–4 land on.
6. `uv add <chosen TUI library>` inside `python/11_tui/`; bump `pyproject.toml`'s `description`.
7. `tests/test_repl.py`, `tests/test_boukensha_repl.py`, `tests/test_tui.py` per the delta table.
8. `week1_baseline/bin/python/11_tui` launcher (new, standard shape).
9. `README.md` rewrite.
10. Run `week1_baseline/bin/ruby/11_tui` (build+install the gem per its README, or `bundle exec
    bin/boukensha`) and `week1_baseline/bin/python/11_tui` side by side. Unlike prior steps, this
    is a full-screen interactive UI, not line-oriented stdout — "diff the output" doesn't apply
    literally. Verify instead: layout matches (4 zones in the right order), keybindings all work
    (`Enter`, `Esc`, `Ctrl+L`, `PgUp`/`PgDn`, `Ctrl+C`/`Ctrl+D`), the progress line updates live
    during a real turn, and the status line's fields (version/model/context/tools/clock) match.
    Also run `uv run pytest -v && make lint` inside `python/11_tui/`.
