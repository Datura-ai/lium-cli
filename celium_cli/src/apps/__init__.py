from typing import TYPE_CHECKING
import typer

from celium_cli.src.const import EPILOG

if TYPE_CHECKING:
    from celium_cli.src.cli_manager import CLIManager


class BaseApp:
    app: typer.Typer

    def __init__(self, cli_manager: "CLIManager"):
        self.cli_manager = cli_manager
        self.app = typer.Typer(epilog=EPILOG)
        self.run()

    def run(self):
        pass
