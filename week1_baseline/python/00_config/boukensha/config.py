from __future__ import annotations

import os
from pathlib import Path
from typing import Any, overload

import yaml
from dotenv import load_dotenv

# The .boukensha config directory is resolved in this order:
#   1. BOUKENSHA_DIR environment variable (set before loading .env)
#   2. ~/.boukensha  (default)
DEFAULT_DIR = Path.home() / ".boukensha"

# Default prompts shipped alongside the library code.
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class Config:
    def __init__(self) -> None:
        self._dir = self._resolve_dir()
        self._load_env()
        self._settings = self._load_settings()

    @property
    def dir(self) -> Path:
        return self._dir

    @property
    def settings(self) -> dict[str, Any]:
        return self._settings

    # ---------- tasks -----------------------------------------------------

    @overload
    def tasks(self, name: None = None) -> dict[str, Any]: ...
    @overload
    def tasks(self, name: str) -> dict[str, Any] | None: ...

    def tasks(self, name: str | None = None) -> dict[str, Any] | None:
        all_tasks = self.dig("tasks") or {}
        return all_tasks if name is None else all_tasks.get(name)

    @property
    def user_prompts_dir(self) -> Path:
        return self._dir / "prompts"

    # ---------- MUD connection ---------------------------------------------

    @property
    def mud_host(self) -> str:
        return self.dig("mud", "host") or "localhost"

    @property
    def mud_port(self) -> int:
        return self.dig("mud", "port") or 4000

    @property
    def mud_username(self) -> str | None:
        return self.dig("mud", "username")

    @property
    def mud_password(self) -> str | None:
        return self.dig("mud", "password")

    # ---------- low-level helpers -------------------------------------------

    def dig(self, *keys: str) -> Any:
        node: Any = self._settings
        for key in keys:
            node = node.get(key) if isinstance(node, dict) else None
        return node

    def __str__(self) -> str:
        return f"#<Boukensha::Config dir={self._dir} tasks={','.join(self.tasks().keys())}>"

    __repr__ = __str__

    def _resolve_dir(self) -> Path:
        raw = os.environ.get("BOUKENSHA_DIR") or str(DEFAULT_DIR)
        return Path(raw).expanduser().resolve()

    def _load_env(self) -> None:
        env_file = self._dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)

    def _load_settings(self) -> dict[str, Any]:
        settings_file = self._dir / "settings.yaml"
        if settings_file.exists():
            return yaml.safe_load(settings_file.read_text()) or {}
        return {}
