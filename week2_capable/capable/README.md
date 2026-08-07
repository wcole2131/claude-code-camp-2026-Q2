# capable — Observable Mapping

Implements phases 1–4 of [`docs/plans/observable.md`](../../docs/plans/observable.md)
(parse a room from raw MUD text, track it in a persistent room graph, gate
the automatic mapping step with an explicit tool policy, compute the route
back to a designated home room) plus phases 1–4 of
[`docs/plans/room_database.md`](../../docs/plans/room_database.md) (durable
SQLite persistence, destination routing beyond just home, and a per-visit
ledger so "how many times has the player passed through this room" is a
real query).

**Deferred**: `observable.md` phase 5+ (BERT-Medium-backed room
identification via a standalone `embedding_mcp` server, and
bootstrapping/validating the graph against the offline
`circlemud_world_parser` `.wld` database — everything here works on
exact-match room identification only), and `room_database.md`'s optional
`on_depart`/dwell-time hook.

**Requires Ruby 3.3.12** (see `.ruby-version`) — this directory previously
had no `.ruby-version` file and silently fell back to whatever system Ruby
was on `PATH` (3.0.2 here), inconsistent with every `week1_baseline/ruby/*`
step. Fixed as part of adding the `sqlite3` gem, which needs the matching
Ruby version's precompiled native extension.

## Layout

```
lib/boukensha/
  observation/
    result.rb    -- Observation::Result: a parsed room (name, description, exits, mobs, items)
    parser.rb     -- Observation::Parser.parse: raw look/check text -> Result
    on_entry.rb    -- Observation::OnEntry.call: the "map where I am" loop, wired to policy + world
  memory/
    world.rb        -- Memory::World: the room graph, BFS route(from:, to:) / route_to(from:, destination_name:)
    sqlite_store.rb  -- Memory::SqliteStore: durable rooms/exits + the room_visits ledger (optional store: collaborator)
  control/
    mode.rb         -- Control::Mode: :observe / :act
    policy.rb        -- Control::Policy: allow/deny tool rules per mode, enforce!
  observable.rb        -- requires everything above EXCEPT sqlite_store.rb
                          (kept out so the sqlite3 gem stays opt-in --
                          require "boukensha/memory/sqlite_store" explicitly
                          where it's actually used)
```

## The SQLite layer

`Memory::World` works exactly as before with no `store:` — nothing above
requires SQLite. Pass a `Memory::SqliteStore` to get durable, queryable
persistence instead of (or alongside) `World#dump`/`.load`'s YAML blob:

```ruby
require "boukensha/memory/sqlite_store"

store = Boukensha::Memory::SqliteStore.new(".boukensha/world.sqlite3")
world = Boukensha::Memory::World.new(store: store)
store.hydrate(world)   # optional: rehydrate everything already known

Boukensha::Observation::OnEntry.call(
  dispatcher: dispatcher, world: world,
  character: "wanderer", session_id: "20260806T...-abcd1234"  # enables room_visits logging
)

world.route_to(from: some_identity, destination_name: "The Temple Of Midgaard")
store.visit_count(some_identity, character: "wanderer")  # how many times, real query, not a guess
```

`character:`/`session_id:` are both required together to log a
`room_visits` row — omit either and `OnEntry` behaves exactly as it did
before this plan (mapping still happens, just without visit tracking).

## Try it

```
ruby examples/demo.rb
```

Runs the whole pipeline against fixture `look` text (no live MUD needed) —
parses two rooms, builds the graph, and shows the computed route back to
"The Temple Of Midgaard", plus a policy rejection when `:observe` mode is
asked to call `move`.

### Against a real MUD

```
MUD_NAME=<character> MUD_PASSWORD=<password> ruby examples/live_demo.rb
MUD_NAME=<character> MUD_PASSWORD=<password> ruby examples/live_walk_demo.rb
```

Wires `Observation::OnEntry` to the real `mud_manager_mcp` server, reusing
`Boukensha::MCP` (the client from `week1_baseline/ruby/12_context`)
unmodified — no new MCP protocol code, just a small adapter from
`#call_tool` to the `#call` shape `OnEntry`'s `dispatcher:` expects.
`live_demo.rb` maps the current room; `live_walk_demo.rb` also moves one
step (under `:act` mode) and re-maps, proving the graph/route-to-home logic
against a second real room. Defaults to the `mud:` block in
`.boukensha/settings.yaml`; override with `MUD_NAME`/`MUD_PASSWORD` env vars
for a different character. See "Verified live" in
[`docs/plans/observable.md`](../../docs/plans/observable.md) for what
real-server testing found that fixture text alone didn't catch (ANSI codes,
the actual `check kind: where` format, a login-flow bug fixed in
`mud_manager` itself). `examples/bootstrap_character.rb <name> <password>`
creates a fresh ordinary character if you need one.

## Test

```
bundle install   # first time only -- installs the sqlite3 gem
for f in tests/test_*.rb; do ruby "$f"; done
```

Pure Minitest (Ruby stdlib) — everything except `test_memory_sqlite_store.rb`
and the sqlite-backed cases in `test_observation_on_entry.rb` needs no gem
at all; those two use a real (temp-file) SQLite database, no live MUD
server required either way. `Observation::OnEntry` takes any `dispatcher`
responding to `#call(tool_name, **args)`, so wiring it to a real
`Boukensha::Registry` (see `week1_baseline/ruby/10_standard_tool_library`)
or `mud_manager_mcp` is a matter of passing the real dispatcher in —
nothing here depends on either.
