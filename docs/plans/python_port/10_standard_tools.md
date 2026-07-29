Status: DRAFT — open questions below must be answered before implementation starts.

## Goal

Turn `week1_baseline/python/10_standard_tool_library/` (currently an exact clone of
`python/08_the_repl_loop`, still describing "Step 8" throughout) into a port of
`@week1_baseline/ruby/10_standard_tool_library/`, by applying the delta Ruby made getting there —
same copy-prior-step-then-apply-delta workflow used for every step so far.

**Naming wrinkle:** Ruby's `10_standard_tool_library` is two steps past Ruby's own `08_the_repl_loop`
— Ruby has an intervening `09_global_executable` step that Python never ported (no
`python/09_global_executable` directory or plan exists, and none is being added now). So the
correct "prev" comparison for finding *Python's* delta is not Ruby's 09→10 diff, it's the
**cumulative** Ruby 08→10 diff — everything Ruby changed across both steps that Python hasn't
absorbed yet. That's what this plan is built from (`diff -rq` and `diff -u` were run directly
between `ruby/08_the_repl_loop` and `ruby/10_standard_tool_library`, skipping past 09 entirely).

This step adds two new tool-registration modules — `Boukensha::Tools::FileSystem` (`pwd`,
`list_directory`, `read_file`, `write_file`, `delete_file`, `search_files`, all sandboxed to a
`working_dir` root) and `Boukensha::Tools::Shell` (`run_command`, with a timeout and an optional
executable allow-list) — and wires both into `Boukensha.run`/`Boukensha.repl` via new
`working_dir:`/`allowed_commands:`/`shell_timeout:` keyword arguments, auto-registered whenever
`working_dir` is truthy (the default is the process's cwd; pass `working_dir: false` to opt out).
`Context` gains a `working_dir` attribute recording the resolved root. Two unrelated regressions
ride along in the same cumulative diff — `Config#resolve_dir` **drops** the `./.boukensha`
cwd-override tier `08_the_repl_loop` added, and `Client` **drops** the 401-specific `ApiError`
message `08_the_repl_loop` added — both are real reversions in Ruby's own history, not artifacts of
skipping step 09, and must be ported faithfully (see "Two reversions" below). `VERSION` bumps to
`"0.10.0"`.

Ruby's 10 also ships a third tool module, `Boukensha::Tools::Mud` (~480 lines, 25 tools wrapping a
separate `mud_manager` gem — a ~690-line raw-socket CircleMUD telnet client/primitives library
under `week0_explore/mud_manager/`), plus Ruby-packaging changes unrelated to the tool-library
theme (`bin/boukensha`, `boukensha.gemspec`, `lib/boukensha_loader.rb`, a `gemspec`/`mud_manager`
path dependency added to `Gemfile`). **Recommendation: descope both from this Python step** — see
"Open questions" below.

## How this plan was created

1. Confirmed `week1_baseline/python/10_standard_tool_library/` is byte-identical to
   `week1_baseline/python/08_the_repl_loop/` (still says "Step 8" in its README and
   `pyproject.toml`'s `description`).
2. Diffed `@week1_baseline/ruby/08_the_repl_loop/` directly against
   `@week1_baseline/ruby/10_standard_tool_library/` (`diff -rq`, excluding `vendor/`, `.bundle/`,
   `Gemfile.lock`, `.gitignore`) — deliberately skipping the intermediate `09_global_executable`
   diff, since Python needs the *cumulative* delta, not either half separately. Changed/new:
   `Gemfile`, `README.md`, `bin/` (new dir), `boukensha.gemspec` (new), `examples/example.rb`,
   `lib/boukensha/client.rb`, `lib/boukensha/config.rb`, `lib/boukensha/context.rb`,
   `lib/boukensha/repl.rb`, `lib/boukensha/tools/` (new dir: `file_system.rb`, `shell.rb`,
   `mud.rb`), `lib/boukensha/version.rb`, `lib/boukensha.rb`, `lib/boukensha_loader.rb` (new).
   `lib/boukensha/agent.rb`, `errors.rb`, `logger.rb`, `registry.rb`, `tool.rb`, `message.rb`,
   `run_dsl.rb`, every `backends/*.rb`, `tasks/base.rb`, `tasks/player.rb`: unchanged,
   byte-identical.
3. Read every changed/new file in full with precise `diff -u` against the 08 baseline:
   `lib/boukensha.rb`, `lib/boukensha/config.rb`, `lib/boukensha/context.rb`,
   `lib/boukensha/repl.rb`, `lib/boukensha/client.rb`, `lib/boukensha/version.rb`, `Gemfile`,
   `examples/example.rb`. Read the three new `lib/boukensha/tools/*.rb` files whole, plus
   `lib/boukensha_loader.rb`, `boukensha.gemspec`, and skimmed `bin/boukensha`'s existence (not its
   contents in depth — packaging-only, see open questions).
4. Read the new Ruby step's `README.md` in full. It documents `Tools::FileSystem` and
   `Tools::Shell` in detail but **does not mention `Tools::Mud` at all**, despite `Mud` being fully
   wired into `boukensha.rb` and being the *entire subject* of the step's own `examples/example.rb`
   (a MUD-exploration demo, not a filesystem one). This is a stronger-than-usual version of the
   "README doesn't match the code" pattern flagged in nearly every prior step's plan — here the
   README doesn't just misdescribe a feature, it omits one that the example script is built
   entirely around.
5. Checked `week0_explore/` for any existing Python equivalent of the `mud_manager` gem (raw
   socket session management + CircleMUD command primitives). None exists —
   `week0_explore/explore_architecture/04_n8n/mud.py` is a superficially similar-sounding file but
   is architecturally unrelated (drives a `tmux`+`telnet` subprocess for an n8n bridge, not a
   socket-level session/primitives library) and isn't a usable substitute.
6. Read the current Python scaffold in full — `boukensha/__init__.py` (`run`/`repl`),
   `boukensha/config.py`, `boukensha/context.py`, `boukensha/client.py`, `boukensha/repl.py`,
   `boukensha/registry.py`, `boukensha/tool.py`, `examples/example.py`, relevant `tests/` files —
   to confirm exact existing signatures/conventions this step's new code must plug into. Confirmed
   Python's `config.py`/`test_config.py` and `client.py`/`test_client.py` currently *have* the
   cwd-tier and 401-message behavior (ported correctly in `08_the_repl_loop`), which is exactly what
   Ruby's cumulative 08→10 diff removes — so removing them here is a real, deliberate port, not
   dead work.

## Starting point (what's already in place, unchanged)

`week1_baseline/python/10_standard_tool_library/` is currently byte-identical to
`week1_baseline/python/08_the_repl_loop/`. These files need **no changes** because their Ruby
originals are identical between `08_the_repl_loop` and `10_standard_tool_library`:

- `boukensha/agent.py`, `boukensha/errors.py`, `boukensha/logger.py`, `boukensha/registry.py`,
  `boukensha/tool.py`, `boukensha/message.py`, `boukensha/run_dsl.py`
- `boukensha/backends/base.py`, `.../anthropic.py`, `.../gemini.py`, `.../ollama.py`,
  `.../ollama_cloud.py`, `.../openai.py`
- `boukensha/tasks/base.py`, `boukensha/tasks/player.py`, `boukensha/tasks/__init__.py`
- `boukensha/prompt_builder.py`, `prompts/system.md`
- `tests/test_agent.py` (no new assertions needed — `Agent` itself is untouched),
  `tests/test_backends.py`, `tests/test_logger.py`, `tests/test_message.py`,
  `tests/test_prompt_builder.py`, `tests/test_registry.py`, `tests/test_run_dsl.py`,
  `tests/test_tasks.py`, `tests/test_tool.py`
- `.gitignore`, `Makefile`, `.python-version`

## Two reversions (port faithfully, not bugs to "fix")

Both of these are Ruby's own real cumulative changes across 08→10 (landed somewhere in the
skipped-in-Python `09_global_executable` step), not artifacts of this plan's diffing method. Same
principle as prior steps' "port observed Ruby quirks faithfully" guidance — apply here to the
*removal* of two features, not just to keeping odd ones.

**`Config._resolve_dir` loses the cwd tier.** Ruby's `resolve_dir` goes from a 3-tier
env-var/cwd/home lookup back down to 2-tier (env-var-or-default):

```python
def _resolve_dir(self) -> Path:
    env_dir = os.environ.get("BOUKENSHA_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return DEFAULT_DIR.expanduser().resolve()
```

The module docstring/comment above `DEFAULT_DIR` in `config.py` (currently describing 3 tiers)
needs to drop back to 2, matching Ruby's own updated comment.

**`Client.call` loses the 401-specific message.** The `if status == 401: raise ApiError(...)`
branch is deleted; a 401 now falls straight through to the existing generic
`if status is None or not (200 <= status < 300)` raise, same as any other non-2xx/non-retryable
status.

## The `Tools::FileSystem` and `Tools::Shell` primitives

New package `boukensha/tools/` (`boukensha/tools/__init__.py` — empty or minimal, matching how
`boukensha/backends/` and `boukensha/tasks/` are already structured as sub-packages).

### `boukensha/tools/file_system.py`

| Ruby | Python | Notes |
|---|---|---|
| `module FileSystem; def self.register(registry, working_dir:)` | `def register(registry: Registry, *, working_dir: str \| Path) -> None:` (module-level function, not a class — matches the "duck-typed module of behavior" shape already used for `Tools::FileSystem`/`Shell` having no instance state) | |
| `root = File.expand_path(working_dir)` | `root = Path(working_dir).expanduser().resolve()` | |
| `resolve = ->(path) { ... }` closure doing traversal-guard math | inner `def _resolve(path: str) -> Path \| str:` closure (or nested function) returning either the resolved `Path` or an `"error: ..."` string, mirroring Ruby's own "return either a real value or an error string" convention (already established throughout this port — tools return strings, they don't raise, so the agent sees the error and can adapt) | `absolute == root or absolute.is_relative_to(root)` is the direct Python equivalent of Ruby's `absolute == root \|\| absolute.start_with?("#{root}/")` guard |
| `registry.tool "pwd", ...` | `registry.tool("pwd", description=..., parameters={}, block=lambda: str(root))` | |
| `registry.tool "list_directory", ...` — `Dir.entries(target).reject{".","..""}.sort.map{dir? "#{name}/" : name}` | `sorted(p.name + "/" if p.is_dir() else p.name for p in target.iterdir())`, joined `"\n"`, or `"(empty)"` | Ruby's `Dir.entries` includes `.`/`..` which get filtered; `Path.iterdir()` never yields them, so the reject step has no Python equivalent to port — this is a simplification, not a gap |
| `registry.tool "read_file", ...` | reads via `target.read_text()`, catches `OSError` → `f"error: {e}"` | |
| `registry.tool "write_file", ...` — `FileUtils.mkdir_p(dirname); File.write; "ok: wrote N bytes to REL"` | `target.parent.mkdir(parents=True, exist_ok=True)`; `target.write_text(content)`; `f"ok: wrote {len(content.encode())} bytes to {target.relative_to(root)}"` | `content.bytesize` → `len(content.encode())` (byte count, not char count — matters for non-ASCII) |
| `registry.tool "delete_file", ...` | `target.unlink()`; catch `OSError` | |
| `registry.tool "search_files", ...` — builds a glob, compiles a `Regexp`, walks matches | `Path.rglob(glob)` (or `target.glob(glob)` if `target` is the dir itself) filtered to files, `re.compile(pattern)`, `re.error` caught → `"error: invalid pattern: {e}"` | Ruby's `Regexp.new(pattern)` (Onigiruma syntax) vs Python's `re` module — not a 1:1 syntax match for every regex feature, but this port has never attempted cross-engine regex fidelity elsewhere either; document the same caveat implicitly by not claiming exact parity |

All six tools' `description:` strings port verbatim (they're user/agent-facing text, not code).

### `boukensha/tools/shell.py`

| Ruby | Python | Notes |
|---|---|---|
| `def self.register(registry, working_dir:, timeout: 30, allowed_commands: nil)` | `def register(registry: Registry, *, working_dir: str \| Path, timeout: int = 30, allowed_commands: list[str] \| None = None) -> None:` | |
| allow-list guard: `command.strip.split(/\s+/).first` checked against `allowed_commands.map(&:to_s)` | `shlex.split(command)[0]` (or plain `command.split()[0]` — Ruby's `split(/\s+/)` is whitespace-only, no quoting awareness, so `command.split()[0]` is the more faithful direct port; don't reach for `shlex` unless quoting turns out to matter) against `allowed_commands` | |
| `Open3.capture2e(command, chdir: root)` wrapped in `Timeout.timeout(timeout)` | `subprocess.run(command, shell=True, cwd=root, capture_output=True, timeout=timeout, text=True)` combining stdout+stderr — Ruby's `capture2e` merges both streams into one; Python's `subprocess.run` keeps them separate by default, so merge explicitly (`stdout=subprocess.STDOUT` when using `Popen`, or concatenate `result.stdout + result.stderr` after the fact) | `shell=True` is required to match Ruby's `Open3.capture2e(command, ...)` behavior of running the string through a shell (enables `&&`, pipes, globbing the same way the Ruby original does) — this is inherent to porting "run this shell command string" faithfully, not a new vulnerability introduced by the port; the *allow-list* is the mitigation both languages rely on |
| `rescue Errno::ENOENT` / `rescue Timeout::Error` / generic `rescue` | `except FileNotFoundError` / `except subprocess.TimeoutExpired` / `except OSError` | |
| exit-code/empty-output formatting | `f"{output}" + (f"\n[exit {code}]" if code != 0 else "")`, `"(no output)"` when stripped output is empty | |

## `Context.working_dir`

```python
def __init__(self, task: type[Base] | None, system: str | None = None, working_dir: str | Path | None = None) -> None:
    ...
    self.working_dir = Path(working_dir).expanduser().resolve() if working_dir else None
```

Add `working_dir` to the `__str__`/`__repr__`? No — Ruby's `to_s` doesn't include it either (only
`task`/`turns`/`tools`), so don't add it to `Context.__str__` either. Straight attribute add, no
other behavior change.

## `boukensha/__init__.py` — `run()`/`repl()` new keyword arguments

Both functions gain the same three new parameters, applied identically (this port already
duplicates `run()`'s backend-resolution block into `repl()` verbatim per `07_the_run_dsl`/
`08_the_repl_loop`'s precedent — continue that copy-paste rather than factoring out a shared
helper, matching "don't introduce abstractions beyond what the task requires"):

| Ruby | Python | Notes |
|---|---|---|
| `working_dir: Dir.pwd` | `working_dir: str \| Path \| Literal[False] \| None = None`, resolved inside the function body: `if working_dir is None: working_dir = Path.cwd()` | **New pitfall, not covered by prior steps:** Ruby re-evaluates `Dir.pwd` fresh on *every call* as the default expression; Python evaluates a `def`'s default expression once, at import time, so `working_dir: Path = Path.cwd()` as a literal default would silently freeze to whatever the cwd was when `boukensha/__init__.py` was first imported — stale if the caller `chdir`s afterward. Same "resolve inside the body" fix as the already-known mutable-default pitfall, but for a different underlying reason (call-time vs. def-time evaluation, not mutability) — worth its own row here since it's easy to conflate with the mutable-default case and reach for the wrong justification |
| `allowed_commands: nil` | `allowed_commands: list[str] \| None = None` | plain optional list, no new pitfall |
| `shell_timeout: 30` | `shell_timeout: int = 30` | literal int default, safe as-is |
| `if working_dir; Tools::FileSystem.register(...); Tools::Shell.register(...); end` | `if working_dir: tools.file_system.register(registry, working_dir=working_dir); tools.shell.register(registry, working_dir=working_dir, timeout=shell_timeout, allowed_commands=allowed_commands)` | placed right after `registry = Registry(ctx)`, before the `if configure is not None` block — matches Ruby's ordering (tools registered before user's `configure`/`instance_eval` block runs, so user-registered tools can be added alongside, and in principle override, the standard ones) |
| `ctx = Context.new(task: task_class, system: system, working_dir: working_dir)` | `ctx = Context(task=task_class, system=system, working_dir=working_dir if working_dir else None)` | pass the *resolved* `working_dir` (or `None` when the caller passed `False`) — mirrors Ruby passing whatever `working_dir` currently holds (`Dir.pwd`-or-caller-value, never `false` itself reaching `Context.new` un-guarded... actually Ruby *does* pass `false` through un-guarded here; Ruby's `Context#initialize` does `@working_dir = working_dir ? File.expand_path(working_dir) : nil`, so `false` naturally maps to `nil` there too) | keep the same "let the falsy-check happen in `Context.__init__`" shape rather than pre-converting in `run`/`repl` — one falsy-check site, not two |
| `mud:` parameter, `Tools::Mud.register`, `mud_opts_from_config` helper | **not ported** — see open question 1 | |

`Repl.__init__`/`_banner` do **not** gain a `mud`/`mud_status_string` parameter or banner line
under the recommended descope (open question 1) — the banner stays exactly as
`08_the_repl_loop` already has it.

## `examples/example.py`

Ruby's new `examples/example.rb` is a MUD-exploration demo (`Boukensha.run(task: "Connect to the
MUD...", working_dir: false, mud: ...)`) — entirely built around the descoped `Tools::Mud`. Since
this plan recommends not porting `Tools::Mud`, the Python example can't follow Ruby's literal
script; instead, rewrite it as a small demo of the *ported* feature (`Tools::FileSystem`/
`Tools::Shell`), replacing the current step's manually-`configure`d `read_file`/`list_directory`
tools with the new automatic `working_dir=` registration — e.g. point `working_dir` at
`../../07_the_run_dsl` (a real directory with files to browse, same target the current scaffold
already uses) and drop the `configure()` function entirely, since `boukensha.run`/`repl` now
registers those tools by itself. See open question 2 for the exact task text and whether to keep
`repl()` or switch to a one-shot `run()` call.

## `pyproject.toml`

Bump `description` to `"— 10: a standard tool library"`. No new dependency — `Tools::Shell` uses
only `subprocess`/`shlex` (stdlib); `Tools::FileSystem` uses only `pathlib`/`re` (stdlib). (Ruby's
`Gemfile` gained `gem "mud_manager", path: "..."` plus a bare `gemspec` line — both are artifacts
of the descoped `Mud` tool and the descoped gem-packaging step; neither has a Python-side
equivalent to add.)

## `README.md`

Rewrite from Ruby's `week1_baseline/ruby/10_standard_tool_library/README.md`, adapted for Python
(run instructions via `week1_baseline/bin/python/10_standard_tool_library`, not `bundle exec`),
documenting `Tools::FileSystem` and `Tools::Shell` exactly as Ruby's README does. Explicitly note,
in a short "Scope" or "Considerations" section, that `Tools::Mud` exists in Ruby's step but is not
ported here — pending a Python port of `mud_manager` (or a decision to build one) — rather than
silently omitting it and leaving a future reader to wonder why the Ruby/Python step diverge. Carry
forward Ruby's own "Technical Considerations" caveats about `Tools::Shell`'s allow-list not
handling an already-in-use MUD session prompt (not applicable without `Mud`, so this one specific
caveat can be dropped) and about there "not being enough tools" (keep — applies equally to
`FileSystem`/`Shell` alone).

## Delta to apply to `python/10_standard_tool_library`

| Change | File(s) | Action |
|---|---|---|
| Drop cwd tier | `boukensha/config.py` | edit `_resolve_dir` + module comment, per "Two reversions" |
| Drop 401 message | `boukensha/client.py` | edit, remove the `status == 401` branch, per "Two reversions" |
| New tools package | `boukensha/tools/__init__.py` | create (empty/minimal) |
| New `FileSystem` tools | `boukensha/tools/file_system.py` | create, per mapping above |
| New `Shell` tools | `boukensha/tools/shell.py` | create, per mapping above |
| `working_dir` attribute | `boukensha/context.py` | add param + attribute |
| New `run()`/`repl()` kwargs | `boukensha/__init__.py` | add `working_dir`/`allowed_commands`/`shell_timeout`, auto-register both tool modules, per mapping above |
| Version bump | `boukensha/version.py` | `VERSION = "0.10.0"` |
| Rewritten example | `examples/example.py` | rewrite per "examples/example.py" above and open question 2 |
| New launcher | `week1_baseline/bin/python/10_standard_tool_library` | create, standard shape (see skill template) |
| Bump description | `pyproject.toml` | `description` → `"— 10: a standard tool library"` |
| Rewritten README | `README.md` | rewrite, documenting `FileSystem`/`Shell`, noting `Mud` scope decision |
| Drop cwd-tier tests | `tests/test_config.py` | remove `test_resolve_dir_prefers_cwd_boukensha_over_default` and `test_resolve_dir_env_var_takes_priority_over_cwd` (or rewrite the latter to just assert env-var-wins without a cwd `.boukensha` in play) |
| Drop 401 test | `tests/test_client.py` | remove `test_401_status_code_raises_authentication_specific_error` |
| `working_dir` test | `tests/test_context.py` | add coverage for `working_dir` resolution (falsy → `None`, relative/`~` path → resolved absolute `Path`) |
| New tests | `tests/test_tools_file_system.py` | create — `pwd`/`list_directory`/`read_file`/`write_file`/`delete_file`/`search_files`, plus a path-traversal-rejection case |
| New tests | `tests/test_tools_shell.py` | create — `run_command` success, non-zero exit, allow-list rejection, timeout, command-not-found |
| Extended tests | `tests/test_boukensha_run.py`, `tests/test_boukensha_repl.py` | add assertions that `working_dir` (truthy) triggers both `Tools.file_system.register`/`Tools.shell.register` calls (mock/monkeypatch them), and that `working_dir=False` skips both |

## Decisions carried over (no longer open)

- **Copy-forward-then-delta workflow**, `uv` + `hatchling`, flat `boukensha/` layout,
  `.python-version` = 3.14, `ruff`/`isort`/`ty` via `uv run`, `pytest` in `tests/` — unchanged.
- **Port observed Ruby quirks/regressions faithfully rather than silently correcting or omitting
  them** — established by `02_the_registry`/`04_api_client`/`08_the_repl_loop`; reapplied here to
  both the cwd-tier and 401-message *reversions* (not just to keeping odd-but-intentional
  behavior — Ruby really did remove these, so Python removes them too).
- **No symbol/string key duality to port** — plain `str`/`dict.get` throughout, per `00_config`.
- **Tools return error strings, never raise, for agent-recoverable failures** — already Ruby's own
  convention throughout `FileSystem`/`Shell`, carried straight into the port with no change.
- **Never trust a Ruby README's example/output block (or, this time, its silence) at face value**
  — verify against actual code, per `02_the_registry` onward; reapplied here to the
  README's *omission* of `Tools::Mud` entirely, not just a misdescription.
- **Duplicate `run()`'s backend-resolution logic into `repl()` rather than factoring out a shared
  helper** — decided in `07_the_run_dsl`/`08_the_repl_loop`, reused verbatim for the new
  `working_dir`/`allowed_commands`/`shell_timeout` wiring.

## Open questions (please answer before implementation)

1. **Descope `Tools::Mud` and the Ruby-packaging changes, or port them too?**
   Ruby's cumulative 08→10 delta includes a third tool module, `Tools::Mud` (~480 lines, 25 tools),
   which itself depends on a separate ~690-line gem (`week0_explore/mud_manager/`, a raw-socket
   CircleMUD telnet session/primitives library with no existing Python equivalent anywhere in this
   repo) — plus Ruby-only packaging additions (`bin/boukensha`, `boukensha.gemspec`,
   `lib/boukensha_loader.rb`, the `Gemfile`'s `gemspec`/`mud_manager` lines) that mirror what
   Ruby's `09_global_executable` step did, a step Python's port has already, apparently
   deliberately, skipped (no `python/09_global_executable` directory or plan exists).
   *Recommendation:* descope both, for this step. Porting `Tools::Mud` faithfully would mean
   writing a Python `mud_manager` equivalent from scratch (session management, IAC stripping,
   CircleMUD command primitives) against a *live* MUD server for testing — a much larger and
   differently-shaped undertaking than "translate this file's Ruby idioms," and arguably its own
   future step (e.g. a hypothetical `11_mud_tools`) rather than something to fold into "a standard
   tool library." The Ruby-packaging pieces (gemspec, global `bin/boukensha`, `boukensha_loader.rb`)
   have no Python analog to port at all — Python's `week1_baseline/bin/python/<step>` launcher
   convention already serves the "run this step" need, established since `00_config`, and nothing
   about `10_standard_tool_library` changes that. This plan is written entirely on this
   recommendation; if you want `Mud` ported now instead, this plan needs a substantial rewrite
   before implementation (new sections for `mud_manager`-equivalent + `Tools.mud`, a live-server
   verification story, and a `mud` kwarg on `run`/`repl`/`Repl`'s banner) rather than a quick
   amendment.

2. **`examples/example.py` content, given `Tools::Mud` is descoped.** Ruby's own new example script
   is a MUD demo that doesn't apply here. *Recommendation:* rewrite the Python example to
   demonstrate `working_dir=` auto-registering `Tools::FileSystem`/`Tools::Shell`, pointed at
   `../../07_the_run_dsl` (keeping the "browse a real step's source" flavor the current scaffold
   already has), dropping the manual `configure()`-based `read_file`/`list_directory` registration
   entirely (redundant with the new automatic tools). Keep it as a `boukensha.repl(...)` call (this
   step doesn't change anything about the REPL vs. one-shot `run()` choice) so the user can
   interactively ask the agent to explore/read/search that directory and optionally run a shell
   command (e.g. `ls`, `grep`) in it. Confirm this shape, or propose different demo tasks/target
   directory.
3. **Test scope for `subprocess.run(..., shell=True)` in `test_tools_shell.py`.** Real
   subprocess execution (not mocked) is the natural way to test `run_command` end-to-end (there's
   no complex object to mock — it's a single `subprocess.run` call), but that means tests depend on
   real shell executables (`echo`, `false`, `sleep`) being present, which is a new kind of test
   dependency this port hasn't taken on before (every prior external-facing test — `Client`,
   backends — mocks the network boundary). *Recommendation:* don't mock; call `subprocess.run`
   for real using portable, always-present commands (`echo`, `false`/exit-code checks via `python3
   -c "import sys; sys.exit(1)"`, a `sleep`-based timeout test), matching how this project already
   treats `Tools::FileSystem` as suitable for real-filesystem (`tmp_path`) tests rather than mocked
   ones. Confirm, or say if you'd rather mock `subprocess.run` instead.

## Implementation steps (once questions above are answered)

1. Edit `boukensha/config.py`: drop the cwd tier from `_resolve_dir`, update the module comment.
2. Edit `boukensha/client.py`: remove the 401-specific `ApiError` branch.
3. Add `boukensha/tools/__init__.py`, `boukensha/tools/file_system.py`,
   `boukensha/tools/shell.py`, per "The `Tools::FileSystem` and `Tools::Shell` primitives" above.
4. Add `working_dir` param/attribute to `boukensha/context.py`.
5. Add `working_dir`/`allowed_commands`/`shell_timeout` params and tool auto-registration to both
   `run()` and `repl()` in `boukensha/__init__.py`; pass `working_dir` through to `Context`.
6. Bump `boukensha/version.py` to `"0.10.0"`.
7. Rewrite `examples/example.py` per open question 2's confirmed shape.
8. Add `week1_baseline/bin/python/10_standard_tool_library` (standard launcher shape).
9. Update `pyproject.toml`'s `description`.
10. Rewrite `README.md` from Ruby's, documenting `FileSystem`/`Shell` and noting the `Mud` scope
    decision.
11. Remove the cwd-tier tests from `tests/test_config.py`; remove the 401 test from
    `tests/test_client.py`; add `working_dir` coverage to `tests/test_context.py`; add
    `tests/test_tools_file_system.py` and `tests/test_tools_shell.py`; extend
    `tests/test_boukensha_run.py`/`tests/test_boukensha_repl.py` for the new kwargs.
12. Verify: `uv run pytest -v && make lint` (isort/ruff/ty) in
    `week1_baseline/python/10_standard_tool_library/`. Run
    `week1_baseline/bin/python/10_standard_tool_library` and
    `week1_baseline/bin/ruby/10_standard_tool_library` and compare — note Ruby's launcher will
    attempt a live MUD connection (per its own example.rb) while Python's won't, so this
    comparison is necessarily partial (FileSystem/Shell behavior only, not a byte-for-byte session
    match) given the open-question-1 descope.
