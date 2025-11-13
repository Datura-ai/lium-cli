from dataclasses import dataclass
from typing import Any


@dataclass
class ActionResult:
    ok: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class Action:
    name: str = "action"
    fatal: bool = True

    def run(self, ctx: dict[str, Any]) -> ActionResult:
        raise NotImplementedError


__all__ = ["Action", "ActionResult"]
