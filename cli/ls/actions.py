"""List command actions."""

from typing import List

from cli.actions import ActionResult


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
