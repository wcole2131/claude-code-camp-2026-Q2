import os
from pathlib import Path

import boukensha

repo_root = Path(__file__).resolve().parents[4]
os.environ.setdefault("BOUKENSHA_DIR", str(repo_root / ".boukensha"))

# The base directory tools operate relative to — the 07_the_run_dsl step folder
# makes a good playground since it already has source files to read.
base_dir = Path(__file__).resolve().parents[2] / "07_the_run_dsl"

print(f"Config: {boukensha.get_config()}")
print()

boukensha.repl(working_dir=base_dir)
