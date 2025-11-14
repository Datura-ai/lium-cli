"""Pods (ps) command implementation."""

from typing import Optional
import click

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors, ensure_config
from . import display
from .actions import GetPodsAction


@click.command("ps")
@click.argument("pod_id", required=False)
@handle_errors
def ps_command(pod_id: Optional[str]):
    """List active GPU pods."""

    ensure_config()

    # Load data
    lium = Lium()
    ctx = {"lium": lium}

    action = GetPodsAction()
    result = ui.load("Loading pods", lambda: action.execute(ctx))

    if not result.ok:
        ui.error(result.error)
        return

    pods = result.data["pods"]

    # Check if empty
    if not pods:
        ui.warning("No active pods")
        return

    # Filter by pod_id if provided
    if pod_id:
        pod = next((p for p in pods if p.id == pod_id or p.huid == pod_id or p.name == pod_id), None)
        if pod:
            pods = [pod]
        else:
            ui.error(f"Pod '{pod_id}' not found")
            return

    # Build table
    table, header = display.build_pods_table(pods)

    # Display
    ui.info(header)
    ui.print(table)
