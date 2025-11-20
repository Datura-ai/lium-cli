"""Config path command implementation."""

import click

from lium.cli import ui
from lium.cli.utils import handle_errors
from .actions import PathConfigAction


@click.command(name="path")
@handle_errors
def config_path_command():
    """Show the path to the configuration file."""

    # Execute
    ctx = {}

    action = PathConfigAction()
    result = action.execute(ctx)

    path = result.data.get("path")
    ui.info(path)
