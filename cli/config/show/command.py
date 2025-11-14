"""Config show command implementation."""

import click

from cli import ui
from cli.utils import handle_errors
from .actions import ShowConfigAction
from . import display


@click.command(name="show")
@click.option("--all", is_flag=True, help="Show all sections including internal data.")
@handle_errors
def config_show_command(all: bool):
    """Show the entire configuration."""

    # Execute
    ctx = {"show_all": all}

    action = ShowConfigAction()
    result = action.execute(ctx)

    config_data = result.data.get("config_data")
    config_path = result.data.get("config_path")
    show_all = result.data.get("show_all")

    output = display.format_config(config_data, str(config_path), show_all)
    ui.info(output)
