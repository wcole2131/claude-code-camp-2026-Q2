from __future__ import annotations

from typing import Any, ClassVar

from ..errors import UnsupportedModelError


class Base:
    """Common base for all provider backends.

    Normalized response contract
    -----------------------------
    Every backend's parse_response returns::

        {"stop_reason": "tool_use" | "end_turn",
         "content": [<block>, <block>, ...]}

    where each block is one of::

        {"type": "reasoning",
         "text": "<human-readable reasoning, may be empty>",
         "signature": "<opaque provider token, optional>",  # round-trip only
         "redacted": True | False}                          # optional

        {"type": "text", "text": "..."}

        {"type": "tool_use", "id": ..., "name": ..., "input": {...}}

    Reasoning blocks come FIRST in content, before text and tool_use (matching
    Anthropic's native ordering). `text` is what the viewer renders and may be
    empty (redacted/omitted reasoning). `signature`/`redacted` are opaque
    carry-through for providers that require the block echoed back unchanged
    (Anthropic thinking signatures, Gemini thoughtSignature) -- consumers never
    interpret them. Backends that don't accept reasoning back in a request drop
    these blocks when rebuilding assistant turns.
    """

    MODELS: ClassVar[dict[str, dict[str, Any]]]

    @classmethod
    def models(cls) -> dict[str, dict[str, Any]]:
        try:
            return cls.MODELS
        except AttributeError:
            raise NotImplementedError(f"{cls.__name__} must define MODELS") from None

    @classmethod
    def _model_info_for(cls, model: str) -> dict[str, Any] | None:
        return cls.models().get(model)

    @classmethod
    def validate_model(cls, model: str) -> str:
        if cls._model_info_for(model) is not None:
            return model

        supported = ", ".join(sorted(cls.models()))
        raise UnsupportedModelError(f"{cls.__name__} does not support model {model!r}. Supported models: {supported}")

    @property
    def model_info(self) -> dict[str, Any]:
        return self._model_info

    @property
    def context_window(self) -> int:
        return self._model_info["context_window"]

    @property
    def input_token_cost_per_million(self) -> float | None:
        return self._model_info["cost_per_million"]["input"]

    @property
    def output_token_cost_per_million(self) -> float | None:
        return self._model_info["cost_per_million"]["output"]

    @property
    def usage_unit(self) -> str:
        return self._model_info["usage_unit"]

    @property
    def usage_level(self) -> str | None:
        return self._model_info.get("usage_level")

    def estimate_cost(self, *, input_tokens: int, output_tokens: int) -> float | None:
        input_cost = self.input_token_cost_per_million
        output_cost = self.output_token_cost_per_million
        if input_cost is None or output_cost is None:
            return None

        return ((input_tokens * input_cost) + (output_tokens * output_cost)) / 1_000_000.0

    def _configure_model(self, model: str) -> None:
        self.model = self.validate_model(model)
        model_info = self._model_info_for(self.model)
        assert model_info is not None, "validate_model already confirmed this model exists"
        self._model_info: dict[str, Any] = model_info

    def to_messages(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        raise NotImplementedError(f"{type(self).__name__} must define to_messages")

    def to_tools(self, tools: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError(f"{type(self).__name__} must define to_tools")

    def to_payload(
        self, context: Any, *, max_output_tokens: int = 1024, tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__} must define to_payload")

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__} must define parse_response")

    @property
    def headers(self) -> dict[str, str]:
        raise NotImplementedError(f"{type(self).__name__} must define headers")

    @property
    def url(self) -> str:
        raise NotImplementedError(f"{type(self).__name__} must define url")
