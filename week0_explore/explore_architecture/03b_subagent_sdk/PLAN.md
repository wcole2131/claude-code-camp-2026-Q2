# Plan: switch 03b from filesystem subagent to SDK `AgentDefinition`

> **Status: implemented.** Per your follow-up notes, this became a full
> replacement (`.claude/agents/mud-play.md` deleted), the agent definition
> is loaded from `agents/mud-player.md` at runtime (not hardcoded as a TS
> string), and `scripts/agent.ts` runs as an interactive readline loop
> instead of a one-shot CLI-arg invocation. See the repo tree for the
> result; details below are the original proposal.

## Context

`03a_subagent_sdk` and `03b_subagent_sdk` are currently identical copies. Both
define the `mud-player` subagent the *filesystem* way — Claude Code's harness
auto-discovers `.claude/agents/mud-play.md` (YAML frontmatter + prompt body)
because it's sitting in the project's `.claude/agents/` directory. There is no
SDK driver code anywhere in this repo yet.

Per the Preweek journal (`docs/journal/0_preweek.md`, Ref 1), this pair is
meant to contrast two ways of getting a "filesystem subagent": *driven by the
coding harness* (03a, keep as-is) vs *driven by the Coding Agent SDK* (03b,
this change) — i.e. defining the same agent programmatically via
`AgentDefinition` and handing it to the SDK in code, instead of relying on
Claude Code's directory-scan convention.

Decisions already confirmed with you:
- Language: **TypeScript**, using `@anthropic-ai/claude-agent-sdk` (npm,
  confirmed installable — v0.3.216 checked).
- `.claude/agents/mud-play.md` in **03b only** gets **deleted** once its
  content is ported into code. `03a` is untouched, so the filesystem version
  remains available for comparison.

## What changes in `03b_subagent_sdk`

1. **`package.json`** (new) — minimal, `@anthropic-ai/claude-agent-sdk` as a
   dependency, `type: module`, a `tsx`/`ts-node` dev dependency to run the
   driver without a separate build step, and an npm script (`npm start` /
   `npm run play`) that forwards CLI args as the prompt.

2. **`tsconfig.json`** (new) — bare-bones Node/ESM/strict config, just enough
   for `tsx` to type-check on the fly.

3. **`scripts/agent.ts`** (new) — the SDK driver:
   - A `MUD_PLAYER_AGENT: AgentDefinition` constant holding what's currently
     split across `mud-play.md`'s frontmatter + body:
     - `description`: the existing one-line trigger description (verbatim).
     - `prompt`: the existing markdown body (Workflow, Long-term memory,
       Playing well, etc.) — copied as-is, since it's still accurate
       instructions for the same scripts.
     - `tools`: `["Bash"]` (see note below on the current `Bash(python3*)`
       restriction).
     - `model`: omitted (inherit).
   - Calls `query({ prompt, options: { agents: { "mud-player":
     MUD_PLAYER_AGENT }, cwd: <project root>, permissionMode: ... } })` from
     the SDK, streams/logs the resulting messages to stdout.
   - Reads the user's request from `process.argv` (e.g. `npm start -- "log
     in and look around"`) so it's runnable the same way you'd invoke the
     harness-driven version, just via `node`/`tsx` instead of the `claude`
     CLI.

4. **Delete** `.claude/agents/mud-play.md` and (since it becomes empty)
   the `.claude/agents/` directory in `03b_subagent_sdk` — content now lives
   in `scripts/agent.ts`.

5. **No changes** to `scripts/mud_*.sh`, `data/`, `assets/`, `references/` —
   those are the shared tmux/telnet plumbing the agent's `Bash` tool calls
   into, and stay identical to 03a.

## Open items / things I'll flag rather than silently decide

- **`tools: Bash(python3*)` in the current frontmatter** looks like a
  copy/paste mismatch — the scripts it actually calls are `.sh` files, not
  Python. I'll carry over plain `Bash` (unscoped) in the `AgentDefinition`
  unless you'd rather I preserve the same restrictive pattern.
- I will **not** invent a top-level orchestrating "main agent" persona beyond
  what's needed to route to `mud-player` — the SDK still needs a top-level
  `query()` call; I'll keep its own prompt minimal (essentially "you have a
  `mud-player` subagent, delegate MUD requests to it") rather than
  duplicating instructions.
- I won't try to actually run this against a live MUD/telnet session as part
  of making this change (no network/tmux verification beyond confirming the
  script runs and calls the SDK correctly) unless you want me to smoke-test
  it end-to-end after.

## Verification

- `npx tsc --noEmit` (or the `tsx` equivalent) to confirm the driver
  type-checks against the SDK's real `.d.ts`.
- Optionally, a dry run (`npm start -- "look"`) if you'd like to see it
  actually connect — this requires the MUD server on `localhost:4000` (per
  `scripts/mud_env.sh`) and network access from this sandbox.

---

## Your follow-up additions (incorporated)

1. Full replacement — done: `.claude/agents/mud-play.md` and the now-empty
   `.claude/agents/` dir were deleted from `03b_subagent_sdk`.
2. Load a markdown file — done: `agents/mud-player.md` holds the
   description/tools/prompt, and `scripts/agent.ts` reads + parses it
   (via `gray-matter`) at runtime into an `AgentDefinition`, rather than the
   prompt being a hardcoded TS string.
3. Interactive loop — done: `scripts/agent.ts` runs a `readline`-driven REPL
   (`npm start`), streaming an `AsyncGenerator<SDKUserMessage>` into `query()`
   and printing assistant text/tool-use as it arrives, turn after turn,
   until `/exit`, `/quit`, or Ctrl-D.