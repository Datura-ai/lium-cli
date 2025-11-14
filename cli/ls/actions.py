"""List command actions."""

from dataclasses import dataclass
from typing import List


@dataclass
class ActionResult:
    """Result from an action."""
    ok: bool
    data: dict
    error: str = ""


class GetExecutorsAction:
    """Get available executors."""

    def execute(self, ctx: dict) -> ActionResult:
        """Get executors list.

        Context:
            lium: Lium SDK instance
            gpu_type: Optional[str] - GPU type filter
        """
        lium = ctx["lium"]
        gpu_type = ctx.get("gpu_type")

        try:
            executors = lium.ls(gpu_type=gpu_type)
            return ActionResult(
                ok=True,
                data={"executors": executors}
            )
        except Exception as e:
            return ActionResult(ok=False, data={}, error=str(e))
