"""Actions for bk rm command."""

from cli.core import ActionResult
from cli.lium_sdk import Lium


class RemoveBackupAction:
    """Remove backup configuration."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute backup removal."""
        lium: Lium = ctx["lium"]
        pod_name: str = ctx["pod_name"]

        try:
            backup_config = lium.backup_config(pod=pod_name)

            if not backup_config:
                return ActionResult(ok=False, error="No backup configuration found")

            lium.backup_delete(backup_config.id)

            return ActionResult(ok=True)
        except Exception as e:
            return ActionResult(ok=False, error=str(e))
