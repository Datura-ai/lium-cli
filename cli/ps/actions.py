"""PS command actions."""

from typing import List

from cli.actions import ActionResult


class GetPodsAction:
    """Get active pods."""

    def execute(self, ctx: dict) -> ActionResult:
        """Get pods list.

        Context:
            lium: Lium SDK instance
        """
        lium = ctx["lium"]

        try:
            pods = lium.ps()
            return ActionResult(
                ok=True,
                data={"pods": pods}
            )
        except Exception as e:
            return ActionResult(ok=False, data={}, error=str(e))
