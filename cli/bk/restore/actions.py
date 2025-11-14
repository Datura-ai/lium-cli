"""Actions for bk restore command."""

from cli.lium_sdk import Lium


class ActionResult:
    """Result of an action execution."""

    def __init__(self, ok: bool, data: dict | None = None, error: str | None = None):
        self.ok = ok
        self.data = data or {}
        self.error = error


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
