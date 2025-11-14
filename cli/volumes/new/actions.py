"""Volumes new actions."""

from dataclasses import dataclass


@dataclass
class ActionResult:
    ok: bool
    data: dict
    error: str = ""


class CreateVolumeAction:

    def execute(self, ctx: dict) -> ActionResult:
        lium = ctx["lium"]
        name = ctx["name"]
        description = ctx.get("description", "")

        try:
            new_volume = lium.volume_create(name=name, description=description)
            return ActionResult(
                ok=True,
                data={"volume": new_volume}
            )
        except Exception as e:
            return ActionResult(ok=False, data={}, error=str(e))
