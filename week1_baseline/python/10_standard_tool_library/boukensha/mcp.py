from __future__ import annotations

import atexit
import json
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .version import VERSION

if TYPE_CHECKING:
    from .registry import Registry

# A generic MCP (Model Context Protocol) client over stdio.
#
# Connects to *any* MCP server -- not just mud_manager_mcp -- by spawning it
# as a subprocess and speaking the minimal JSON-RPC 2.0 subset needed for
# tool calling: initialize, notifications/initialized, tools/list,
# tools/call. It discovers whatever tools the server advertises at connect
# time and can register all of them against a Registry generically -- the
# registry never knows or needs to know the tools came from MCP.
#
# Usage:
#
#   client = MCPClient.connect(
#       command=["bundle", "exec", "ruby", "bin/mud_manager_server"],
#       cwd="../../mud_manager_mcp",
#       env={"MUD_HOST": "localhost", "MUD_NAME": "Gandalf", "MUD_PASSWORD": "secret"},
#   )
#   client.register_all(registry)
#
# See docs/plans/mud_manager/mcp_generalization_plan.md for the design
# rationale (why this exists as its own client, separate from any one
# server it happens to talk to). Mirrors Boukensha::MCP (lib/boukensha/mcp.rb).

PROTOCOL_VERSION = "2024-11-05"

# week1_baseline/, computed from this file's location
# (boukensha/mcp.py -> boukensha -> 10_standard_tool_library -> python -> week1_baseline),
# for the convenience factory methods below.
_WEEK1_BASELINE_DIR = Path(__file__).resolve().parents[3]


class MCPError(RuntimeError):
    pass


class MCPClient:
    def __init__(
        self,
        *,
        command: list[str],
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        # Strip any inherited Bundler env before spawning -- without this, a
        # Ruby MCP server launched via `bundle exec` from inside a process
        # that itself inherited BUNDLE_GEMFILE/RUBYOPT (e.g. a shell that
        # ran a ruby bundle exec command earlier) would resolve against the
        # wrong Gemfile instead of doing a fresh cwd-based lookup in `cwd`.
        base_env = {k: v for k, v in os.environ.items() if not k.startswith("BUNDLE_") and k != "RUBYOPT"}
        full_env = {**base_env, **(env or {})}
        self._proc = subprocess.Popen(
            command,
            cwd=cwd,
            env=full_env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,  # inherit -- server warnings surface directly, no pipe to drain
            text=True,
            bufsize=1,  # line-buffered
        )
        self._next_id = 0
        self._tools_cache: list[dict[str, Any]] | None = None
        atexit.register(self.close)

    @classmethod
    def connect(
        cls,
        *,
        command: list[str],
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> MCPClient:
        client = cls(command=command, cwd=cwd, env=env)
        client._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "boukensha", "version": VERSION},
            },
        )
        client._notify("notifications/initialized", {})
        return client

    # Convenience specs for this repo's three bundled MCP servers, for use
    # with boukensha.run/repl's mcp_servers:. Raw {command, cwd, env} dicts
    # matching MCPClient.connect's kwargs -- nothing about connecting to
    # them is special, these are just shorthand so common cases don't need
    # to spell out a subprocess command by hand. See
    # docs/plans/mud_manager/mcp_mud_plan.md, decision 3.

    @staticmethod
    def file_system_server(*, working_dir: str | Path) -> dict[str, Any]:
        return {
            "command": ["bundle", "exec", "ruby", "bin/file_system_mcp_server"],
            "cwd": _WEEK1_BASELINE_DIR / "file_system_mcp",
            "env": {"WORKING_DIR": str(Path(working_dir).resolve())},
        }

    @staticmethod
    def shell_server(
        *, working_dir: str | Path, timeout: int = 30, allowed_commands: list[str] | None = None
    ) -> dict[str, Any]:
        env = {"WORKING_DIR": str(Path(working_dir).resolve()), "SHELL_TIMEOUT": str(timeout)}
        if allowed_commands:
            env["ALLOWED_COMMANDS"] = ",".join(allowed_commands)
        return {
            "command": ["bundle", "exec", "ruby", "bin/shell_mcp_server"],
            "cwd": _WEEK1_BASELINE_DIR / "shell_mcp",
            "env": env,
        }

    @staticmethod
    def mud_manager_server(*, name: str, password: str, host: str = "localhost", port: int = 4000) -> dict[str, Any]:
        return {
            "command": ["bundle", "exec", "ruby", "bin/mud_manager_server"],
            "cwd": _WEEK1_BASELINE_DIR / "mud_manager_mcp",
            "env": {"MUD_HOST": host, "MUD_PORT": str(port), "MUD_NAME": name, "MUD_PASSWORD": password},
        }

    def tools(self) -> list[dict[str, Any]]:
        if self._tools_cache is None:
            self._tools_cache = self._request("tools/list", {})["tools"]
        return self._tools_cache

    def call_tool(self, name: str, **args: Any) -> str:
        result = self._request("tools/call", {"name": name, "arguments": args})
        return self._content_to_string(result.get("content", []))

    def register_all(self, registry: Registry) -> None:
        for tool in self.tools():
            name = tool["name"]
            registry.tool(
                name,
                description=tool.get("description", ""),
                parameters=self._schema_to_parameters(tool.get("inputSchema")),
                block=self._make_block(name),
            )

    def close(self) -> None:
        if self._proc.poll() is not None:
            return
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
            self._proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            self._proc.kill()

    def _make_block(self, name: str) -> Any:
        return lambda **args: self.call_tool(name, **args)

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._proc.poll() is not None:
            raise MCPError(f"{method}: server is not running")

        self._next_id += 1
        request_id = self._next_id

        assert self._proc.stdin is not None
        assert self._proc.stdout is not None
        self._proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}) + "\n")
        self._proc.stdin.flush()

        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise MCPError(f"{method}: server closed the connection")

            message = json.loads(line)
            if message.get("id") != request_id:
                continue

            if "error" in message:
                raise MCPError(f"{method}: {message['error']['message']}")
            return message["result"]

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        assert self._proc.stdin is not None
        self._proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method, "params": params}) + "\n")
        self._proc.stdin.flush()

    @staticmethod
    def _content_to_string(content: list[dict[str, Any]]) -> str:
        if not content:
            return ""
        parts = []
        for block in content:
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            else:
                parts.append(f"[unsupported content type: {block.get('type')}]")
        return "".join(parts)

    @staticmethod
    def _schema_to_parameters(input_schema: dict[str, Any] | None) -> dict[str, Any]:
        if not input_schema:
            return {}
        properties = input_schema.get("properties", {})
        required = set(input_schema.get("required", []))
        parameters: dict[str, Any] = {}
        for name, spec in properties.items():
            entry: dict[str, Any] = {"type": spec.get("type"), "description": spec.get("description")}
            if name not in required:
                entry["required"] = False
            parameters[name] = entry
        return parameters
