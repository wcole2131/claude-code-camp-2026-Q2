import os
from pathlib import Path

import boukensha
from boukensha import RunDSL

repo_root = Path(__file__).resolve().parents[4]
os.environ.setdefault("BOUKENSHA_DIR", str(repo_root / ".boukensha"))

base_dir = Path(__file__).resolve().parent.parent


def configure(dsl: RunDSL) -> None:
    dsl.tool(
        "read_file",
        description="Read the contents of a file from disk",
        parameters={"path": {"type": "string", "description": "The file path to read"}},
        block=lambda *, path: Path(base_dir, path).resolve().read_text(),
    )

    dsl.tool(
        "list_directory",
        description="List the files in a directory",
        parameters={"path": {"type": "string", "description": "The directory path to list"}},
        block=lambda *, path: ", ".join(f for f in os.listdir(Path(base_dir, path).resolve()) if not f.startswith(".")),
    )


print("=== BOUKENSHA Step 7: The Boukensha.run DSL ===")
print()
print(f"Config: {boukensha.get_config()}")
print()

result = boukensha.run(
    task="Read the README.md file and summarise what this MUD player assistant framework can do.",
    configure=configure,
)

print()
print("=== FINAL RESPONSE ===")
print(result)
