"""Actions for config get command."""

from cli.actions import ActionResult
from cli.settings import config


class GetConfigAction:
    """Get config value."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute config get."""
        key: str = ctx["key"]

        value = config.get(key)

        if value is None:
            return ActionResult(ok=False, error=f"Key '{key}' not found")

        return ActionResult(ok=True, data={"value": value})
