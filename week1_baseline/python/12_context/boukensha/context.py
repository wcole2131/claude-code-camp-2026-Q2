from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from .message import Message

if TYPE_CHECKING:
    from .tool import Tool


class Context:
    def __init__(
        self,
        *,
        system: str | None = None,
        context_window: int = 200_000,
        working_dir: str | Path | Literal[False] | None = None,
        compaction_threshold: float = 0.85,
    ) -> None:
        self.system = system
        self.context_window = context_window
        self.working_dir = Path(working_dir).expanduser().resolve() if working_dir else None
        self.compaction_threshold = compaction_threshold
        self.messages: list[Message] = []
        self.tools: dict[str, Tool] = {}
        self.current_tokens = 0
        self.turn_tokens = 0

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def add_message(
        self, role: str, content: str | list[dict[str, Any]], *, tool_use_id: str | None = None
    ) -> None:
        self.messages.append(Message(role, content, tool_use_id))

    def update_tokens(self, n: int) -> None:
        self.current_tokens = int(n)

    def reset_turn_tokens(self) -> None:
        self.turn_tokens = 0

    def add_turn_tokens(self, input_tokens: int, output_tokens: int) -> None:
        self.turn_tokens += int(input_tokens) + int(output_tokens)

    @property
    def usage_fraction(self) -> float:
        return self.current_tokens / self.context_window if self.context_window > 0 else 0.0

    @property
    def usage_pct(self) -> int:
        return round(self.usage_fraction * 100)

    def needs_compaction(self, threshold: float | None = None) -> bool:
        threshold = self.compaction_threshold if threshold is None else threshold
        return self.usage_fraction >= threshold

    # target_fraction is accepted for parity with Ruby's compact_messages! but, like the
    # Ruby original, is never actually used in the drop-count calculation below.
    def compact_messages(self, target_fraction: float = 0.60) -> int:
        drop_count = min(math.ceil(len(self.messages) * 0.40), len(self.messages) - 2)
        drop_count = max(drop_count, 0)
        self.messages = self.messages[drop_count:]
        self.current_tokens = 0
        return drop_count

    def clear_messages(self) -> None:
        self.messages = []
        self.current_tokens = 0

    @property
    def tool_count(self) -> int:
        return len(self.tools)

    @property
    def turn_count(self) -> int:
        return len(self.messages)

    def __str__(self) -> str:
        return (
            f"#<Context turns={self.turn_count} tools={self.tool_count} "
            f"window={self.context_window} current={self.current_tokens}>"
        )

    __repr__ = __str__
