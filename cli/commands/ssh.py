"""SSH to pods command using Lium SDK."""
from __future__ import annotations

import os
import sys
import subprocess
import shutil
from typing import Optional, List

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, PodInfo
from ..utils import console, handle_errors, loading_status


def _resolve_pod(target: str, all_pods: List[PodInfo]) -> Optional[PodInfo]:
    """Resolve a single pod from target specification."""
    # Try as index (1-based from ps output)
    try:
        idx = int(target) - 1
        if 0 <= idx < len(all_pods):
            return all_pods[idx]
    except ValueError:
        pass
    
    # Try as pod ID/name/huid
    for pod in all_pods:
        if target in (pod.id, pod.name, pod.huid):
            return pod
    
    return None


@click.command("ssh")
@click.argument("target")
@handle_errors
def ssh_command(target: str):
    """Open SSH session to a GPU pod.
    
    TARGET: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
    
    Examples:
      lium ssh 1                    # SSH to pod #1 from ps
      lium ssh eager-wolf-aa        # SSH to specific pod
    """
    # Check if ssh is available
    if not shutil.which("ssh"):
        console.print("[red]Error: 'ssh' command not found. Please install an SSH client.[/red]")
        return
    
    # Get pods and resolve target
    lium = Lium()
    with loading_status("Loading pods", ""):
        all_pods = lium.ps()
    
    pod = _resolve_pod(target, all_pods)
    
    if not pod:
        console.print(f"[red]Pod '{target}' not found[/red]")
        # Show available pods
        if all_pods:
            console.print("\n[dim]Available pods:[/dim]")
            for i, p in enumerate(all_pods, 1):
                status_color = "green" if p.status == "RUNNING" else "yellow"
                console.print(f"  {i}. [{status_color}]{p.huid}[/] ({p.status})")
        return
    
    # Check if pod is running
    if pod.status != "RUNNING":
        console.print(f"[yellow]Warning: Pod '{pod.huid}' is {pod.status}[/yellow]")
        if pod.status in ["STOPPED", "FAILED"]:
            console.print("[red]Cannot SSH to a stopped or failed pod[/red]")
            return
    
    # Check if SSH command is available
    if not pod.ssh_cmd:
        console.print(f"[red]No SSH connection available for pod '{pod.huid}'[/red]")
        return
    
    # Get SSH command from SDK
    try:
        ssh_cmd = lium.ssh(pod)
        console.print(f"[dim]Connecting to {pod.huid}...[/dim]")
    except ValueError as e:
        # Fallback to using the raw ssh_cmd if SDK method fails
        ssh_cmd = pod.ssh_cmd
        console.print(f"[dim]Connecting to {pod.huid} (using default SSH)...[/dim]")
    
    # Execute SSH command interactively
    try:
        # Use subprocess.run to hand over terminal control for interactive session
        result = subprocess.run(ssh_cmd, shell=True, check=False)
        
        # Only show exit code if it's non-zero and not 255 (common disconnect code)
        if result.returncode != 0 and result.returncode != 255:
            console.print(f"\n[dim]SSH session ended with exit code {result.returncode}[/dim]")
    except KeyboardInterrupt:
        console.print("\n[yellow]SSH session interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]Error executing SSH: {e}[/red]")