import os
from pathlib import Path

import boukensha
from boukensha import RunDSL

repo_root = Path(__file__).resolve().parents[4]
os.environ.setdefault("BOUKENSHA_DIR", str(repo_root / ".boukensha"))

# The base directory tools operate relative to — the 07_the_run_dsl step folder
# makes a good playground since it already has source files to read.
base_dir = Path(__file__).resolve().parents[2] / "07_the_run_dsl"


def configure(dsl: RunDSL) -> None:
    dsl.tool(
        "read_file",
        description="Read the contents of a file from disk",
        parameters={"path": {"type": "string", "description": "File path (relative to the working directory)"}},
        block=lambda *, path: Path(base_dir, path).resolve().read_text(),
    )

    dsl.tool(
        "list_directory",
        description="List the files in a directory",
        parameters={
            "path": {
                "type": "string",
                "description": "Directory path (relative to the working directory, or '.' for root)",
            }
        },
        block=lambda *, path: ", ".join(
            sorted(f for f in os.listdir(Path(base_dir, path).resolve()) if not f.startswith("."))
        ),
    )


print(f"Config: {boukensha.get_config()}")
print()

boukensha.repl(configure=configure)
