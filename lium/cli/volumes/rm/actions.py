from lium.cli.actions import ActionResult


class RemoveVolumesAction:

    def execute(self, ctx: dict) -> ActionResult:
        lium = ctx["lium"]
        volumes_to_remove = ctx["volumes_to_remove"]
        ui = ctx.get("ui")

        failed_huids = []

        for idx, volume_data in volumes_to_remove:
            volume_id = volume_data['id']
            volume_huid = volume_data['huid']

            try:
                lium.volume_delete(volume_id)
            except Exception as e:
                failed_huids.append(volume_huid)
                if ui:
                    ui.debug(f"Failed to remove {volume_huid}: {e}")

        return ActionResult(
            ok=len(failed_huids) == 0,
            data={"failed_huids": failed_huids}
        )
