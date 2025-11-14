"""Actions for config get command."""

from cli.config import config


class ActionResult:
    """Result of an action execution."""

    def __init__(self, ok: bool, data: dict | None = None, error: str | None = None):
        self.ok = ok
        self.data = data or {}
        self.error = error


class GetConfigAction:
    """Get config value."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute config get."""
        key: str = ctx["key"]

        value = config.get(key)

        if value is None:
            return ActionResult(ok=False, error=f"Key '{key}' not found")

        return ActionResult(ok=True, data={"value": value})
