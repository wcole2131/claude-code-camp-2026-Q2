---
name: python-port
description: Port the next week1_baseline/ruby/NN_stepname step to week1_baseline/python/NN_stepname, following this repo's established copy-forward-then-delta workflow. Use whenever the user asks to "port the next ruby step to python," "port week1_baseline/ruby/<step>," continue the Boukensha Python port, or otherwise wants a new NN_* step translated from Ruby to Python in this repo. Also use if the user asks to write or update a plan doc under docs/plans/python_port/ — that plan-writing step is part of this same workflow, not a separate task.
---

# Python Port

This repo ports a Ruby teaching project (`boukensha`, under `week1_baseline/ruby/NN_stepname/`)
to Python (`week1_baseline/python/NN_stepname/`) one numbered step at a time. Steps 00-03 are
already ported and establish a consistent workflow — follow it rather than re-deriving an
approach from scratch. Deviating from it (e.g. porting a step's full Ruby source from nothing,
or skipping the plan doc) will produce a result that's inconsistent with the rest of the repo.

**The core idea**: each Ruby step is usually a small delta on top of the previous Ruby step, not
a rewrite. So each Python step should be an equally small delta applied on top of a verbatim copy
of the previous Python step — never a from-scratch port. Finding that delta (by diffing the two
Ruby directories) is most of the work; applying it in Python is comparatively mechanical.

## 0. Figure out which step you're porting

If the user names a step explicitly, use that. Otherwise, find the next one:

```bash
ls week1_baseline/ruby/       # every NN_stepname that exists in Ruby
ls week1_baseline/python/     # every NN_stepname already ported
```

The next step is the lowest-numbered `ruby/NN_*` directory with no corresponding *completed*
`python/NN_*` directory. A `python/NN_*` directory only counts as "already ported," not just
present — check `docs/plans/python_port/NN_stepname.md` (or `.md`-less variants; both exist in
this repo) for `Status: DRAFT` vs. a finished plan, and check whether the directory's `README.md`
still describes an earlier step (a sign it's an un-adapted copy, not a real port). If in doubt, ask.

Call the step you're porting `<new_step>` (e.g. `04_api_client`) and the one immediately before it
`<prev_step>` (e.g. `03_prompt_builder`).

## 1. Read one prior plan as a worked example

Before writing anything, read one or two existing plans in `docs/plans/python_port/` — ideally
the most recent completed one (highest-numbered) plus `01_struct_skeleton` if you want to see the
copy-forward workflow explained in the porter's own words the first time it was used. These are
the actual worked examples this skill is modeling; skim them for tone and structure rather than
re-reading every one every time.

## 2. Establish the exact delta between the two Ruby steps

Don't read the new Ruby step in isolation — read it *as a diff* against the previous one. That
diff is the actual scope of the porting work.

```bash
diff -rq week1_baseline/ruby/<prev_step>/ week1_baseline/ruby/<new_step>/ \
  -x vendor -x .bundle -x Gemfile.lock -x .gitignore
```

Then `diff -u` (or just `Read`) each file that differs, plus read every genuinely new file in
full. Files `diff -rq` doesn't list are byte-identical between the two Ruby steps — their Python
counterparts need **no changes** and should be left untouched.

Also skim the new step's `README.md` in full — it's the behavior spec (config resolution order,
schemas, expected output), not just prose describing the code. If something in the README
disagrees with what the code actually does, trust the code, and note the discrepancy in the plan
(this has happened before — see the `02_the_registry` plan's note about a stale `budget=8192` field).

If you want to see the new Ruby step's *actual* output (safer/more informative than trusting the
README's documented example), run its launcher:

```bash
week1_baseline/bin/ruby/<new_step>
```

If this fails with a Bundler version error, run `week1_baseline/bin/setup_ruby_step <new_step>`
first (it repins `Gemfile.lock`'s `BUNDLED WITH` line to the Bundler actually installed on this
machine, then does `bundle install`) — this is a known, expected local-environment quirk, not a
sign anything is actually broken.

## 3. Copy the previous Python step forward

```bash
rsync -a --exclude='.venv/' --exclude='__pycache__/' --exclude='.ruff_cache/' --exclude='.pytest_cache/' \
  week1_baseline/python/<prev_step>/ week1_baseline/python/<new_step>/
```

(Any equivalent `cp -r` + cleanup works too.) This is the scaffold you'll edit — do not write any
Python file from a blank slate if an equivalent already exists from the previous step. The
excluded directories are caches/build output that regenerate on first `uv run`; there's nothing in
them worth carrying forward.

## 4. Write the plan doc

Write `docs/plans/python_port/<new_step>.md`, opening with `Status: DRAFT — open questions below
must be answered before implementation starts.` Use `references/plan_template.md` in this skill
as the structural template — it has the section headers and short guidance on what goes in each
one, pulled directly from how the existing plans (00 through 03) are written. Fill it in for real;
don't leave template placeholder text in the committed plan.

The two tables that matter most:
- **Delta to apply** — Change / File(s) / Action, one row per file that actually needs editing.
- **Ruby → Python behavior mapping** — Ruby idiom / Python equivalent / Notes, for anything new or
  changed in this step. `references/mapping_notes.md` in this skill lists the simplifications
  already settled in prior steps (symbol/string key duality, `Struct` → `dataclass`, inclusive
  Ruby ranges, etc.) — reuse those verbatim where they apply instead of re-deriving them, and only
  add new mapping rows for genuinely new Ruby idioms this step introduces.

Only ask **open questions** for things prior steps haven't already settled — new abstraction
shapes, test scope for a genuinely novel kind of behavior, typing looseness on something new. Don't
re-ask about things already decided (package layout, `uv`/`hatchling`, dict.get-only lookups,
mutable dataclasses, copy-forward-then-delta itself) — carry those forward as a "Decisions carried
over" section instead, same as the existing plans do.

## 5. Stop and wait for the user

The plan is DRAFT until the user answers the open questions (if any). Present the plan and the
open questions, then wait — don't start editing Python files yet. If there are no genuine open
questions for this step, say so plainly and ask the user to confirm the plan before proceeding
rather than silently plowing ahead.

## 6. Implement the delta

Once the plan is confirmed, apply only what the "Delta to apply" table says. Concretely, that
usually means some subset of:

- New/changed modules under `boukensha/` (and matching new/changed `tests/test_*.py`)
- `boukensha/__init__.py` — export any new public names
- `examples/example.py` — rewritten to match the new Ruby step's `examples/example.rb`
- `week1_baseline/bin/python/<new_step>` — new launcher script (see below; doesn't exist yet for
  the step you're porting)
- `pyproject.toml` — bump the `description` field's step suffix (e.g. `"— 03: prompt builder"` →
  `"— 04: api client"`); add a dependency only if the new Ruby step's `Gemfile` added a gem with a
  clear Python equivalent (most steps in this project add none — they're pure in-memory logic)
- `README.md` — rewritten from the new Ruby step's README, adapted for Python (see below)

Leave every file the plan's "Starting point" section says is unchanged strictly alone — don't
"improve" or reformat it as a drive-by; that's scope creep this repo's plans explicitly guard
against.

**Launcher script** (`week1_baseline/bin/python/<new_step>`, executable, mirrors every existing
one exactly):

```bash
#!/usr/bin/env bash

cd "$(dirname "$0")/../../python/<new_step>"
uv run python examples/example.py
```

**README**: adapt the new Ruby step's README for Python — same behavior/schema documented, same
section shape, but Python run instructions (`week1_baseline/bin/python/<new_step>`, not
`bundle exec`) and — important — real captured output from actually running the port, not output
copy-pasted from the Ruby README (which has been observed stale at least once; see step 2).

**Tests**: this project has consistently added `pytest` coverage for new/changed modules at each
step even though the Ruby side ships none, matching the naming already in `tests/` (one
`test_<module>.py` per `boukensha/<module>.py`). Keep doing that unless the plan's open questions
say otherwise for this step.

`references/pyproject_template.toml` and `references/makefile_template` in this skill capture the
exact boilerplate shape (`uv` + `hatchling`, flat `boukensha/` package, Python 3.14,
`ruff`/`isort`/`ty`/`pytest` via `uv run`) — you shouldn't need them since you're copying an
existing step forward rather than scaffolding fresh, but they're there as a sanity check if
something in the copied scaffold looks off.

## 7. Verify by running both sides

```bash
week1_baseline/bin/python/<new_step>
week1_baseline/bin/ruby/<new_step>
```

Compare the actual output of both — same sections, same structure, same values, modulo things that
are expected to differ (e.g. the `Config` dir path, which is absolute and machine-specific). Don't
declare the port done off a read-through alone; this project's whole verification method is
"run both, diff the output," and skipping it is how the stale-README mismatch in `02_the_registry`
would have shipped unnoticed.

If `pytest`/`ruff`/`isort`/`ty` are relevant to what changed, also run them:

```bash
cd week1_baseline/python/<new_step> && uv run pytest -v && make lint
```

## Common pitfalls (from prior steps' plans)

- **Off-by-one on Ruby's inclusive ranges.** `content.to_s[0..60]` is 61 characters. The Python
  equivalent is `content[:61]`, not `content[:60]`.
- **Don't reintroduce symbol/string key duality.** Ruby's `dig`/`fetch`/`transform_keys(&:to_sym)`
  exist because Ruby hashes can have string *or* symbol keys. PyYAML and Python `**kwargs` only
  ever produce/accept `str` keys — the duality has no Python equivalent to port, so don't invent
  one; plain `dict.get(key)` / `**kwargs` is the correct simplification, not a shortcut.
- **Mutable default arguments.** Ruby's `parameters: {}` in a method signature is safe (Ruby
  re-evaluates default literals per call); Python's `def f(x={})` is not (the dict is shared across
  calls). Use `x: dict | None = None` and default it to `{}` inside the function body.
- **Don't trust a Ruby README's "Expected Output" block blindly** — run the actual Ruby launcher
  and use that output as ground truth (see step 2).
- **Keep the abstract-method style Ruby actually uses.** `Tasks::Base`'s `task_name` is a
  duck-typed `NotImplementedError`-raising class method, not an instance-based abstract method —
  Python's `abc.ABC`/`@abstractmethod` doesn't map cleanly onto class-level, no-instance methods,
  so this project has consistently kept the duck-typed `NotImplementedError` shape instead.
- **Watch for floating artifacts when a Ruby step has no matching Python step.** `ruby/09_global_executable`
  (the gem/`bin/boukensha`/`~/.boukensharc` machinery) has no `python/09_*` counterpart and never
  will — see `docs/plans/floating_artifacts/boukensharc.md` before treating a diff that spans the
  09 gap (e.g. `python/08` → `python/10`) as step content. Check that doc's list of floating
  artifacts before assuming everything in such a diff needs porting.
- **Editing an already-ported file outside of this porting workflow (a bug fix, a refactor, an
  infrastructure change) still needs both sides updated in the same change.** This skill's steps
  above cover porting a *new* step; they don't fire when you're just patching an existing one. Any
  file with a `# Mirrored by ...` / `# Mirrors ...` comment pointing at its counterpart (e.g.
  `lib/boukensha/mcp.rb` ↔ `boukensha/mcp.py`) has to move in lockstep — grep for `Mirror` across
  both `lib/` and `boukensha/` if you're not sure whether a file you're touching has one, don't
  assume you'll remember, and don't wait for a future full re-port to catch the drift.
