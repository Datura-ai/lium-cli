"""Templates command actions."""

from typing import Optional

from cli.actions import ActionResult


class GetTemplatesAction:

    def execute(self, ctx: dict) -> ActionResult:
        lium = ctx["lium"]
        search = ctx.get("search")

        try:
            templates = lium.templates(search)
            return ActionResult(
                ok=True,
                data={"templates": templates}
            )
        except Exception as e:
            return ActionResult(ok=False, data={}, error=str(e))
