"""Reboot command implementation."""

from typing import Optional
import click

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors
from . import validation, parsing
from .actions import RebootPodsAction


@click.command("reboot")
@click.argument("targets", required=False)
@click.option("--all", "-a", is_flag=True, help="Reboot all active pods")
@click.option("--volume-id", help="Volume ID to attach when rebooting")
@handle_errors
def reboot_command(targets: Optional[str], all: bool, volume_id: Optional[str]):
    """Reboot GPU pods."""

    # Validate
    valid, error = validation.validate(targets, all)
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
    parsed, error = parsing.parse(targets, all, all_pods)
    if error:
        ui.error(error)
        return

    selected_pods = parsed.get("selected_pods")

    # Execute
    payload_volume_id = volume_id.strip() if volume_id else None
    ctx = {"pods": selected_pods, "lium": lium, "volume_id": payload_volume_id}

    action = RebootPodsAction()
    result = action.execute(ctx)

    # Only error if anything failed
    if not result.ok:
        failed_huids = result.data.get("failed_huids", [])
        ui.error(f"Failed to reboot pods: {', '.join(failed_huids)}")
