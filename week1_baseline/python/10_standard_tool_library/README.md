# 10 · A Standard Tool Library (Python port)

Python port of `week1_baseline/ruby/10_standard_tool_library`. **Boukensha ships no tool
implementations of its own** — every capability (filesystem, shell, MUD) lives outside the
framework as its own standalone MCP server (`week1_baseline/file_system_mcp`, `shell_mcp`,
`mud_manager_mcp`), and `boukensha` only ships the generic mechanism to connect to them:
`Registry`/`Tool`/`Context`, plus `boukensha.mcp.MCPClient` — a client that can connect to *any*
MCP server and discover/register whatever tools it advertises. See
`docs/plans/mud_manager/mcp_mud_plan.md` for why this is the target architecture, not a missing
feature — `boukensha.tools.file_system`/`.shell`/`.mud` (hand-written per-language modules) no
longer exist in this step at all.

## `boukensha.run` / `boukensha.repl`'s `mcp_servers=`

```python
boukensha.run(
    task="...",
    mcp_servers=[
        MCPClient.file_system_server(working_dir="/my/project"),
        MCPClient.shell_server(working_dir="/my/project", allowed_commands=["python3", "git"]),
        MCPClient.mud_manager_server(name="Gandalf", password="secret"),
    ],
)
```

`mcp_servers=` is the literal, honest shape of "tools are not part of the agent" — a list of
`{command, cwd, env}` specs, each connected via `MCPClient.connect(**spec).register_all(registry)`.
`MCPClient.file_system_server`/`.shell_server`/`.mud_manager_server` are convenience factories
building the right spec for this repo's three bundled (Ruby) servers — nothing about connecting to
them is Python-specific or otherwise special.

Leave `mcp_servers=` unset (the default, `None`) and `run`/`repl` build a sensible default set
instead: `file_system_mcp` + `shell_mcp` rooted at `working_dir=` (default: current directory; pass
`working_dir=False` to exclude both), plus `mud_manager_mcp` if `settings.yaml`'s `mud:` block has
`mud_username` configured.

```python
# Only allow python3 and git — rm, curl, etc. will be rejected
boukensha.run(task="...", working_dir="/my/project", allowed_commands=["python3", "git"])
```

`allowed_commands=`/`shell_timeout=` only affect the default `shell_mcp` spec. Pass
`mcp_servers=[]` to connect to nothing, or your own list to take full control.

## `boukensha.mcp.MCPClient` — the generic client

```python
client = MCPClient.connect(command=[...], cwd="...", env={...})
client.tools()                    # tools/list result
client.call_tool("look")          # tools/call result, unwrapped to a string
client.register_all(registry)     # registers every discovered tool generically
client.close()
```

Tests live in `tests/test_tools_mud.py` (against `tests/fake_circlemud.py`, a fake CircleMUD
double), `tests/test_tools_file_system.py`, and `tests/test_tools_shell.py` — all spawn the real
Ruby MCP servers, skipped automatically if `bundle`/Ruby isn't available. `tests/test_mcp_client.py`
proves `MCPClient.register_all` isn't secretly MUD- or filesystem-shaped: it spawns
`tests/toy_mcp_server.py`, a two-tool toy MCP server with zero relation to any of this repo's real
servers, and drives it through the exact same generic code path.

## Run the demo

```sh
week1_baseline/bin/python/10_standard_tool_library
```

The demo drops you into a REPL with `working_dir` pointed at the `07_the_run_dsl` step's folder —
ask the agent to list the directory, read a file, search for something, or run a shell command
(e.g. `ls`, `wc -l boukensha/*.py`) against it.

## Scope: Ruby's packaging additions are not ported

Ruby's own Ruby-only packaging additions for this step (`bin/boukensha`, `boukensha.gemspec`,
`lib/boukensha_loader.rb`, turning the gem into a global executable) have no Python analog — this
port keeps using the `week1_baseline/bin/python/<step>` launcher convention established since
`00_config`. Tool implementations aren't part of this scope question at all anymore — since none of
`file_system`/`shell`/`mud` live inside either language's `boukensha` package, there's nothing left
to port per language for them; every language's agent reaches the same bundled servers the same way.

## Technical Considerations

Observations we don't want to fix right now, just to preserve for future steps:

- There's not yet enough tool coverage to accomplish every task efficiently — several agent goals
  would still map down to the same handful of primitives (`run_command` as an escape hatch for
  anything `file_system_mcp` doesn't cover directly).
