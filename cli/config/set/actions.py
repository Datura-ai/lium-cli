"""Actions for config set command."""

from config import config

class ActionResult:
    """Result of an action execution."""

    def __init__(self, ok: bool, data: dict | None = None, error: str | None = None):
        self.ok = ok
        self.data = data or {}
        self.error = error


class SetConfigAction:
    """Set config value."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute config set."""
        key: str = ctx["key"]
        value: str = ctx["value"]

        config.set(key, value)

        new_value = config.get(key)

        if new_value is None:
            return ActionResult(ok=False, error=f"Failed to set {key}")

        return ActionResult(ok=True, data={"value": new_value})
