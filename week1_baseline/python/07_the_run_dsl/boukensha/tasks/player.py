from __future__ import annotations

from .base import Base


class Player(Base):
    @classmethod
    def task_name(cls) -> str:
        return "player"
