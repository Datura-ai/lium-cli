"""Actions for config show command."""

from cli.actions import ActionResult
from cli.settings import config


class ShowConfigAction:
    """Show all config."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute config show."""
        config_path = config.get_config_path()

        if not config_path.exists():
            return ActionResult(ok=True, data={"config_path": config_path, "content": ""})

        content = config_path.read_text()

        return ActionResult(
            ok=True,
            data={
                "config_path": config_path,
                "content": content
            }
        )
