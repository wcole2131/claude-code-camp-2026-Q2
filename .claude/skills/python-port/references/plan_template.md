# Python Port Plan · <NN> · <Step Title>

Status: DRAFT — open questions below must be answered before implementation starts.

## Goal

One short paragraph: what `week1_baseline/python/<new_step>/` needs to become, and which Ruby
directory it must behave equivalently to (`@week1_baseline/ruby/<new_step>/README.md` is the
spec). Name the previous step it's being copied forward from.

## How this plan was created

Numbered list of what was actually done to produce this plan — not a hypothetical process, the
real one. Typically includes: confirming the python/<new_step> copy is byte-identical to
python/<prev_step> (or noting where it already diverges, if this plan is being revised);
diff -rq / diff -u between the two ruby/ steps; reading every changed/new Ruby file in full;
reading the new Ruby README in full; running the Ruby launcher to capture real output; reading the
current Python scaffold to confirm what's reusable as-is; confirming whether
week1_baseline/bin/python/<new_step> exists yet (it usually doesn't).

## Starting point (what's already in place, unchanged)

List every file that needs **no changes** because its Ruby original is byte-identical between
`<prev_step>` and `<new_step>` (per the diff in the previous section). Being explicit here is what
stops the implementation step from accidentally touching files it shouldn't.

## The exact delta (from `diff -u` between the two Ruby steps)

File-by-file description of what changed in the Ruby source going from `<prev_step>` to
`<new_step>`: new files (describe what they do), changed files (describe the change, not a full
reproduction of the diff), and an explicit note of anything that changed but has *no* Python
equivalent to port (e.g. Ruby packaging/Bundler concerns).

## Delta to apply to `python/<new_step>`

| Change | File(s) | Action |
|---|---|---|
| ... | ... | ... |

One row per file that actually needs an edit or needs to be created. Include the launcher,
`pyproject.toml`'s description bump, and the README rewrite as their own rows — they're easy to
forget.

## Ruby → Python behavior mapping

| Ruby | Python equivalent | Notes |
|---|---|---|
| ... | ... | ... |

Only for what's new or changed this step. Reuse the standing mappings in this skill's
`references/mapping_notes.md` (symbol/string key duality → `dict.get`, `Struct` → `dataclass`,
inclusive-range slicing, `Pathname` → `pathlib.Path`, duck-typed abstract methods) rather than
re-deriving them; add new rows only for idioms this step introduces for the first time.

## Decisions carried over (no longer open)

Bullet list of standing conventions from prior steps that apply again here without needing
re-litigation: copy-forward-then-delta workflow, `uv` + `hatchling`, flat `boukensha/` layout,
`.python-version` = 3.14, `ruff`/`isort`/`ty` via `uv run`, `pytest` in `tests/`, dict.get-only
lookups, plain/mutable dataclasses, duck-typed `NotImplementedError` abstract methods — plus
anything step-specific settled by an earlier plan that's relevant here.

## Open questions (please answer before implementation)

Only genuinely new ambiguities this step introduces — a new abstraction's exact shape, whether to
add test coverage for something novel, a typing looseness call, an ambiguous README instruction.
Give a recommendation for each; don't ask questions whose answer is "same as last time."

If there are truly none, say so explicitly instead of omitting the section.

## Implementation steps (once questions above are answered)

Numbered, concrete, file-by-file. Last step should always be "run both launchers and diff their
output" (see SKILL.md step 7) — don't let verification become implicit.
