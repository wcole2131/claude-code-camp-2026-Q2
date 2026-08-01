from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# The .boukensha config directory is resolved in this order:
#   1. BOUKENSHA_DIR environment variable (set before loading .env)
#   2. ~/.boukensha  (default)
DEFAULT_DIR = Path.home() / ".boukensha"


class Config:
    def __init__(self) -> None:
        self._dir = self._resolve_dir()
        self._load_env()
        self._settings = self._load_settings()
        self._system_prompt = self._load_system_prompt()

    @property
    def dir(self) -> Path:
        return self._dir

    @property
    def settings(self) -> dict[str, Any]:
        return self._settings

    # ---------- provider -----------------------------------------------------

    @property
    def provider_type(self) -> str:
        return self.dig("tasks", "player", "provider") or "anthropic"

    @property
    def model(self) -> str:
        return self.dig("tasks", "player", "model") or "claude-haiku-4-5"

    # ---------- system prompt -------------------------------------------------

    @property
    def system_prompt(self) -> str | None:
        return self._system_prompt

    @property
    def system_override(self) -> bool:
        return self.dig("system", "override") is True

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

    # ---------- agent limits ----------------------------------------------
    # Static per-turn circuit breakers, read where the agent is constructed.
    # A value of 0 or nil means "disabled" (no ceiling) -- useful for debugging.

    @property
    def agent_max_iterations(self) -> int:
        v = self.dig("agent", "max_iterations")
        return 25 if v is None else int(v)

    @property
    def agent_max_output_tokens(self) -> int:
        v = self.dig("agent", "max_output_tokens")
        return 1024 if v is None else int(v)

    @property
    def agent_max_turn_tokens(self) -> int:
        v = self.dig("agent", "max_turn_tokens")
        return 60_000 if v is None else int(v)

    @property
    def agent_compaction_threshold(self) -> float:
        v = self.dig("agent", "compaction_threshold")
        return 0.85 if v is None else float(v)

    # ---------- low-level helpers -------------------------------------------

    def dig(self, *keys: str) -> Any:
        node: Any = self._settings
        for key in keys:
            node = node.get(key) if isinstance(node, dict) else None
        return node

    def __str__(self) -> str:
        return f"#<Boukensha::Config dir={self._dir} provider={self.provider_type} model={self.model}>"

    __repr__ = __str__

    def _resolve_dir(self) -> Path:
        env_dir = os.environ.get("BOUKENSHA_DIR")
        if env_dir:
            return Path(env_dir).expanduser().resolve()

        return DEFAULT_DIR.expanduser().resolve()

    def _load_env(self) -> None:
        env_file = self._dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)

    def _load_settings(self) -> dict[str, Any]:
        settings_file = self._dir / "settings.yaml"
        if settings_file.exists():
            return yaml.safe_load(settings_file.read_text()) or {}
        return {}

    # Resolves the system prompt. When the player task opts into a prompt
    # override (tasks.player.prompt_override.system: true), the task-scoped
    # file prompts/player/system.md wins; otherwise (and as a fallback) the
    # flat prompts/system.md is used. Returns None when neither exists.
    def _load_system_prompt(self) -> str | None:
        if self.dig("tasks", "player", "prompt_override", "system") is True:
            task_file = self._dir / "prompts" / "player" / "system.md"
            if task_file.exists():
                return task_file.read_text().strip()

        system_file = self._dir / "prompts" / "system.md"
        return system_file.read_text().strip() if system_file.exists() else None
