from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .backends.base import Base
    from .context import Context


class PromptBuilder:
    def __init__(self, context: Context, backend: Base) -> None:
        self.context = context
        self.backend = backend

    def to_messages(self) -> list[dict[str, Any]]:
        return self.backend.to_messages(self.context.messages)

    def to_tools(self) -> list[dict[str, Any]]:
        return self.backend.to_tools(self.context.tools)

    def to_api_payload(
        self, *, max_output_tokens: int = 1024, tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        return self.backend.to_payload(self.context, max_output_tokens=max_output_tokens, tools=tools)

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return self.backend.parse_response(response)

    @property
    def headers(self) -> dict[str, str]:
        return self.backend.headers

    @property
    def url(self) -> str:
        return self.backend.url
