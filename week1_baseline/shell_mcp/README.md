# shell_mcp — a real MCP server for shell command execution

Same rationale as `file_system_mcp` (see that directory's README and
`docs/plans/mud_manager/mcp_mud_plan.md`): the Boukensha agent framework
ships no shell tool implementation of its own. `run_command` lives here
instead, as its own standalone MCP server.

## Config

| Variable | Required | Default | Meaning |
|----------|----------|---------|---------|
| `WORKING_DIR` | yes | — | Commands run with this as their cwd. |
| `SHELL_TIMEOUT` | no | `30` | Seconds before a command is killed. |
| `ALLOWED_COMMANDS` | no | unset = allow all | Comma-separated executable allow-list, e.g. `ruby,git,bundle`. Any command whose first token isn't in the list is rejected before execution. |

## Running it

```sh
bundle install   # first time only
WORKING_DIR=/my/project ALLOWED_COMMANDS=ruby,git bundle exec ruby bin/shell_mcp_server
```

Speaks JSON-RPC 2.0 over stdio, same protocol as `mud_manager_mcp` and
`file_system_mcp`.

## What lives here vs. what doesn't

- **`bin/shell_mcp_server`** — the MCP server, using the generic
  `Boukensha::MCP::Server` (a Bundler path dependency on
  `../ruby/10_standard_tool_library`, for the generic primitives only).
- **`lib/shell_tools.rb`** — the actual tool definition, moved here from
  `Boukensha::Tools::Shell` (which no longer exists — the framework has no
  built-in tools).
