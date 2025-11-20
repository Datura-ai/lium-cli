from lium.cli.actions import ActionResult
from lium.sdk import Lium, PodInfo


class TriggerBackupAction:
    """Trigger immediate backup."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute backup trigger."""
        lium: Lium = ctx["lium"]
        pod: PodInfo = ctx["pod"]
        name: str = ctx["name"]
        description: str = ctx["description"]

        try:
            # Check if backup config exists
            backup_config = lium.backup_config(pod)

            if not backup_config:
                return ActionResult(ok=False, data={}, error="No backup configuration found")

            # Trigger backup
            lium.backup_now(
                pod=pod,
                name=name,
                description=description
            )

            return ActionResult(ok=True, data={})
        except Exception as e:
            return ActionResult(ok=False, data={}, error=str(e))
