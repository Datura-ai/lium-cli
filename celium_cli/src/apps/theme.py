import typer
from typing import TYPE_CHECKING, List
from celium_cli.src.apps import BaseApp
from celium_cli.src.styles import style_manager, ThemeName, THEMES

if TYPE_CHECKING:
    from celium_cli.src.cli_manager import CLIManager

class ThemeApp(BaseApp):
    def run(self):
        self.app.command("set")(self.set_theme)
        self.app.command("list")(self.list_themes)
        self.app.command("current")(self.show_current_theme)

    def set_theme(self, theme_name: str = typer.Argument(..., help=f"Name of the theme to set. Choices: {', '.join(THEMES.keys())}")):
        """
        Sets the CLI display theme.
        """
        try:
            # Cast to ThemeName if it's a valid choice, otherwise style_manager will raise ValueError
            valid_theme_name = theme_name.lower()
            if valid_theme_name not in style_manager.get_available_themes():
                style_manager.console.print(f"[error]Error: Invalid theme name '{theme_name}'.[/error]")
                self.list_themes()
                raise typer.Exit(code=1)
            
            style_manager.switch_theme(valid_theme_name) # type: ignore
            # The global console in styles.py is now updated, and style_manager.console is also updated.
            # We should use the console imported from styles module for output.
            style_manager.console.print(f"[success]Successfully switched theme to '{valid_theme_name}'.[/success]")
            style_manager.console.print("Please restart the CLI for the theme to fully apply to all output if you see inconsistencies.")
        except ValueError as e:
            style_manager.console.print(f"[error]Error: {e}[/error]")
            self.list_themes()

    def list_themes(self):
        """Lists all available themes."""
        style_manager.console.print("[title]Available Themes:[/title]")
        available_themes = style_manager.get_available_themes()
        for theme in available_themes:
            style_manager.console.print(f"  - {theme}")
        style_manager.console.print(f"\nCurrent theme: [key]{style_manager._current_theme_name}[/key]")

    def show_current_theme(self):
        """Shows the currently active theme."""
        style_manager.console.print(f"Current theme: [key]{style_manager._current_theme_name}[/key]") 