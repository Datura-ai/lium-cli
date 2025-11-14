"""Actions for config unset command."""

from config import config



class ActionResult:
    """Result of an action execution."""

    def __init__(self, ok: bool, data: dict | None = None, error: str | None = None):
        self.ok = ok
        self.data = data or {}
        self.error = error


class UnsetConfigAction:
    """Unset config value."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute config unset."""
        key: str = ctx["key"]

        removed = config.unset(key)

        if not removed:
            return ActionResult(ok=False, error=f"Key '{key}' not found")

        return ActionResult(ok=True)
