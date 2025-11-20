from lium.cli.actions import ActionResult
from lium.cli.settings import config


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
