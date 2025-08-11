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
from ..utils import console, handle_errors, loading_status


def _parse_targets(targets: str, all_pods: List[PodInfo]) -> List[PodInfo]:
    """Parse target specification and return matching pods."""
    if targets.lower() == "all":
        return all_pods
    
    selected = []
    for target in targets.split(","):
        target = target.strip()
        
        # Try as index (1-based from ps output)
        try:
            idx = int(target) - 1
            if 0 <= idx < len(all_pods):
                selected.append(all_pods[idx])
                continue
        except ValueError:
            pass
        
        # Try as pod ID/name/huid
        for pod in all_pods:
            if target in (pod.id, pod.name, pod.huid):
                selected.append(pod)
                break
    
    return selected


@click.command("scp")
@click.argument("targets")
@click.argument("local_path", type=click.Path(exists=True, readable=True))
@click.argument("remote_path", required=False)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def scp_command(targets: str, local_path: str, remote_path: Optional[str], yes: bool):
    """Copy local files to GPU pods.
    
    TARGETS: Pod identifiers - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
      - Comma-separated (1,2,eager-wolf-aa)
      - All pods (all)
    
    LOCAL_PATH: Local file path to copy
    REMOTE_PATH: Remote destination path (optional, defaults to ~/filename)
    
    Examples:
      lium scp 1 ./script.py                    # Copy to ~/script.py on pod #1
      lium scp eager-wolf-aa ./data.csv ~/data/ # Copy to ~/data/ directory
      lium scp all ./config.json                # Copy to all pods
      lium scp 1,2,3 ./file.txt ~/bin/file.txt  # Copy to specific path on multiple pods
    """
    # Validate local file
    local_file = Path(local_path).expanduser().resolve()
    if not local_file.is_file():
        console.print(f"[red]Error: '{local_path}' is not a file[/red]")
        return
    
    # Get pods and resolve targets
    lium = Lium()
    with loading_status("Loading pods", ""):
        all_pods = lium.ps()
    
    if not all_pods:
        console.print("[yellow]No active pods[/yellow]")
        return
    
    selected_pods = _parse_targets(targets, all_pods)
    
    if not selected_pods:
        console.print(f"[red]No pods match targets: {targets}[/red]")
        return
    
    # Determine remote path
    if not remote_path:
        remote_path = f"/root/{local_file.name}"
    
    # Show what we're about to copy
    console.print(f"[cyan]File to copy:[/cyan] {local_file}")
    console.print(f"[cyan]Target pods ({len(selected_pods)}):[/cyan]")
    for pod in selected_pods:
        console.print(f"  - [cyan]{pod.huid}[/cyan] ({pod.status}) → {remote_path}")
    
    # Confirm unless -y flag
    if not yes:
        pods_text = f"{len(selected_pods)} pod{'s' if len(selected_pods) > 1 else ''}"
        confirm_msg = f"\nCopy '{local_file.name}' to {remote_path} on {pods_text}?"
        if not Confirm.ask(confirm_msg, default=True):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    # Copy to pods
    success_count = 0
    failed_pods = []
    
    console.print()
    for pod in selected_pods:
        try:
            console.print(f"[dim]Copying to {pod.huid}...[/dim]", end="")
            lium.scp(pod, str(local_file), remote_path)
            console.print(f" [green]✓[/green]")
            success_count += 1
        except Exception as e:
            console.print(f" [red]✗[/red]")
            console.print(f"[red]  Error: {e}[/red]")
            failed_pods.append(pod.huid)
    
    # Summary
    console.print()
    if len(selected_pods) == 1:
        if success_count == 1:
            console.print("[green]File copied successfully[/green]")
        else:
            console.print("[red]Failed to copy file[/red]")
    else:
        console.print(f"[dim]Copied to {success_count}/{len(selected_pods)} pods[/dim]")
        
        if failed_pods:
            console.print(f"[red]Failed pods: {', '.join(failed_pods)}[/red]")
        
        if success_count == len(selected_pods):
            console.print("[green]All copies successful[/green]")
