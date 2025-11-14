"""Actions for bk restore command."""

from cli.actions import ActionResult
from cli.lium_sdk import Lium


class RestoreBackupAction:
    """Restore backup."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute backup restore."""
        lium: Lium = ctx["lium"]
        pod_name: str = ctx["pod_name"]
        backup_id: str = ctx["backup_id"]
        restore_path: str = ctx["restore_path"]

        try:
            lium.restore(
                pod=pod_name,
                backup_id=backup_id,
                restore_path=restore_path
            )

            return ActionResult(ok=True)
        except Exception as e:
            return ActionResult(ok=False, error=str(e))
