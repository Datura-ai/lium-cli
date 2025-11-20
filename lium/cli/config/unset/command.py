"""Config unset command implementation."""

import click

from lium.cli import ui
from lium.cli.utils import handle_errors
from .actions import UnsetConfigAction


@click.command(name="unset")
@click.argument("key")
@handle_errors
def config_unset_command(key: str):
    """Remove a configuration value."""

    # Execute
    ctx = {"key": key}

    action = UnsetConfigAction()
    result = action.execute(ctx)

    if result.error:
        ui.warning(result.error)
