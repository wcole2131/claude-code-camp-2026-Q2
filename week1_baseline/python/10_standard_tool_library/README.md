# 10 · A Standard Tool Library (Python port)

Python port of `week1_baseline/ruby/10_standard_tool_library`. Boukensha now ships two built-in
tool modules — instead of manually registering tools, a real coding harness gives the agent a
standard library of capabilities out of the box.

## What's new

### `boukensha.tools.file_system`

Registers automatically when `working_dir=` is set:

| Tool | Description |
|------|-------------|
| `pwd` | Return the working directory |
| `list_directory` | List files at a path (default `.`) |
| `read_file` | Read a file's contents |
| `write_file` | Write (or create) a file |
| `delete_file` | Delete a file |
| `search_files` | Grep for a regex pattern across the working tree, returns `path:line:content` matches |

All paths are **relative to the working directory**. Absolute paths and `..` traversals that
escape the root are rejected with an error string, not an exception — the agent sees the error and
can try something sensible instead.

### `boukensha.tools.shell`

Registers automatically when `working_dir=` is set:

| Tool | Description |
|------|-------------|
| `run_command` | Run a shell command inside the working directory |

Commands run with a configurable timeout and an optional allow-list of permitted executables.

### New `boukensha.run` / `boukensha.repl` keyword arguments

```python
boukensha.run(
    task="...",
    working_dir="/my/project",
    allowed_commands=["python3", "git"],  # None = allow all (default)
    shell_timeout=30,                     # seconds, default 30
)
```

`working_dir` defaults to the current working directory; pass `working_dir=False` to skip
registering any filesystem/shell tools entirely. `allowed_commands=None` permits any executable.
Pass an explicit list to lock the agent down:

```python
# Only allow python3 and git — rm, curl, etc. will be rejected
boukensha.run(task="...", allowed_commands=["python3", "git"])
```

### Direct registration

Both modules can be registered manually if you need finer control:

```python
from boukensha.tools import file_system, shell

file_system.register(registry, working_dir="/my/project")
shell.register(registry, working_dir="/my/project", timeout=10, allowed_commands=["python3"])
```

## Run the demo

```sh
week1_baseline/bin/python/10_standard_tool_library
```

The demo drops you into a REPL with `working_dir` pointed at the `07_the_run_dsl` step's folder —
ask the agent to list the directory, read a file, search for something, or run a shell command
(e.g. `ls`, `wc -l boukensha/*.py`) against it.

## Scope: `Tools::Mud` is not ported

Ruby's step also ships a third tool module, `Boukensha::Tools::Mud` (25 tools wrapping a separate
`mud_manager` gem — a raw-socket CircleMUD telnet session/primitives library under
`week0_explore/mud_manager/`). That gem has no Python equivalent anywhere in this repo, and
building one is a materially different, larger undertaking than translating this step's Ruby
idioms (it needs its own session/protocol layer and a live MUD server to test against). It's left
out of this port; `boukensha.run`/`boukensha.repl` have no `mud=` keyword argument, and there is no
`boukensha/tools/mud.py`. Ruby's own Ruby-only packaging additions for this step (`bin/boukensha`,
`boukensha.gemspec`, `lib/boukensha_loader.rb`, turning the gem into a global executable) also have
no Python analog — this port keeps using the `week1_baseline/bin/python/<step>` launcher
convention established since `00_config`.

## Technical Considerations

Observations we don't want to fix right now, just to preserve for future steps:

- There's not yet enough tool coverage to accomplish every task efficiently — several agent goals
  would still map down to the same handful of primitives (`run_command` as an escape hatch for
  anything `FileSystem` doesn't cover directly).
