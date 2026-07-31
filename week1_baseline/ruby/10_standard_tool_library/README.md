# Step 10 — A Standard Tool Library

## Build

gem build boukensha.gemspec
gem install boukensha-0.10.0.gem

**Boukensha ships no tool implementations of its own.** Every capability — filesystem, shell,
MUD — lives outside the framework as its own standalone MCP server, and the agent gets its entire
tool surface by connecting to whichever ones you point it at. This is a deliberate architecture,
not a missing feature: see `docs/plans/mud_manager/mcp_mud_plan.md` for why. The framework itself
only ships the generic mechanism: `Registry`/`Tool`/`Context`, plus `Boukensha::MCP` — a client that
can connect to *any* MCP server and discover/register whatever tools it advertises, and
`Boukensha::MCP::Server` — the matching generic server-side helper every bundled MCP server uses.

## The three bundled servers

| Server | Directory | Tools |
|---|---|---|
| `file_system_mcp` | `week1_baseline/file_system_mcp/` | `pwd`, `list_directory`, `read_file`, `write_file`, `delete_file`, `search_files` |
| `shell_mcp` | `week1_baseline/shell_mcp/` | `run_command` |
| `mud_manager_mcp` | `week1_baseline/mud_manager_mcp/` | 27 MUD gameplay tools wrapping `mud_manager` (`mud_connect`/`look`/`attack`/`shop`/`send_raw`/...) |

Each is a real MCP server (JSON-RPC 2.0 over stdio: `initialize` → `tools/list` → `tools/call`) —
see their own READMEs for config (env vars) and protocol details. None of them are Ruby-specific in
principle; they just happen to be written in Ruby today (`mud_manager` requires it; the other two
could be any language, but there's no reason to duplicate them per language once they're servers).

## `Boukensha.run` / `Boukensha.repl`'s `mcp_servers:`

```ruby
Boukensha.run(
  task: "...",
  mcp_servers: [
    Boukensha::MCP.file_system_server(working_dir: "/my/project"),
    Boukensha::MCP.shell_server(working_dir: "/my/project", allowed_commands: ["ruby", "git"]),
    Boukensha::MCP.mud_manager_server(name: "Gandalf", password: "secret"),
  ]
)
```

`mcp_servers:` is the honest, literal shape of "tools are not part of the agent" — a list of
`{command:, dir:, env:}` specs, each connected via `Boukensha::MCP.connect(**spec).register_all(registry)`.
`Boukensha::MCP.file_system_server`/`.shell_server`/`.mud_manager_server` are just convenience
factories building the right spec for this repo's three bundled servers — nothing about connecting
to them is special.

Leave `mcp_servers:` unset and `run`/`repl` build a sensible default set instead: `file_system_mcp` +
`shell_mcp` rooted at `working_dir:` (default `Dir.pwd`; pass `working_dir: false` to exclude both),
plus `mud_manager_mcp` if `settings.yaml`'s `mud:` block has a `username` configured. `allowed_commands:`
and `shell_timeout:` only affect this default `shell_mcp` spec. Pass `mcp_servers: []` to connect to
nothing, or your own list to take full control.

```ruby
Boukensha.run(task: "...", working_dir: "/my/project", allowed_commands: ["ruby", "git"])
```

## `Boukensha::MCP` — the generic client

```ruby
client = Boukensha::MCP.connect(command: [...], dir: "...", env: {...})
client.tools                    # => tools/list result
client.call_tool("look")        # => tools/call result, unwrapped to a String
client.register_all(registry)   # registers every discovered tool generically
client.close
```

`register_all` is what `mcp_servers:` uses internally for each spec. Nothing about it is MUD- or
filesystem-specific — it was verified against a two-tool toy MCP server with zero relation to any
of this repo's actual servers (see `week1_baseline/python/10_standard_tool_library/tests/test_mcp_client.py`
and `tests/toy_mcp_server.py`) specifically to prove that.

## Run the demo

```sh
ruby examples/demo.rb

# or via the global executable pointed at this step:
BOUKENSHA_PATH=~/Sites/boukensha/10_standard_tool_library boukensha
```

## Technical Considerations
This is observations we dont want to fix these right now just to perserve current future layers.

- There could be a case where is a session is already in use for a user they are prompted with Yes or No
to kill the session and our agent's/mud manager doesn't have a way to handle that case.
- It seems like we need more tool work, as there might not be enough tools to accomplish
tasks efficiently and mostly are mapping the same task to primitive.