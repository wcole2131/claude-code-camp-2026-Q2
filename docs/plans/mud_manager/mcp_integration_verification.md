# MCP Integration: What's Actually Required, and Verified Proof It Works

Companion to [`generic_interfacing.md`](./generic_interfacing.md) (the design
doc for *why* `mud_manager_mcp` exists and what it looks like). This doc
answers a narrower question that came up after building it: **does Ruby's own
`boukensha` still work standalone, or is `mud_manager_mcp` now a hard
dependency for everyone?** — and proves the answer with real runs against a
live CircleMUD server, not just the fake test double.

## The four layers

```
week0_explore/mud_manager                 the gem: telnet client + CircleMUD
  (MudManager::Session, ::Primitives)      command primitives. Nothing else
                                            talks to a socket directly.
        ↑ required by
week1_baseline/ruby/10_standard_tool_library/lib/boukensha/tools/mud.rb
  (Boukensha::Tools::Mud)                  the 27 tool definitions
  (look, attack, shop, send_raw, ...)      (descriptions + parameter schemas
                                            + dispatch logic). Single source
                                            of truth — nothing duplicates
                                            these definitions in Ruby.
        ↑ called directly,              ↑ registered unmodified as its
        │ in-process                    │ dispatch table by
        │                                │
  Boukensha.run/repl                week1_baseline/mud_manager_mcp
  (the ruby step's own agent)       (bin/mud_manager_server — JSON-lines
                                      sidecar over stdio)
                                            ↑ spawned as a subprocess,
                                            │ driven over JSON-lines
                                            │
                              week1_baseline/python/10_standard_tool_library
                              /boukensha/tools/mud.py  (MudBridge)
                              — and any future non-Ruby language port
```

## Is `mud_manager_mcp` a hard requirement?

**For the Ruby step itself: no.** `Boukensha::Tools::Mud.register` (in
`mud.rb`) still does exactly what it always did — opens a
`MudManager::Session` directly, in-process, no subprocess, no sidecar. Running
`boukensha` from the terminal, or `ruby examples/example.rb`, in
`week1_baseline/ruby/10_standard_tool_library` is **completely unaffected**
by anything built in `mud_manager_mcp`. Nothing was changed in `mud.rb`,
`boukensha.rb`, or the Ruby step's `Gemfile`/gemspec to route through it.

**For every other language: yes, by construction.** `mud_manager` is a Ruby
gem. No other language in this repo can open a `MudManager::Session`
directly — the *only* supported way for a non-Ruby agent to reach the MUD is
to spawn `week1_baseline/mud_manager_mcp/bin/mud_manager_server` and speak
its JSON-lines protocol. That's not a policy choice layered on top; it's the
only path that exists. `week1_baseline/python/10_standard_tool_library/
boukensha/tools/mud.py` is the first (and so far only) example of a language
doing this.

So: one gem (`mud_manager`), one place its tool definitions live (`mud.rb`),
two ways to reach it — direct in-process (Ruby only) and through the MCP
sidecar (everyone else, Ruby included if it wanted to).

## Verified against a real CircleMUD server

This environment already has a live CircleMUD running on `localhost:4000`
("Temple of Midgaard" — the CircleMUD stock world), with test credentials in
`.boukensha/settings.yaml` (`mud: host/port/username: dummy/password`). All
three paths below were run against that same real server just now — not the
`tests/fake_circlemud.py` double used for automated test coverage.

### 1. Ruby step, direct in-process (unaffected baseline)

`Boukensha::Tools::Mud.register` called directly against a `Registry`, no
sidecar involved — this is exactly what `boukensha`/`example.rb` do today:

```
tool_count: 27
mud_status -> connected to localhost:4000
look -> The Temple Of Midgaard
   You are in the southern end of the temple hall in the Temple of Midgaard.
   ...
   [ Exits: n e s w d ]
24H 100M 83V (news) (motd) >
mud_disconnect -> disconnected
```

### 2. `mud_manager_mcp/examples/demo.rb` (sidecar, Ruby client)

Spawns `bin/mud_manager_server` as a real subprocess and drives it over the
JSON-lines protocol — proves the sidecar itself works end to end against a
live server, independent of any particular consuming language:

```
Connecting to localhost:4000 as dummy...
→ mud_status({})
← connected to localhost:4000
→ look({})
← The Temple Of Midgaard ...
→ check({"kind"=>"score"})
← You are 17 years old. ... This ranks you as Dummy the Swordpupil (level 1).
→ check({"kind"=>"inventory"})
← You are carrying: the teleporter
→ mud_disconnect({})
← disconnected
```

### 3. Python bridge, through the sidecar

`boukensha.tools.mud.register` (Python) spawning the same sidecar and
dispatching through the Python `Registry`:

```
tool_count: 27
mud_status -> connected to localhost:4000
look -> The Temple Of Midgaard ...
check score -> You are 17 years old. ... This ranks you as Dummy the Swordpupil (level 1).
mud_disconnect -> disconnected
```

Same server, same character, same 27 tools, three different entry points —
one direct, two through the MCP sidecar (one from Ruby, one from Python) —
all producing identical results.

## For future language ports

When adding a new `week1_baseline/<language>/` port that needs MUD access,
the integration point is fixed and already proven — don't build a new one:

1. Spawn `bundle exec ruby bin/mud_manager_server` with cwd set to
   `week1_baseline/mud_manager_mcp/`, and `MUD_HOST`/`MUD_PORT`/`MUD_NAME`/
   `MUD_PASSWORD` in its environment (`MUD_HOST` defaults to `localhost`,
   `MUD_PORT` to `4000` if unset).
2. Write one JSON object per line to its stdin: `{"id": <int>, "tool":
   <name>, "args": {...}}`.
3. Read one JSON object per line back from its stdout: `{"id": <int>, "ok":
   true, "result": <string>}` or `{"id": <int>, "ok": false, "error":
   <string>}`.
4. Hand-register the same 27 tools (name/description/parameters) against
   that language's own registry — see `mud.py` for the reference list, or
   `mud.rb` for the authoritative source. This is the one piece that's
   duplicated per language (see the "open question" in
   `generic_interfacing.md` — resolved as hand-duplication, not a dynamic
   `describe` call, while there are only two languages to keep in sync).

`week1_baseline/python/10_standard_tool_library/boukensha/tools/mud.py` is
the reference implementation of steps 1–4; copy its shape, not its Python
syntax.
