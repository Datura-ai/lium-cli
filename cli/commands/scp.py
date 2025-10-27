"""Copy files between pods and local machine via SCP for Lium CLI."""
from __future__ import annotations
from rich.prompt import Confirm
import os
from pathlib import Path
from typing import Optional

import click

from cli.lium_sdk import Lium, PodInfo
from ..utils import console, handle_errors, loading_status, parse_targets


@click.command("scp")
@click.argument("targets")
@click.argument("source_path")
@click.argument("destination_path", required=False)
@click.option("--download", "-d", is_flag=True, help="Download files from pods to your local machine.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def scp_command(
    targets: str,
    source_path: str,
    destination_path: Optional[str],
    download: bool,
    yes: bool,
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

    # Upload: validate local file and remote path defaults
    if not download:
        local_file = Path(source_path).expanduser().resolve()
        if not local_file.is_file():
            console.error(f"Error: '{source_path}' is not a file")
            return
        remote_path = destination_path or f"/root/{local_file.name}"
        remote_path = remote_path.strip()
        console.info(f"File to upload: {local_file}")
    else:
        remote_path = source_path.strip()
        if not remote_path:
            console.error("Remote path is required when downloading.")
            return
        remote_basename = Path(remote_path).name
        if not remote_basename:
            remote_basename = "downloaded_file"
        destination_map = {}
        destination_str = destination_path or ""
        destination_input = Path(destination_path).expanduser().resolve() if destination_path else None
        multiple_pods = len(selected_pods) > 1
        destination_is_dir_hint = bool(destination_str and destination_str.endswith(os.sep))

        if multiple_pods:
            if destination_input and destination_input.exists() and not destination_input.is_dir():
                console.error("Destination must be a directory when downloading from multiple pods.")
                return
            base_dir = destination_input if destination_input else Path.cwd()
            destination_map = {
                pod.huid: (pod, (base_dir / f"{pod.huid}-{remote_basename}").resolve())
                for pod in selected_pods
            }
        else:
            pod = selected_pods[0]
            if destination_input:
                is_dir = (destination_input.exists() and destination_input.is_dir()) or destination_is_dir_hint
                if is_dir:
                    local_dest = (destination_input / remote_basename).resolve()
                else:
                    local_dest = destination_input.resolve()
            else:
                local_dest = (Path.cwd() / remote_basename).resolve()
            destination_map[pod.huid] = (pod, local_dest)
        console.info(f"Remote file to download: {remote_path}")

    # Show what we're about to copy
    console.info(f"Target pods ({len(selected_pods)}):")
    if download:
        for pod_huid, (pod, local_dest) in destination_map.items():
            console.info(f"  - {console.get_styled(pod_huid, 'pod_id')} ({pod.status}) → {local_dest}")
    else:
        for pod in selected_pods:
            console.info(f"  - {console.get_styled(pod.huid, 'pod_id')} ({pod.status}) → {remote_path}")

    # Confirm unless -y flag
    if not yes:
        pods_text = f"{len(selected_pods)} pod{'s' if len(selected_pods) > 1 else ''}"
        if download:
            confirm_msg = f"\nDownload '{remote_path}' from {pods_text}?"
        else:
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
            if download:
                _, local_dest = destination_map[pod.huid]
                console.dim(f"Downloading from {pod.huid}...", end="")
                local_dest.parent.mkdir(parents=True, exist_ok=True)
                lium.download(pod, remote_path, str(local_dest))
            else:
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
            if download:
                pod_huid = selected_pods[0].huid
                _, local_dest = destination_map[pod_huid]
                console.success(f"File downloaded successfully to {local_dest}")
            else:
                console.success("File copied successfully")
        else:
            action = "download file" if download else "copy file"
            console.error(f"Failed to {action}")
    else:
        console.dim(f"Completed {success_count}/{len(selected_pods)} transfers")
        
        if failed_pods:
            console.error(f"Failed pods: {', '.join(failed_pods)}")
        
        if success_count == len(selected_pods):
            if download:
                console.success("All downloads successful")
            else:
                console.success("All copies successful")
