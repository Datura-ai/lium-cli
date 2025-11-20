from lium.cli.actions import ActionResult
from lium.cli.settings import config


class PathConfigAction:
    """Get config path."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute config path."""
        config_path = config.get_config_path()

        return ActionResult(ok=True, data={"path": str(config_path)})
