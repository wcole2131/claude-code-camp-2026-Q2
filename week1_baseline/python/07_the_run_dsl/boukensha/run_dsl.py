from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from .registry import Registry
    from .tool import Tool


# Passed to a boukensha.run `configure` callback. Exposes only `tool`, keeping
# the DSL surface intentionally small.
class RunDSL:
    def __init__(self, registry: Registry) -> None:
        self._registry = registry

    def tool(
        self,
        name: str,
        *,
        description: str,
        parameters: dict[str, Any] | None = None,
        block: Callable[..., Any],
    ) -> Tool:
        return self._registry.tool(name, description=description, parameters=parameters, block=block)
