"""Bk rm command implementation."""

import click

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors, ensure_config
from . import validation, parsing
from .actions import RemoveBackupAction


@click.command("rm")
@click.argument("pod_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def bk_rm_command(pod_id: str, yes: bool):
    """Remove backup configuration for a pod.

    \b
    POD_ID: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)

    \b
    Examples:
      lium bk rm 1                  # Remove backup for pod #1
      lium bk rm eager-wolf-aa      # Remove backup by name
      lium bk rm 1 --yes            # Remove without confirmation
    """
    ensure_config()

    # Validate
    valid, error = validation.validate(pod_id)
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
    parsed, error = parsing.parse(pod_id, all_pods)
    if error:
        ui.error(error)
        return

    pod_name = parsed.get("pod_name")

    # Confirm
    if not yes:
        if not ui.confirm(f"Remove backup configuration for pod '{pod_id}'?"):
            return

    # Execute
    ctx = {"lium": lium, "pod_name": pod_name}

    action = RemoveBackupAction()
    result = ui.load("Removing backup configuration", lambda: action.execute(ctx))

    if not result.ok:
        ui.error(result.error)
