from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    block: Callable[..., str]

    def __str__(self) -> str:
        return f"#<Tool name={self.name} description={self.description[:41]} params={list(self.parameters.keys())}>"

    __repr__ = __str__
