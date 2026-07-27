from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .errors import UnknownToolError
from .tool import Tool

if TYPE_CHECKING:
    from collections.abc import Callable

    from .context import Context


class Registry:
    def __init__(self, context: Context) -> None:
        self.context = context

    def tool(
        self,
        name: str,
        *,
        description: str,
        parameters: dict[str, Any] | None = None,
        block: Callable[..., Any],
    ) -> Tool:
        tool = Tool(name, description, parameters or {}, block)
        self.context.register_tool(tool)
        return tool

    def dispatch(self, name: str, args: dict[str, Any] | None = None) -> Any:
        tool = self.context.tools.get(name)
        if tool is None:
            raise UnknownToolError(f"No tool registered as '{name}'")
        return tool.block(**(args or {}))
