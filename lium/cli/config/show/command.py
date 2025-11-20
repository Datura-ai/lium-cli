"""Config show command implementation."""

import click

from lium.cli import ui
from lium.cli.utils import handle_errors
from .actions import ShowConfigAction


@click.command(name="show")
@handle_errors
def config_show_command():
    """Show the entire configuration."""

    # Execute
    ctx = {}

    action = ShowConfigAction()
    result = action.execute(ctx)

    config_path = result.data.get("config_path")
    content = result.data.get("content")

    ui.dim(f"# {config_path}")
    if content:
        ui.print(content, markup=False, highlight=False)
