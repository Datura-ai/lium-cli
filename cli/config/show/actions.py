"""Actions for config show command."""

from cli.settings import config



class ActionResult:
    """Result of an action execution."""

    def __init__(self, ok: bool, data: dict | None = None, error: str | None = None):
        self.ok = ok
        self.data = data or {}
        self.error = error


class ShowConfigAction:
    """Show all config."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute config show."""
        show_all: bool = ctx["show_all"]

        config_data = config.get_all()
        config_path = config.get_config_path()

        return ActionResult(
            ok=True,
            data={
                "config_data": config_data,
                "config_path": config_path,
                "show_all": show_all
            }
        )
