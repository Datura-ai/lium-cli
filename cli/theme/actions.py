"""Theme command actions."""

from cli.core import ActionResult


class GetThemeAction:

    def execute(self, ctx: dict) -> ActionResult:
        console = ctx["console"]

        try:
            current = console.get_current_theme_name()
            resolved = console.get_resolved_theme_name()

            return ActionResult(
                ok=True,
                data={
                    "current": current,
                    "resolved": resolved
                }
            )
        except Exception as e:
            return ActionResult(ok=False, data={}, error=str(e))


class SwitchThemeAction:

    def execute(self, ctx: dict) -> ActionResult:
        console = ctx["console"]
        theme_name = ctx["theme_name"]

        try:
            old_theme = console.get_current_theme_name()
            console.switch_theme(theme_name)

            resolved = None
            if theme_name == "auto":
                resolved = console.get_resolved_theme_name()

            return ActionResult(
                ok=True,
                data={
                    "old_theme": old_theme,
                    "new_theme": theme_name,
                    "resolved": resolved
                }
            )
        except Exception as e:
            return ActionResult(ok=False, data={}, error=str(e))
