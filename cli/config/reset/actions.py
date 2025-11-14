"""Actions for config reset command."""

from cli.settings import config



class ActionResult:
    """Result of an action execution."""

    def __init__(self, ok: bool, data: dict | None = None, error: str | None = None):
        self.ok = ok
        self.data = data or {}
        self.error = error


class ResetConfigAction:
    """Reset config."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute config reset."""
        config_file = config.get_config_path()

        if not config_file.exists():
            return ActionResult(ok=False, error="Configuration already empty")

        config_file.unlink()

        return ActionResult(ok=True)
