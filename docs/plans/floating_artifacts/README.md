# Floating Artifacts

Steps in this repo normally form a chain: each new step is a copy of the previous step plus a
small delta (see `.claude/skills/python-port/SKILL.md`, `docs/plans/python_port/PORT_PLAN.md`).
Whatever existed in step N is expected to still exist, possibly changed, in step N+1 — and on the
Python side, every Ruby step is expected to eventually get a matching port.

A **floating artifact** is code that breaks that chain: it doesn't get carried forward into the
next step(s). It's introduced at some point and then the lineage that normally re-copies and
re-documents everything just stops running through it. Because nothing in the mechanical
copy-forward process ever points back at it, a future AI session that follows "copy step N-1
forward, apply the delta" has no way to discover it exists unless it's written down somewhere.
This directory is that somewhere.

## Current artifacts

| Artifact | Introduced in | Where the chain stops | Doc |
|---|---|---|---|
| `~/.boukensharc` / global executable (`bin/boukensha`, `*.gemspec`, `lib/boukensha_loader.rb`) | `week1_baseline/ruby/09_global_executable` | Never carried into the Python port — `docs/plans/python_port/` has no `09_*` entry and `week1_baseline/python/09_global_executable` doesn't exist; the port jumps straight from step 08 to step 10. | [boukensharc.md](boukensharc.md) |

## Adding a new entry

Add one whenever a step introduces code that the normal copy-forward-then-delta process won't
carry into whatever comes next — a skipped port step, a language/toolchain concern with no
equivalent on the other side, etc. Give it its own `<artifact_name>.md` here, add a row to the
table, and say plainly where the chain breaks and what a future step should do about it.
