"""Volumes list actions."""

from cli.core import ActionResult


class GetVolumesAction:

    def execute(self, ctx: dict) -> ActionResult:
        lium = ctx["lium"]

        try:
            volumes = lium.volumes()
            return ActionResult(
                ok=True,
                data={"volumes": volumes}
            )
        except Exception as e:
            return ActionResult(ok=False, data={}, error=str(e))
