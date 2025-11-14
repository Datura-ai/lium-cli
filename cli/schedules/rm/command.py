"""Schedules rm command implementation."""

import click

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors
from . import validation, parsing
from .actions import CancelSchedulesAction


@click.command("rm")
@click.argument("indices")
@handle_errors
def schedules_rm_command(indices: str):
    """Cancel scheduled terminations by index."""

    # Validate
    valid, error = validation.validate(indices)
    if not valid:
        ui.error(error)
        return

    # Load data
    lium = Lium()
    all_pods = ui.load("Loading scheduled terminations", lambda: lium.ps())

    if not all_pods:
        ui.warning("No active pods")
        return

    # Parse
    parsed, error = parsing.parse(indices, all_pods)
    if error:
        ui.error(error)
        return

    pods_to_cancel = parsed.get("pods_to_cancel")

    # Execute
    ctx = {"pods": pods_to_cancel, "lium": lium}

    action = CancelSchedulesAction()
    result = action.execute(ctx)

    # Only error if anything failed
    if not result.ok:
        failed_huids = result.data.get("failed_huids", [])
        ui.error(f"Failed to cancel schedules: {', '.join(failed_huids)}")
