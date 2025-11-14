"""Config reset command implementation."""

import click

from cli import ui
from cli.utils import handle_errors
from . import validation
from .actions import ResetConfigAction


@click.command(name="reset")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt.")
@handle_errors
def config_reset_command(confirm: bool):
    """Reset configuration to defaults."""

    # Validate
    valid, error = validation.validate(confirm)
    if not valid:
        ui.info(error)
        return

    # Execute
    ctx = {}

    action = ResetConfigAction()
    result = action.execute(ctx)

    if not result.ok:
        ui.info(result.error)
        return

    ui.success("Configuration reset to defaults")
