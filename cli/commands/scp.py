"""Copy files to pods via SCP for Lium CLI."""
from __future__ import annotations
from rich.prompt import Confirm
import os
import sys
from pathlib import Path
from typing import Optional, List

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, PodInfo
from ..utils import console, handle_errors, loading_status, parse_targets


@click.command("scp")
@click.argument("targets")
@click.argument("local_path", type=click.Path(exists=True, readable=True))
@click.argument("remote_path", required=False)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def scp_command(targets: str, local_path: str, remote_path: Optional[str], yes: bool):
    """Copy local files to GPU pods.
    
    \b
    TARGETS: Pod identifiers - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
      - Comma-separated (1,2,eager-wolf-aa)
      - All pods (all)
    
    LOCAL_PATH: Local file path to copy
    REMOTE_PATH: Remote destination path (optional, defaults to ~/filename)
    
    \b
    Examples:
      lium scp 1 ./script.py                    # Copy to ~/script.py on pod #1
      lium scp eager-wolf-aa ./data.csv ~/data/ # Copy to ~/data/ directory
      lium scp all ./config.json                # Copy to all pods
      lium scp 1,2,3 ./file.txt ~/bin/file.txt  # Copy to specific path on multiple pods
    """
    # Validate local file
    local_file = Path(local_path).expanduser().resolve()
    if not local_file.is_file():
        console.error(f"Error: '{local_path}' is not a file")
        return
    
    # Get pods and resolve targets
    lium = Lium()
    with loading_status("Loading pods", ""):
        all_pods = lium.ps()
    
    if not all_pods:
        console.warning("No active pods")
        return
    
    selected_pods = parse_targets(targets, all_pods)
    
    if not selected_pods:
        console.error(f"No pods match targets: {targets}")
        return
    
    # Determine remote path
    if not remote_path:
        remote_path = f"/root/{local_file.name}"
    
    # Show what we're about to copy
    console.info(f"File to copy: {local_file}")
    console.info(f"Target pods ({len(selected_pods)}):")
    for pod in selected_pods:
        console.info(f"  - {console.get_styled(pod.huid, 'pod_id')} ({pod.status}) → {remote_path}")
    
    # Confirm unless -y flag
    if not yes:
        pods_text = f"{len(selected_pods)} pod{'s' if len(selected_pods) > 1 else ''}"
        confirm_msg = f"\nCopy '{local_file.name}' to {remote_path} on {pods_text}?"
        if not Confirm.ask(confirm_msg, default=True):
            console.warning("Cancelled")
            return
    
    # Copy to pods
    success_count = 0
    failed_pods = []
    
    console.info("")
    for pod in selected_pods:
        try:
            console.dim(f"Copying to {pod.huid}...", end="")
            lium.scp(pod, str(local_file), remote_path)
            console.success(" ✓")
            success_count += 1
        except Exception as e:
            console.error(" ✗")
            console.error(f"  Error: {e}")
            failed_pods.append(pod.huid)
    
    # Summary
    console.info("")
    if len(selected_pods) == 1:
        if success_count == 1:
            console.success("File copied successfully")
        else:
            console.error("Failed to copy file")
    else:
        console.dim(f"Copied to {success_count}/{len(selected_pods)} pods")
        
        if failed_pods:
            console.error(f"Failed pods: {', '.join(failed_pods)}")
        
        if success_count == len(selected_pods):
            console.success("All copies successful")
