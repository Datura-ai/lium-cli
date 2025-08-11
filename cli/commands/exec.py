"""Execute commands on pods using Lium SDK."""
from __future__ import annotations

import os
import sys
from typing import Optional, List, Tuple
from pathlib import Path

import click
from rich.text import Text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, PodInfo
from ..utils import console, handle_errors, loading_status, parse_targets


def _format_output(pod: PodInfo, result: dict, show_header: bool = True) -> None:
    """Format and display execution output."""
    if show_header:
        console.print(f"\n[bold cyan]── {pod.huid} ──[/]")
    
    if result.get("success"):
        if result.get("stdout"):
            console.print(result["stdout"], end="")
        if result.get("stderr"):
            console.print(f"[yellow]{result['stderr']}[/]", end="")
    else:
        if result.get("error"):
            console.print(f"[red]Error: {result['error']}[/]")
        else:
            console.print(f"[red]Command failed (exit code: {result.get('exit_code', 'unknown')})[/]")
            if result.get("stderr"):
                console.print(f"[red]{result['stderr']}[/]", end="")


@click.command("exec")
@click.argument("targets")
@click.argument("command", required=False)
@click.option("--script", "-s", type=click.Path(exists=True), help="Execute a script file")
@click.option("--env", "-e", multiple=True, help="Set environment variables (KEY=VALUE)")
@handle_errors
def exec_command(targets: str, command: Optional[str], script: Optional[str], env: Tuple[str]):
    """Execute commands on GPU pods.
    
    TARGETS: Pod identifiers - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
      - Comma-separated (1,2,eager-wolf-aa)
      - All pods (all)
    
    COMMAND: Command to execute
    
    Examples:
      lium exec eager-wolf-aa "nvidia-smi"     # Run on specific pod
      lium exec 1 "python --version"           # Run on pod #1 from ps
      lium exec 1,2,3 "uptime"                 # Run on multiple pods
      lium exec all "df -h"                    # Run on all pods
      lium exec 1 --script setup.sh            # Run script on pod
      lium exec 1 -e API_KEY=xyz "python app.py"  # With env vars
    """
    # Validate inputs
    if not command and not script:
        console.print("[red]Error: Either COMMAND or --script must be provided[/red]")
        return
    
    if command and script:
        console.print("[red]Error: Cannot use both COMMAND and --script[/red]")
        return
    
    # Load script if provided
    if script:
        try:
            with open(script, 'r') as f:
                command = f.read()
        except Exception as e:
            console.print(f"[red]Error reading script: {e}[/red]")
            return
    
    # Parse environment variables
    env_dict = {}
    for env_var in env:
        if '=' not in env_var:
            console.print(f"[red]Error: Invalid env format '{env_var}' (use KEY=VALUE)[/red]")
            return
        key, value = env_var.split('=', 1)
        env_dict[key] = value
    
    # Get pods and resolve targets
    lium = Lium()
    with loading_status("Loading pods", ""):
        all_pods = lium.ps()
    
    selected_pods = parse_targets(targets, all_pods)
    
    if not selected_pods:
        console.print(f"[red]No pods match targets: {targets}[/red]")
        return
    
    # Show what we're executing
    if len(selected_pods) == 1:
        pod = selected_pods[0]
        console.print(f"Executing on [cyan]{pod.huid}[/cyan]")
    else:
        console.print(f"Executing on [cyan]{len(selected_pods)}[/cyan] pods")
    
    if env_dict:
        console.print(f"[dim]Environment: {', '.join(f'{k}={v}' for k, v in env_dict.items())}[/dim]")
    
    # Execute on pods
    if len(selected_pods) == 1:
        # Single pod - stream output
        pod = selected_pods[0]
        try:
            result = lium.exec(pod, command, env_dict)
            _format_output(pod, result, show_header=False)
        except Exception as e:
            console.print(f"[red]Failed: {e}[/red]")
    else:
        # Multiple pods - use parallel execution
        results = lium.exec_all(selected_pods, command, env_dict)
        
        for pod, result in zip(selected_pods, results):
            _format_output(pod, result)
        
        # Summary
        success_count = sum(1 for r in results if r.get("success"))
        console.print(f"\n[dim]Completed: {success_count}/{len(results)} successful[/dim]")