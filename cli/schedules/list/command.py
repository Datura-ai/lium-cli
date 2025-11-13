"""Schedules list command implementation."""

import click

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors
from .. import display


@click.command("list")
@handle_errors
def schedules_list_command():
    """List all pods with scheduled terminations."""

    lium = Lium()
    all_pods = ui.load("Loading scheduled terminations", lambda: lium.ps())

    # Build table
    table, header, tip = display.build_schedules_table(all_pods)

    if not table:
        return

    # Display
    ui.info(header)
    ui.print(table)
    ui.print("")
    ui.info(tip)
