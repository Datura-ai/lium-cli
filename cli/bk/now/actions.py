"""Actions for bk now command."""

from cli.core import ActionResult
from cli.lium_sdk import Lium


class TriggerBackupAction:
    """Trigger immediate backup."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute backup trigger."""
        lium: Lium = ctx["lium"]
        pod_name: str = ctx["pod_name"]
        name: str = ctx["name"]
        description: str = ctx["description"]

        try:
            # Check if backup config exists
            backup_config = lium.backup_config(pod=pod_name)

            if not backup_config:
                return ActionResult(ok=False, error="No backup configuration found")

            # Trigger backup
            lium.backup_now(
                pod=pod_name,
                name=name,
                description=description
            )

            return ActionResult(ok=True)
        except Exception as e:
            return ActionResult(ok=False, error=str(e))
