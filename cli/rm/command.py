"""Remove (rm) command implementation."""

from typing import Optional
import click

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors
from . import validation, parsing
from .actions import RemovePodsAction, ScheduleRemovalAction


@click.command("rm")
@click.argument("targets", required=False)
@click.option("--all", "-a", is_flag=True, help="Remove all active pods")
@click.option("--in", "in_duration", help="Schedule removal after duration")
@click.option("--at", "at_time", help="Schedule removal at time")
@handle_errors
def rm_command(targets: Optional[str], all: bool, in_duration: Optional[str], at_time: Optional[str]):
    """Remove (terminate) GPU pods."""

    # Validate
    valid, error = validation.validate(targets, all, in_duration, at_time)
    if not valid:
        ui.error(error)
        return

    # Load data
    lium = Lium()
    all_pods = ui.load("Loading pods", lambda: lium.ps())

    if not all_pods:
        ui.warning("No active pods")
        return

    # Parse
    parsed, error = parsing.parse(targets, all, all_pods, in_duration, at_time)
    if error:
        ui.error(error)
        return

    selected_pods = parsed.get("selected_pods")
    termination_time = parsed.get("termination_time")

    # Execute
    ctx = {"pods": selected_pods, "lium": lium}

    if termination_time:
        ctx["termination_time"] = termination_time.isoformat()
        action = ScheduleRemovalAction()
    else:
        action = RemovePodsAction()

    result = action.execute(ctx)

    # Only error if anything failed
    if not result.ok:
        failed_huids = result.data.get("failed_huids", [])
        ui.error(f"Failed to remove pods: {', '.join(failed_huids)}")
