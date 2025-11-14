"""Actions for config reset command."""

from cli.actions import ActionResult
from cli.settings import config


class ResetConfigAction:
    """Reset config."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute config reset."""
        config_file = config.get_config_path()

        if not config_file.exists():
            return ActionResult(ok=False, error="Configuration already empty")

        config_file.unlink()

        return ActionResult(ok=True)
