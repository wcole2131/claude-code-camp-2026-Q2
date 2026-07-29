from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..registry import Registry

# Shell registers command-execution tools against a registry.
#
# Tools registered:
#   run_command  -- run an arbitrary shell command inside the working directory
#
# Options:
#   working_dir:      (required) all commands run with this as their cwd
#   timeout:          seconds before a command is killed (default 30)
#   allowed_commands: optional list of allowed executable names (e.g. ["python3", "git"]).
#                     When None (the default) all commands are permitted.
#                     When set, any command whose first token is not in the list
#                     is rejected before execution.


def register(
    registry: Registry,
    *,
    working_dir: str | Path,
    timeout: int = 30,
    allowed_commands: list[str] | None = None,
) -> None:
    root = Path(os.path.abspath(os.path.expanduser(str(working_dir))))

    def oops(msg: str) -> str:
        return f"error: {msg}"

    def run_command(*, command: str) -> str:
        if allowed_commands is not None:
            executable = command.strip().split()[0] if command.strip() else ""
            if executable not in allowed_commands:
                return oops(
                    f"'{executable}' is not in the allowed-commands list ({', '.join(allowed_commands)})"
                )

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                text=True,
                check=False,
            )
        except FileNotFoundError as e:
            return oops(f"command not found: {e}")
        except subprocess.TimeoutExpired:
            return oops(f"command timed out after {timeout}s: {command}")
        except OSError as e:
            return oops(str(e))

        exit_note = "" if result.returncode == 0 else f"\n[exit {result.returncode}]"
        output = result.stdout.strip()
        return f"(no output){exit_note}" if not output else f"{output}{exit_note}"

    allowed_note = f" Allowed executables: {', '.join(allowed_commands)}." if allowed_commands else ""
    registry.tool(
        "run_command",
        description=(
            "Run a shell command inside the working directory and return its combined stdout+stderr "
            f"output. Commands run with a {timeout}-second timeout.{allowed_note}"
        ),
        parameters={
            "command": {
                "type": "string",
                "description": "The shell command to execute (e.g. 'python3 script.py', 'ls -la', 'git status')",
            }
        },
        block=run_command,
    )
