from dataclasses import dataclass


@dataclass
class ActionResult:
    ok: bool
    data: dict
    error: str = ""


__all__ = ["ActionResult"]
