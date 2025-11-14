"""Actions for config path command."""

from config import config



class ActionResult:
    """Result of an action execution."""

    def __init__(self, ok: bool, data: dict | None = None, error: str | None = None):
        self.ok = ok
        self.data = data or {}
        self.error = error


class PathConfigAction:
    """Get config path."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute config path."""
        config_path = config.get_config_path()

        return ActionResult(ok=True, data={"path": str(config_path)})
