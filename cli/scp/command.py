"""SCP command implementation."""

from typing import Optional

import click

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors
from . import validation, parsing
from .actions import ScpAction


@click.command("scp")
@click.argument("targets")
@click.argument("source_path")
@click.argument("destination_path", required=False)
@click.option("--download", "-d", is_flag=True, help="Download files from pods to your local machine.")
@handle_errors
def scp_command(
    targets: str,
    source_path: str,
    destination_path: Optional[str],
    download: bool,
):
    """Copy files between your machine and GPU pods.

    Upload is the default behavior. Add `--download / -d` to pull files
    from pods back to your machine.

    \b
    TARGETS: Pod identifiers - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
      - Comma-separated (1,2,eager-wolf-aa)
      - All pods (all)

    SOURCE_PATH / DESTINATION_PATH:
      - Upload (default): SOURCE is a local file, DESTINATION is optional remote path
      - Download (--download): SOURCE is remote path, DESTINATION is optional local path
        (for multiple pods DESTINATION must be a directory)

    \b
    Examples:
      lium scp 1 ./script.py                    # Upload to ~/script.py on pod #1
      lium scp eager-wolf-aa ./data.csv ~/data/ # Upload to ~/data/ directory
      lium scp all ./config.json                # Upload to all pods
      lium scp 1,2,3 ./file.txt ~/bin/file.txt  # Upload to specific path on multiple pods
      lium scp 2 /root/output.log ./outputs -d  # Download from pod #2 into ./outputs/
    """

    # Validate
    valid, error = validation.validate(targets, source_path, download)
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
    parsed, error = parsing.parse(targets, source_path, destination_path, download, all_pods)
    if error:
        ui.error(error)
        return

    pods = parsed.get("pods")
    download_mode = parsed.get("download")

    # Display info
    if not download_mode:
        local_file = parsed.get("local_file")
        remote_path = parsed.get("remote_path")
        ui.info(f"Uploading: {local_file.name}")
        ui.info(f"To: {remote_path}")
    else:
        remote_path = parsed.get("remote_path")
        destination_map = parsed.get("destination_map")
        ui.info(f"Downloading: {remote_path}")
        if len(pods) == 1:
            _, local_dest = destination_map[pods[0].huid]
            ui.info(f"To: {local_dest}")

    ui.info(f"Pods: {len(pods)}")

    # Execute
    ctx = {
        "lium": lium,
        "pods": pods,
        "download": download_mode,
        **parsed
    }

    action = ScpAction()
    result = action.execute(ctx)

    if not result.ok:
        failed_huids = result.data.get("failed_huids", [])
        action_name = "download from" if download_mode else "upload to"
        ui.error(f"Failed to {action_name}: {', '.join(failed_huids)}")
