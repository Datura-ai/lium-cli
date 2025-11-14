"""Actions for bk set command."""

from cli.lium_sdk import Lium


class ActionResult:
    """Result of an action execution."""

    def __init__(self, ok: bool, data: dict | None = None, error: str | None = None):
        self.ok = ok
        self.data = data or {}
        self.error = error


class SetBackupAction:
    """Set backup configuration."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute backup set."""
        lium: Lium = ctx["lium"]
        pod_name: str = ctx["pod_name"]
        path: str = ctx["path"]
        frequency_hours: int = ctx["frequency_hours"]
        retention_days: int = ctx["retention_days"]

        try:
            # Check if backup already exists
            existing_config = lium.backup_config(pod=pod_name)

            if existing_config:
                lium.backup_delete(existing_config.id)

            # Create new backup config
            lium.backup_create(
                pod=pod_name,
                path=path,
                frequency_hours=frequency_hours,
                retention_days=retention_days
            )

            return ActionResult(ok=True)
        except Exception as e:
            return ActionResult(ok=False, error=str(e))
