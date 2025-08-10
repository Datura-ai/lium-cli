"""List active pods command using Lium SDK (tight table design)."""
from __future__ import annotations

import os
import sys
from typing import List, Optional
from datetime import datetime, timezone

import click
from rich.table import Table
from rich.text import Text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, PodInfo
from ..utils import console, handle_errors, loading_status


def _status_style(status: str) -> str:
    """Get color style for status."""
    status_upper = status.upper()
    if status_upper in ["RUNNING"]:
        return "green"
    elif status_upper in ["FAILED", "STOPPED"]:
        return "red"
    elif status_upper in ["PENDING", "STOP_PENDING", "START_PENDING"]:
        return "yellow"
    elif status_upper in ["DELETING"]:
        return "dim"
    return "dim"


def _format_uptime(created_at: str) -> str:
    """Format uptime from created_at timestamp."""
    if not created_at:
        return "—"
    
    try:
        # Parse ISO format timestamp
        if created_at.endswith('Z'):
            dt_created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif '+' not in created_at and '-' not in created_at[10:]:
            dt_created = datetime.fromisoformat(created_at).replace(tzinfo=timezone.utc)
        else:
            dt_created = datetime.fromisoformat(created_at)
        
        now_utc = datetime.now(timezone.utc)
        duration = now_utc - dt_created
        hours = duration.total_seconds() / 3600
        
        if hours < 1:
            mins = duration.total_seconds() / 60
            return f"{mins:.0f}m"
        elif hours < 24:
            return f"{hours:.1f}h"
        else:
            days = hours / 24
            return f"{days:.1f}d"
    except:
        return "—"


def _format_cost(created_at: str, price_per_hour: Optional[float]) -> str:
    """Calculate and format cost based on uptime."""
    if not created_at or price_per_hour is None:
        return "—"
    
    try:
        if created_at.endswith('Z'):
            dt_created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif '+' not in created_at and '-' not in created_at[10:]:
            dt_created = datetime.fromisoformat(created_at).replace(tzinfo=timezone.utc)
        else:
            dt_created = datetime.fromisoformat(created_at)
        
        now_utc = datetime.now(timezone.utc)
        duration = now_utc - dt_created
        hours = duration.total_seconds() / 3600
        cost = hours * price_per_hour
        return f"${cost:.2f}"
    except:
        return "—"


def _format_ssh_command(ssh_cmd: Optional[str]) -> str:
    """Format SSH command for display."""
    if not ssh_cmd:
        return "—"
    
    # Return the full SSH command, styled as code
    return ssh_cmd


def show_pods(pods: List[PodInfo]) -> None:
    """Display pods in a tight, well-engineered table."""
    if not pods:
        console.print("[yellow]No active pods[/yellow]")
        return
    
    # Title
    console.print(Text("Pods", style="bold"), end="")
    console.print(f"  [dim]({len(pods)} active)[/dim]")
    
    table = Table(
        show_header=True,
        header_style="dim",
        box=None,        # no ASCII borders
        pad_edge=False,
        expand=True,     # full terminal width
        padding=(0, 1),  # tight padding
    )
    
    # Add columns with fixed or ratio widths
    table.add_column("Pod", justify="left", ratio=5, min_width=18, overflow="fold")
    table.add_column("Status", justify="left", width=13, no_wrap=True)
    table.add_column("Config", justify="left", width=14, no_wrap=True)
    table.add_column("$/h", justify="right", width=8, no_wrap=True)
    table.add_column("Spent", justify="right", width=10, no_wrap=True)
    table.add_column("Uptime", justify="right", width=9, no_wrap=True)
    table.add_column("SSH", justify="left", ratio=6, min_width=30, overflow="fold")

    
    for i, pod in enumerate(pods, 1):
        # Get executor info (now it's an ExecutorInfo object)
        executor = pod.executor
        
        if executor:
            # Use ExecutorInfo properties directly
            config = f"{executor.gpu_count}×{executor.gpu_type}" if executor.gpu_count > 1 else executor.gpu_type
            price_str = f"${executor.price_per_hour:.2f}"
            price_per_hour = executor.price_per_hour
        else:
            # Fallback if no executor info
            config = "—"
            price_str = "—"
            price_per_hour = None
        
        # Status with color (uppercase)
        status_color = _status_style(pod.status)
        status_text = f"[{status_color}]{pod.status.upper()}[/]"
        
        row = [
            f"[cyan]{pod.huid}[/]",
            status_text,
            config,
            price_str,
            _format_cost(pod.created_at, price_per_hour),
            _format_uptime(pod.created_at),
            f"[blue]{_format_ssh_command(pod.ssh_cmd)}[/]",
        ]
        
        table.add_row(*row)
    
    console.print(table)


@click.command("ps")
@click.argument("pod_id", required=False)
@handle_errors
def ps_command(pod_id: Optional[str]):
    """List active GPU pods.
    
    POD_ID: Optional specific pod ID/name to show details for
    
    Examples:
      lium ps                # Show all active pods
      lium ps eager-wolf-aa  # Show specific pod details
    """
    with loading_status("Loading pods", ""):
        pods = Lium().ps()
    
    if pod_id:
        # Filter for specific pod
        pod = next((p for p in pods if p.id == pod_id or p.huid == pod_id or p.name == pod_id), None)
        if pod:
            show_pods([pod])
        else:
            console.print(f"[red]Pod '{pod_id}' not found[/red]")
    else:
        show_pods(pods)
