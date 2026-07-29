from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..registry import Registry

# FileSystem registers the standard set of file-oriented tools against a
# registry, all sandboxed to a single root directory.
#
# Tools registered:
#   pwd              -- return the working directory
#   list_directory    -- list files and subdirectories at a path
#   read_file        -- read the full contents of a file
#   write_file       -- write (or overwrite) a file
#   delete_file      -- delete a file
#   search_files     -- grep for a pattern across files in the working tree
#
# Every path argument the agent supplies is resolved relative to that root.
# If the resolved path would escape the root (path traversal) the tool
# returns an error string rather than raising -- so the agent sees it and
# can try something sensible instead.


def register(registry: Registry, *, working_dir: str | Path) -> None:
    root = Path(os.path.abspath(os.path.expanduser(str(working_dir))))

    def resolve(path: str) -> Path | str:
        absolute = Path(os.path.normpath(os.path.join(root, path)))
        if absolute == root or str(absolute).startswith(f"{root}{os.sep}"):
            return absolute
        return f"error: path '{path}' escapes the working directory"

    def oops(msg: str) -> str:
        return f"error: {msg}"

    registry.tool(
        "pwd",
        description="Return the working directory — the root that all file paths are relative to.",
        parameters={},
        block=lambda: str(root),
    )

    def list_directory(*, path: str = ".") -> str:
        target = resolve(path)
        if isinstance(target, str):
            return target
        if not target.is_dir():
            return oops(f"'{path}' is not a directory")

        entries = sorted(f"{p.name}/" if p.is_dir() else p.name for p in target.iterdir())
        return "\n".join(entries) if entries else "(empty)"

    registry.tool(
        "list_directory",
        description=(
            "List files and subdirectories at a path relative to the working directory. "
            "Defaults to the working directory itself."
        ),
        parameters={"path": {"type": "string", "description": "Relative path to list (default '.')"}},
        block=list_directory,
    )

    def read_file(*, path: str) -> str:
        target = resolve(path)
        if isinstance(target, str):
            return target
        if not target.is_file():
            return oops(f"'{path}' is not a file")
        try:
            return target.read_text()
        except (OSError, UnicodeDecodeError) as e:
            return oops(str(e))

    registry.tool(
        "read_file",
        description="Read and return the full contents of a file. Path is relative to the working directory.",
        parameters={"path": {"type": "string", "description": "Relative path to the file"}},
        block=read_file,
    )

    def write_file(*, path: str, content: str) -> str:
        target = resolve(path)
        if isinstance(target, str):
            return target
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            rel = target.relative_to(root)
            return f"ok: wrote {len(content.encode())} bytes to {rel}"
        except OSError as e:
            return oops(str(e))

    registry.tool(
        "write_file",
        description=(
            "Write content to a file, creating it (and any missing parent directories) if needed, "
            "overwriting if it exists. Path is relative to the working directory."
        ),
        parameters={
            "path": {"type": "string", "description": "Relative path to the file"},
            "content": {"type": "string", "description": "Text content to write"},
        },
        block=write_file,
    )

    def delete_file(*, path: str) -> str:
        target = resolve(path)
        if isinstance(target, str):
            return target
        if not target.is_file():
            return oops(f"'{path}' is not a file")
        try:
            target.unlink()
            return f"ok: deleted {path}"
        except OSError as e:
            return oops(str(e))

    registry.tool(
        "delete_file",
        description="Delete a file. Directories are not deleted. Path is relative to the working directory.",
        parameters={"path": {"type": "string", "description": "Relative path to the file to delete"}},
        block=delete_file,
    )

    def search_files(*, pattern: str, path: str = ".", glob: str = "*") -> str:
        target = resolve(path)
        if isinstance(target, str):
            return target

        files = [target] if target.is_file() else sorted(target.glob(f"**/{glob}"), key=str)

        try:
            regex = re.compile(pattern)
        except re.error as e:
            return oops(f"invalid pattern: {e}")

        matches: list[str] = []
        for file in files:
            if not file.is_file():
                continue
            rel = file.relative_to(root)
            try:
                for lineno, line in enumerate(file.read_text().splitlines(), start=1):
                    if regex.search(line):
                        matches.append(f"{rel}:{lineno}:{line}")
            except (OSError, UnicodeDecodeError) as e:
                matches.append(f"{rel}: error reading file: {e}")

        return "\n".join(matches) if matches else "no matches"

    registry.tool(
        "search_files",
        description=(
            "Search for a text pattern (literal string or regex) across all files in the working "
            "directory tree. Returns matching lines in 'path:line_number:content' format."
        ),
        parameters={
            "pattern": {"type": "string", "description": "The text or regex pattern to search for"},
            "path": {
                "type": "string",
                "description": "Subdirectory or file to search within (default '.' = entire working directory)",
            },
            "glob": {
                "type": "string",
                "description": "File glob to restrict which files are searched, e.g. '*.py' (default '*')",
            },
        },
        block=search_files,
    )
