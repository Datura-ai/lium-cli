"""Simplified rsync command for Lium CLI."""
from __future__ import annotations
from rich.prompt import Confirm
import os
import sys
import shutil
from pathlib import Path
from typing import Optional

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium
from ..utils import console, handle_errors, loading_status, parse_targets


@click.command("rsync")
@click.argument("targets")
@click.argument("local_path", type=click.Path(exists=True, readable=True))
@click.argument("remote_path", required=False)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def rsync_command(targets: str, local_path: str, remote_path: Optional[str], yes: bool):
    """Sync directories to GPU pods using rsync.

    \b
    Examples:
      lium rsync 1 ./project                     # Sync to /root/project on pod #1
      lium rsync all ./models                    # Sync to all pods
      lium rsync 1,2,3 ./code /root/workspace/   # Sync to multiple pods
    """
    # Quick validations
    if not shutil.which("rsync"):
        console.error("Error: 'rsync' command not found. Please install rsync locally.")
        return

    local_dir = Path(local_path).expanduser().resolve()

    # Get pods
    lium = Lium()
    with loading_status("Loading pods", ""):
        all_pods = lium.ps()

    selected_pods = parse_targets(targets, all_pods)
    if not selected_pods:
        console.error(f"No pods match targets: {targets}")
        return

    remote_path = remote_path or f"/root/{local_dir.name}"

    # Show what we're about to sync
    sync_type = "directory" if local_dir.is_dir() else "file"
    console.info(f"{sync_type.title()} to sync: {local_dir}")
    console.info(f"Target pods ({len(selected_pods)}):")
    for pod in selected_pods:
        console.info(f"  - {console.get_styled(pod.huid, 'pod_id')} ({pod.status}) → {remote_path}")

    # Simple confirmation
    if not yes:
        pods_text = f"{len(selected_pods)} pod{'s' if len(selected_pods) > 1 else ''}"
        if not Confirm.ask(f"\nSync '{local_dir.name}' to {remote_path} on {pods_text}?", default=True):
            return

    # Sync with minimal output
    success = 0
    for pod in selected_pods:
        try:
            # Simple rsync check and install
            check_result = lium.exec(pod, "which rsync")
            if not check_result.get("success"):
                with loading_status(f"Installing rsync on {pod.huid}", ""):
                    install_result = lium.exec(pod, "apt-get update -qq && apt-get install -y rsync -qq")
                if not install_result.get("success"):
                    console.error(f"✗ Failed to install rsync on {pod.huid}")
                    continue

            # Format path for directories
            local_formatted = str(local_dir) + ('/' if local_dir.is_dir() else '')

            with loading_status(f"Syncing to {pod.huid}", ""):
                lium.rsync(pod, local_formatted, remote_path)
            success += 1
        except Exception as e:
            console.error(f" ✗ {e}")
