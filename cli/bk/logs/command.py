"""Bk logs command implementation."""

from typing import Optional

import click

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors, ensure_config
from . import validation, parsing, display
from .actions import GetBackupLogsAction


@click.command("logs")
@click.argument("pod_id", required=False)
@click.option("--id", "backup_id", help="Specific backup ID to show details")
@handle_errors
def bk_logs_command(pod_id: Optional[str], backup_id: Optional[str]):
    """Show backup logs for a pod or specific backup.

    \b
    POD_ID: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)

    \b
    Examples:
      lium bk logs 1                 # Show recent logs for pod #1
      lium bk logs eager-wolf        # Show logs by pod name
      lium bk logs --id abc123       # Show details for specific backup
    """
    ensure_config()

    # Validate
    valid, error = validation.validate(pod_id, backup_id)
    if not valid:
        ui.error(error)
        return

    lium = Lium()

    if backup_id:
        # Show specific backup details
        ui.info(f"Backup ID: {backup_id}")

        ctx = {"lium": lium, "backup_id": backup_id}

        action = GetBackupLogsAction()
        result = ui.load("Loading backup details", lambda: action.execute(ctx))

        if not result.ok:
            ui.error(result.error)
            return

        pod_name_found = result.data.get("pod_name")
        log = result.data.get("log")

        output = display.format_single_backup(pod_name_found, log)
        ui.print(output)
        return

    # Execute - load and parse in one go
    def load_logs():
        all_pods = lium.ps()
        if not all_pods:
            return None, "No active pods"

        parsed, error = parsing.parse(pod_id, all_pods)
        if error:
            return None, error

        pod_name = parsed.get("pod_name")
        ctx = {"lium": lium, "pod_name": pod_name}

        action = GetBackupLogsAction()
        return action.execute(ctx), None

    result, error = ui.load("Loading backup logs", load_logs)

    if error:
        ui.error(error)
        return

    if result and result.error:
        ui.error(result.error)
        return

    logs = result.data.get("logs")

    if not logs:
        ui.warning(f"No backup logs found for pod '{pod_id}'")
        return

    # Display
    table = display.format_logs_table(logs)
    ui.print(table, highlight=True)
