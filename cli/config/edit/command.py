"""Config edit command implementation."""

import click

from cli import ui
from cli.utils import handle_errors
from .actions import EditConfigAction


@click.command(name="edit")
@handle_errors
def config_edit_command():
    """Open configuration file in default editor."""

    # Execute
    ctx = {}

    action = EditConfigAction()
    result = action.execute(ctx)

    if not result.ok:
        ui.error(result.error)
