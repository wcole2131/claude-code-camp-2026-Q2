# file_system_mcp — a real MCP server for filesystem tools

The Boukensha agent framework (`week1_baseline/ruby/10_standard_tool_library`
and its Python port) ships no filesystem tool implementation of its own.
`pwd`/`list_directory`/`read_file`/`write_file`/`delete_file`/`search_files`
live here instead, as their own standalone MCP server — the same shape as
`mud_manager_mcp`, just for a different domain. See
`docs/plans/mud_manager/mcp_mud_plan.md` for the full rationale: the agent
shouldn't have any built-in tools at all, so every capability, not just the
one (MUD) with a hard cross-language blocker, is served over MCP the same
way.

One consequence worth noting: since this is a standalone server rather than
a per-language module, there's no more reason for a `file_system.py` to
exist alongside `file_system.rb` — every language's agent connects to this
one server via `Boukensha::MCP`/`MCPClient`, instead of each language
re-implementing the same filesystem logic.

## Config

| Variable | Required | Meaning |
|----------|----------|---------|
| `WORKING_DIR` | yes | All file paths are resolved relative to this root. Absolute paths and `..` traversals that would escape it are rejected with an error string, not an exception. |

## Running it

```sh
bundle install   # first time only
WORKING_DIR=/my/project bundle exec ruby bin/file_system_mcp_server
```

Speaks JSON-RPC 2.0 over stdio (`initialize` → `tools/list` → `tools/call`),
same protocol as `mud_manager_mcp` — see that directory's README for the
wire-format details, since they're identical here.

## What lives here vs. what doesn't

- **`bin/file_system_mcp_server`** — the MCP server, using the generic
  `Boukensha::MCP::Server` (a Bundler path dependency on
  `../ruby/10_standard_tool_library`, for the generic primitives only —
  `Registry`/`Context`/`Server`, nothing filesystem-specific).
- **`lib/file_system_tools.rb`** — the actual tool definitions, moved here
  from `Boukensha::Tools::FileSystem` (which no longer exists — the
  framework has no built-in tools).
