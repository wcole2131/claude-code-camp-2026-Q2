from __future__ import annotations

import json
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Deferred, whole-module import (not `from . import get_config, is_debug`) is required here:
# boukensha/__init__.py does `from .logger import Logger`, so at the moment this file is first
# loaded, `boukensha/__init__.py` hasn't yet defined `get_config`/`is_debug` in its own namespace
# (isort groups all `from .module import Name` imports before any function definitions). Importing
# the whole module and reading attributes off it lazily, inside method bodies, works because those
# attributes only need to exist by the time this code actually *runs* — long after both modules
# have finished importing — not at import time.
import boukensha

if TYPE_CHECKING:
    from .message import Message
    from .tool import Tool

DEFAULT_SESSION_DIR = "sessions"


class Logger:
    def __init__(
        self,
        *,
        session_id: str | None = None,
        dir: str | Path | None = None,
        log: str | Path | None = None,
        snapshot: dict[str, Any] | None = None,
    ) -> None:
        snapshot = snapshot or {}
        self.session_id = session_id or self._generate_session_id()
        self.path = Path(log) if log else Path(dir or self._default_dir()) / f"{self.session_id}.jsonl"

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._log_io = self.path.open("a")
        self._write_log({"phase": "session_start", **snapshot})

    def iteration(self, *, n: int, max: int) -> None:
        self._write_log({"phase": "iteration", "n": n, "max": max})

    def limit_reached(self, *, kind: str, n: int, max: int) -> None:
        self._write_log({"phase": "limit_reached", "kind": kind, "n": n, "max": max})

    def turn_end(self, *, reason: str, iterations: int, tokens: Any = None) -> None:
        self._write_log({"phase": "turn_end", "reason": reason, "iterations": iterations, "tokens": tokens})

    def prompt(self, *, messages: list[Message], tools: dict[str, Tool]) -> None:
        self._write_log(
            {
                "phase": "prompt",
                "message_count": len(messages),
                "messages": [self._serialize_message(m) for m in messages],
                "tool_count": len(tools),
                "tools": list(tools.keys()),
            }
        )

    def tool_call(self, *, name: str, args: Any) -> None:
        self._write_log({"phase": "tool_call", "name": name, "args": args})

    def tool_result(self, *, name: str, result: Any, ok: bool = True, error: str | None = None) -> None:
        self._write_log({"phase": "tool_result", "name": name, "result": str(result), "ok": ok, "error": error})

    def response(
        self,
        *,
        text: str,
        usage: Any = None,
        stop_reason: str | None = None,
        task: Any = None,
        backend: Any = None,
    ) -> None:
        self._write_log(
            {
                "phase": "response",
                "text": str(text).strip(),
                "usage": usage,
                "stop_reason": stop_reason,
                **self._execution_metadata(task=task, backend=backend, usage=usage),
            }
        )

    def raw(self, *, data: Any) -> None:
        if not boukensha.is_debug():
            return
        self._write_log({"phase": "raw", "data": data})

    def close(self) -> None:
        self._log_io.close()

    def _default_dir(self) -> Path:
        return Path(boukensha.get_config().dir) / DEFAULT_SESSION_DIR

    def _write_log(self, event: dict[str, Any]) -> None:
        line = {**event, "session_id": self.session_id, "at": datetime.now().astimezone().isoformat(timespec="seconds")}
        self._log_io.write(json.dumps(line) + "\n")
        self._log_io.flush()

    @staticmethod
    def _generate_session_id() -> str:
        return f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(4)}"

    @staticmethod
    def _serialize_message(msg: Message) -> dict[str, Any]:
        return {"role": msg.role, "content": msg.content}

    def _execution_metadata(self, *, task: Any, backend: Any, usage: Any) -> dict[str, Any]:
        if not (task or backend or usage):
            return {}

        tokens = self._usage_tokens(usage)
        metadata = {
            "task": self._task_name(task),
            "provider": self._provider_name(backend),
            "model": getattr(backend, "model", None),
            "usage_unit": getattr(backend, "usage_unit", None),
            "usage_level": getattr(backend, "usage_level", None),
            "input_tokens": tokens["input"],
            "output_tokens": tokens["output"],
            "cost_usd": self._estimate_cost(backend, tokens),
        }
        return {k: v for k, v in metadata.items() if v is not None}

    @staticmethod
    def _task_name(task: Any) -> str | None:
        if task is None:
            return None
        return task.task_name() if hasattr(task, "task_name") else str(task)

    @staticmethod
    def _provider_name(backend: Any) -> str | None:
        if backend is None:
            return None
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", type(backend).__name__).lower()

    @classmethod
    def _usage_tokens(cls, usage: Any) -> dict[str, int | None]:
        usage = usage or {}
        return {
            "input": cls._first_integer(usage, "input_tokens", "prompt_tokens", "promptTokenCount", "prompt_eval_count"),
            "output": cls._first_integer(usage, "output_tokens", "completion_tokens", "candidatesTokenCount", "eval_count"),
        }

    @staticmethod
    def _first_integer(usage: dict[str, Any], *keys: str) -> int | None:
        for key in keys:
            value = usage.get(key)
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None
        return None

    @staticmethod
    def _estimate_cost(backend: Any, tokens: dict[str, int | None]) -> float | None:
        if backend is None or not hasattr(backend, "estimate_cost"):
            return None
        if tokens["input"] is None or tokens["output"] is None:
            return None
        return backend.estimate_cost(input_tokens=tokens["input"], output_tokens=tokens["output"])
