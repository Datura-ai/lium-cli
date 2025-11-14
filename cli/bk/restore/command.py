"""Bk restore command implementation."""

import click

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors, ensure_config
from . import validation, parsing
from .actions import RestoreBackupAction


@click.command("restore")
@click.argument("pod_id")
@click.option("--id", "backup_id", required=True, help="Backup ID to restore")
@click.option("--to", "restore_path", default="/root", help="Restore path (default: /root)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def bk_restore_command(pod_id: str, backup_id: str, restore_path: str, yes: bool):
    """Restore a backup to a pod.

    \b
    POD_ID: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)

    \b
    Examples:
      lium bk restore 1 --id <backup-uuid>              # Restore to default /root
      lium bk restore 1 --id <backup-uuid> --to /home   # Restore to specific path
      lium bk restore eager-wolf --id <backup-uuid> -y  # Skip confirmation
    """
    ensure_config()

    # Validate
    valid, error = validation.validate(pod_id, backup_id)
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
        if not ui.confirm(f"Restore backup to pod '{pod_id}' at {restore_path}?"):
            return

    # Execute
    ctx = {
        "lium": lium,
        "pod_name": pod_name,
        "backup_id": backup_id,
        "restore_path": restore_path
    }

    action = RestoreBackupAction()
    result = ui.load(f"Restoring backup to {restore_path}", lambda: action.execute(ctx))

    if not result.ok:
        ui.error(result.error)
