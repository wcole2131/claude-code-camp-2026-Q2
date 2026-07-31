# Plan: One Gem, One Binary — Fold `mud_manager_mcp` into `mud_manager`

Status: proposed — not yet built. Open questions below (with recommendations)
should be confirmed before implementation starts.

Companion to [`generic_interfacing.md`](./generic_interfacing.md) (why the MCP
sidecar exists), [`mcp_generalization_plan.md`](./mcp_generalization_plan.md)
(why it speaks real MCP), and [`mcp_mud_plan.md`](./mcp_mud_plan.md) (why the
framework itself ships no tools and everything is MCP-served). None of those
docs are being rewritten by this plan — they're the historical record of what
was built and why, and remain accurate about *why* an MCP server for MUD
exists at all. This plan only changes *where its code lives and how it
ships*, in response to a packaging problem those docs didn't address: today
there are two separate Ruby projects where conceptually there's one.

## Problem

`week0_explore/mud_manager/` is a real, installable gem: `mud_manager.gemspec`
declares it, `gem build` + `gem install` produces a global `mud-manager`
executable (an interactive raw-command CircleMUD prompt), zero external
dependencies (stdlib only).

`week1_baseline/mud_manager_mcp/` is **not** a gem at all — it has no
gemspec. It's a Bundler-only project directory: a `Gemfile` with two path
dependencies (`mud_manager` at `../../week0_explore/mud_manager`, `boukensha`
at `../ruby/10_standard_tool_library`), runnable only via `bundle exec ruby
bin/mud_manager_server` from inside this exact repo checkout. It exists
solely to expose `mud_manager`'s session/primitives as an MCP server so
non-Ruby language ports (and Ruby's own agent) can reach the MUD.

So today, getting MUD access into an agent means running two different Ruby
projects side by side, only one of which is actually distributable. That's
the problem: **ship one gem with one binary**, not a distributable domain
library plus an un-shippable Bundler-only sidecar bolted on next to it.

## Current state (for reference)

```
week0_explore/mud_manager/            gem "mud_manager" — gem build/install works
  mud_manager.gemspec                 no dependencies
  bin/mud-manager                     interactive raw-command CLI
  lib/mud_manager.rb, session.rb, primitives.rb

week1_baseline/mud_manager_mcp/       NOT a gem — Bundler path-deps only
  Gemfile                             mud_manager (path) + boukensha (path) + dotenv
  bin/mud_manager_server              MCP JSON-RPC server, built on Boukensha::MCP::Server
  lib/mud_tools.rb                    the 27 tool definitions, registers against Boukensha::Registry
  examples/demo.rb                    smoke-test client, uses Boukensha::MCP (the client)
```

## Target architecture

```
week0_explore/mud_manager/                    still the only project; still a gem
  mud_manager.gemspec                         version bump; still zero dependencies
  bin/mud-manager                              ONE binary, two modes:
                                                  mud-manager                 -> today's interactive prompt (unchanged)
                                                  mud-manager --mcp           -> MCP JSON-RPC server over stdio (new)
  lib/mud_manager.rb
  lib/mud_manager/session.rb                   unchanged
  lib/mud_manager/primitives.rb                unchanged
  lib/mud_manager/tools.rb                     NEW — the 27 tool specs, moved from mud_manager_mcp/lib/mud_tools.rb
  lib/mud_manager/mcp_server.rb                NEW — the generic stdio JSON-RPC loop, self-hosted (see decision 2)
  examples/mcp_demo.rb                          NEW — smoke-test client, moved from mud_manager_mcp/examples/demo.rb

week1_baseline/mud_manager_mcp/                DELETED — everything above replaces it
```

## Decisions

### 1. Where does the merged gem live — stay at `week0_explore/mud_manager`, or move to `week1_baseline/`?

`mud_manager_mcp`'s own README currently frames the sidecar as "cross-cutting
infrastructure shared by every language port, not part of any one step's
lesson content" — which reads like an argument for `week1_baseline/`,
alongside `file_system_mcp`/`shell_mcp`.

**Recommendation: stay at `week0_explore/mud_manager`.** Moving it would mean
renaming/relocating a gem that predates this whole MCP effort, rewriting
`week0_explore/HOW_TO_PLAY.md`/`CHALLENGES.md` references, and touching every
consumer's path *twice* (once for the merge, once for the move) for a
reorganization nobody asked for. `week0_explore/` already isn't purely
"throwaway exploration" — `mud_manager` has been load-bearing, cross-cutting
infrastructure since `generic_interfacing.md`, sitting there the whole time;
this plan doesn't need to fix that naming tension to solve the two-gem
problem. If the `week0_explore` vs. `week1_baseline` split ever gets
revisited on its own terms, do it as its own plan.

### 2. Does the merged gem depend on `boukensha` for the JSON-RPC/registry plumbing, or self-host it?

`Boukensha::MCP::Server` (`lib/boukensha/mcp/server.rb`, ~120 lines) already
implements the exact generic stdio JSON-RPC loop this needs, and
`file_system_mcp`/`shell_mcp` both reuse it rather than hand-rolling their
own — that's the whole point of `mcp_mud_plan.md` decision 1. The tempting
move is for `mud_manager` to depend on it too.

**Recommendation: self-host a small, local version instead — do not add a
`boukensha` dependency.** Reasoning:

- `mud_manager` currently has **zero** dependencies and is documented as a
  general-purpose CircleMUD client gem, useful on its own, outside this
  teaching repo. `boukensha` is a specific, step-versioned teaching-framework
  package (`0.10.0` ties to `10_standard_tool_library`). Making a
  general-purpose telnet gem depend on a specific pedagogical package's
  internals to serve its own tools is a layering inversion — `mud_manager`
  would exist "underneath" `boukensha` in every dependency diagram except
  this one edge.
- The piece actually needed — a stdio JSON-RPC loop serving `tools/list` and
  `tools/call` from a fixed tool table — is small and MUD-specific in one
  respect that simplifies it further: `mud_manager`'s server only ever needs
  to serve **its own fixed 27-tool catalog**, never an arbitrary
  caller-supplied one. It doesn't need `Boukensha::Registry`'s generality
  (register arbitrary tools at runtime) — a flat array/hash of `{name:,
  description:, parameters:, block:}` is enough (see decision 4). That's
  meaningfully less code than "port Registry, Tool, and Server."
- Cost: ~90-120 lines of JSON-RPC protocol handling exist in two places
  instead of one. Small and stable (this is exactly the JSON-RPC 2.0 tool
  subset `mcp_generalization_plan.md` already fixed for good) — a reasonable
  price for keeping `mud_manager` genuinely standalone.

If `mud_manager` is ever meant to be published independently (rubygems.org,
outside this repo entirely), this decision is what makes that possible
without an unpublishable `boukensha` dependency riding along. Flagged as a
possible future refactor, out of scope here: extract the ~4 truly generic
files (`registry.rb`, `tool.rb`, `context.rb`, `mcp/server.rb`) into their
own tiny zero-dependency gem that *both* `boukensha` and `mud_manager` depend
on. Not needed to solve today's two-gem problem, and bigger in scope than
what was asked.

### 3. How does one binary serve two modes?

**Recommendation: an `--mcp` boolean flag on the existing `bin/mud-manager`
`OptionParser`.** `--host`/`--port`/`--name`/`--password` are already parsed
into one `options` hash defaulting from `MUD_HOST`/`MUD_PORT`/`MUD_NAME`/
`MUD_PASSWORD`; `--mcp` reuses that same hash rather than requiring
MCP-mode callers to set env vars while interactive-mode callers use flags (or
vice versa) — one consistent set of inputs for both modes. At the top of the
script: `if options[:mcp]` → build the tool table and call
`MudManager::MCPServer.new(...).serve`; else → today's interactive loop,
unchanged.

### 4. Port `Boukensha::Registry`/`Tool` too, or use a flat tool table?

**Recommendation: flat table, no `Registry` port.** `Boukensha::Registry` is
generic because the *agent* framework needs to register tools from an
unbounded number of unrelated MCP servers into one shared registry.
`mud_manager`'s own server only ever advertises the one, fixed 27-tool MUD
catalog it defines — there is no second caller supplying different tools at
runtime. `MudManager::Tools.catalog` returning `[{name:, description:,
parameters:, block:}, ...]` (or a `name => spec` hash for O(1) dispatch) is
sufficient; `MudManager::MCPServer` looks tools up in that table directly
instead of calling into a generic `Registry#dispatch`.

## What changes, file by file

| File | Change |
|---|---|
| `week0_explore/mud_manager/mud_manager.gemspec` | Version bump (0.1.0 → 0.2.0); no new dependencies. `spec.files = Dir["lib/**/*.rb"] + Dir["bin/*"]` already globs in the new `lib/mud_manager/*.rb` files with no edit needed. |
| `week0_explore/mud_manager/bin/mud-manager` | Add `--mcp` to the `OptionParser`; branch at the bottom: MCP mode builds `MudManager::Tools.catalog(...)` and calls `MudManager::MCPServer.new(...).serve`; else today's interactive loop, byte-for-byte unchanged. |
| `week0_explore/mud_manager/lib/mud_manager/tools.rb` | **New.** The 27 tool specs, moved from `mud_manager_mcp/lib/mud_tools.rb`. Same tool names/descriptions/parameters/dispatch bodies (`send_cmd`, `guard`, the `MudManager::Session`/`Primitives` calls) — only the registration mechanism changes, from `registry.tool(name, ...) { block }` calls against a `Boukensha::Registry` to building the flat table from decision 4. |
| `week0_explore/mud_manager/lib/mud_manager/mcp_server.rb` | **New.** Self-hosted JSON-RPC stdio loop, adapted from `Boukensha::MCP::Server` (`initialize`/`notifications/initialized`/`tools/list`/`tools/call`, same `isError` semantics, same `inputSchema` shape) but operating on the flat tool table instead of a `Registry`. |
| `week0_explore/mud_manager/lib/mud_manager.rb` | Add `require_relative "mud_manager/tools"` and `require_relative "mud_manager/mcp_server"`. |
| `week0_explore/mud_manager/examples/mcp_demo.rb` | Moved/rewritten from `mud_manager_mcp/examples/demo.rb`: same read-only smoke sequence (`mud_status`, `look`, `check score`, `check inventory`, `mud_disconnect`), but the client side becomes a small hand-rolled JSON-RPC client (no `Boukensha::MCP` — that would reintroduce the dependency decision 2 just rejected) spawning `bin/mud-manager --mcp` directly. |
| `week0_explore/mud_manager/README.md` | Merge in `mud_manager_mcp/README.md`'s protocol/usage sections (the JSON-RPC message shapes, the env-var table, "who uses this"). |
| `week1_baseline/mud_manager_mcp/` | **Deleted entirely** — `Gemfile`, `Gemfile.lock`, `bin/`, `lib/`, `examples/`, `README.md`, `.gitignore`, `vendor/`. |
| `week1_baseline/ruby/10_standard_tool_library/lib/boukensha/mcp.rb` | `Boukensha::MCP.mud_manager_server` factory: drop `dir:` pointing at the old sidecar directory; `command:` becomes `["ruby", "<path to mud_manager>/bin/mud-manager", "--mcp"]` — plain `ruby`, no `bundle exec`, since the merged gem has zero dependencies (see "Consequences"). |
| `week1_baseline/python/10_standard_tool_library/boukensha/mcp.py` | `MCPClient.mud_manager_server` static method: same command/cwd update, mirrored. |
| `week1_baseline/ruby/10_standard_tool_library/README.md`, `week1_baseline/python/10_standard_tool_library/README.md` | Update the `mud_manager_mcp` table row/prose to describe the merged gem and its new invocation. |
| `week1_baseline/python/10_standard_tool_library/tests/test_tools_mud.py`, `tests/fake_circlemud.py` | Update comments referencing `week1_baseline/mud_manager_mcp/...`; the `pytest.mark.skipif(no bundle)` guard can likely be simplified to "no `ruby`" — worth double-checking once `bundle exec` is no longer required. |
| `week1_baseline/ruby/10_standard_tool_library/lib/boukensha_loader.rb` | No change expected — it only calls `Boukensha::MCP.mud_manager_server(...)`, whose call signature doesn't change, only its internals. |
| `docs/plans/floating_artifacts/boukensharc.md` | Append a new "Change history" entry once this lands, since the command spec `boukensha_loader.rb` ends up building (indirectly, via `Boukensha::MCP.mud_manager_server`) changes shape. Not part of this plan's own scope — a reminder for whoever implements it. |

## What doesn't change

- `MudManager::Session`/`MudManager::Primitives` — the telnet client and
  CircleMUD command builders. Untouched by this plan; it's purely a packaging
  change around them.
- The 27 tools' names, descriptions, parameters, and dispatch behavior —
  moved, not redesigned.
- `file_system_mcp`/`shell_mcp` and `Boukensha::MCP::Server`/`Registry`/
  `Tool`/`Context` — unaffected. They never had a separate "domain gem" the
  way `mud_manager`/`mud_manager_mcp` did, so there's nothing analogous to
  merge for them.
- The MCP wire protocol itself (JSON-RPC 2.0, `initialize`/`tools/list`/
  `tools/call`, `isError` semantics) — identical bytes on the wire; only
  which process answers changes.

## Consequences

- **Simpler local dev invocation, not more complex.** Today,
  `mud_manager_mcp` requires `bundle exec` (its `Gemfile` path-depends on
  `boukensha` and `mud_manager`). Under decision 2 (self-hosted, zero
  dependencies), the merged gem needs no `Gemfile` at all for this purpose —
  `ruby bin/mud-manager --mcp` runs directly, exactly like `mud-manager`'s
  interactive mode already does today. `Boukensha::MCP.mud_manager_server`'s
  default spec gets *simpler*, not more complex.
- **A genuinely distributable MCP server, for the first time.** Today,
  nothing about `mud_manager_mcp` can be `gem install`ed — it only runs
  inside this exact repo checkout via relative Bundler paths. After this
  plan, `gem install mud_manager` (matching `mud_manager`'s existing "Build
  the Gem" instructions) gives you a real, standalone `mud-manager --mcp`
  MCP server usable from *any* MCP client (Claude Desktop, Claude Code, or
  this repo), not just this repo's own dev workflow.
- **Small protocol-code duplication accepted, not eliminated.** Decision 2
  keeps `mud_manager`'s JSON-RPC loop textually separate from
  `Boukensha::MCP::Server`. `mcp_mud_plan.md` set out specifically to kill
  this kind of duplication for `file_system_mcp`/`shell_mcp` — this plan
  reintroduces one instance of it, deliberately, to avoid a worse layering
  problem (see decision 2's reasoning). Worth being honest that this is a
  tradeoff, not a clean win on every axis.

## Phased sequencing

1. Build `MudManager::Tools` (flat table) and `MudManager::MCPServer` (stdio
   loop) inside `week0_explore/mud_manager/lib/mud_manager/`, porting
   `mud_tools.rb`'s 27 tools and `Boukensha::MCP::Server`'s loop respectively.
2. Wire `--mcp` into `bin/mud-manager`; verify manually against a live
   CircleMUD server with the same three checks `mcp_integration_verification.md`
   already established (`mud_status`, `look`, `check score/inventory`,
   `mud_disconnect`), now spawning `mud-manager --mcp` directly instead of
   `mud_manager_mcp/bin/mud_manager_server`.
3. Update `Boukensha::MCP.mud_manager_server` (Ruby) and
   `MCPClient.mud_manager_server` (Python) to the new command/path; re-run
   the full existing verification matrix (Ruby in-process default
   `mcp_servers:`, Python's `test_tools_mud.py` against the fake CircleMUD
   double, `demo`/`mcp_demo` manual smoke test) against the merged gem.
4. Delete `week1_baseline/mud_manager_mcp/` once nothing references it.
5. Update the READMEs and `docs/plans/floating_artifacts/boukensharc.md`
   (append, don't rewrite its existing "Change history").
6. Rebuild the gem (`gem build mud_manager.gemspec`) and, if a global
   `mud-manager` is already installed on this machine from the old 0.1.0
   build, reinstall it so `--mcp` is actually available system-wide, not
   just via the in-repo `ruby bin/mud-manager` path.

## Open questions

1. **Decision 1 (location)** — confirm staying at `week0_explore/mud_manager`
   rather than moving to `week1_baseline/`.
2. **Decision 2 (dependency direction)** — confirm self-hosting the JSON-RPC
   loop (no `boukensha` dependency) rather than depending on
   `Boukensha::MCP::Server`, given the small duplication cost that implies.
3. **Decision 3 (`--mcp` flag vs. subcommand)** — confirm a flag on the
   existing `OptionParser` rather than e.g. `mud-manager mcp` as a
   subcommand.

If all three recommendations look right, implementation can start directly
from the "Phased sequencing" section above.
