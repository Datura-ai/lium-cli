from lium.cli.actions import ActionResult
from lium.cli.settings import config


class UnsetConfigAction:
    """Unset config value."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute config unset."""
        key: str = ctx["key"]

        removed = config.unset(key)

        if not removed:
            return ActionResult(ok=False, data={}, error=f"Key '{key}' not found")

        return ActionResult(ok=True, data={})
