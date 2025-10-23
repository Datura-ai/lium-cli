"""List active pods command."""

import os
import sys
from datetime import datetime, timezone
from typing import List, Optional

import click
from rich.table import Table
from rich.text import Text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lium_sdk import Lium, PodInfo
from ..utils import console, handle_errors, loading_status, ensure_config




def _parse_timestamp(timestamp: str) -> Optional[datetime]:
    """Parse ISO format timestamp."""
    try:
        if timestamp.endswith('Z'):
            return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif '+' not in timestamp and '-' not in timestamp[10:]:
            return datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
        else:
            return datetime.fromisoformat(timestamp)
    except (ValueError, AttributeError):
        return None


def _format_uptime(created_at: str) -> str:
    """Format uptime from created_at timestamp."""
    if not created_at:
        return "—"
    
    dt_created = _parse_timestamp(created_at)
    if not dt_created:
        return "—"
    
    duration = datetime.now(timezone.utc) - dt_created
    hours = duration.total_seconds() / 3600
    
    if hours < 1:
        mins = duration.total_seconds() / 60
        return f"{mins:.0f}m"
    elif hours < 24:
        return f"{hours:.1f}h"
    else:
        days = hours / 24
        return f"{days:.1f}d"


def _format_cost(created_at: str, price_per_hour: Optional[float]) -> str:
    """Calculate and format cost based on uptime."""
    if not created_at or price_per_hour is None:
        return "—"
    
    dt_created = _parse_timestamp(created_at)
    if not dt_created:
        return "—"
    
    duration = datetime.now(timezone.utc) - dt_created
    hours = duration.total_seconds() / 3600
    cost = hours * price_per_hour
    return f"${cost:.2f}"


def _format_template_name(template: dict) -> str:
    """Format template name for display."""
    if not template:
        return "—"
    
    # Try to get template name, fallback to template_name field
    name = template.get("name") or template.get("template_name") or "—"
    return name


def _format_ports(ports: dict) -> str:
    """Format port mappings with consistent spacing."""
    if not ports:
        return "—"
    
    # Format as internal:external pairs
    port_pairs = [f"{k}:{v}" for k, v in ports.items()]
    
    # Join all ports with comma and space for single-line display
    return ", ".join(port_pairs)


def _format_scheduled_termination(removal_scheduled_at: Optional[str]) -> str:
    """Format scheduled termination time."""
    if not removal_scheduled_at:
        return "None"

    try:
        scheduled_time = _parse_timestamp(removal_scheduled_at)
        if not scheduled_time:
            return "Yes"

        # Convert to local timezone
        local_time = scheduled_time.astimezone()

        # Format as "Oct 20, 2025 6:00 AM"
        return local_time.strftime("%b %d, %Y %-I:%M %p")
    except Exception:
        return "Yes"


def _format_jupyter_status(pod: PodInfo) -> str:
    """Format Jupyter installation status."""
    if not hasattr(pod, 'jupyter_installation_status') or not pod.jupyter_installation_status:
        return "—"

    status = pod.jupyter_installation_status
    if status == "SUCCESS":
        return "Yes"
    elif status == "INSTALLING":
        return "Installing"
    elif status == "FAILED":
        return "Failed"
    else:
        return status[:8]  # Abbreviated status


def show_pods(pods: List[PodInfo], short: bool = False) -> None:
    """Display pods in a tight, well-engineered table."""
    if not pods:
        console.warning("No active pods")
        return

    # Title
    console.info(Text("Pods", style="bold"), end="")
    console.dim(f"  ({len(pods)} active)")

    table = Table(
        show_header=True,
        header_style="dim",
        box=None,        # no ASCII borders
        pad_edge=False,
        expand=True,     # full terminal width
        padding=(0, 1),  # tight padding
    )

    # Add columns with fixed or ratio widths
    table.add_column("Pod", justify="left", ratio=3, min_width=18, overflow="fold")
    table.add_column("Status", justify="left", width=11, no_wrap=True)
    table.add_column("Config", justify="left", width=12, no_wrap=True)
    table.add_column("Template", justify="left", ratio=2, min_width=12, overflow="ellipsis")
    table.add_column("$/h", justify="right", width=6, no_wrap=True)
    table.add_column("Spent", justify="right", width=8, no_wrap=True)
    table.add_column("Uptime", justify="right", width=7, no_wrap=True)
    table.add_column("Scheduled Terminate", justify="left", width=23, overflow="ellipsis")
    table.add_column("Jupyter", justify="center", width=11, no_wrap=True)
    table.add_column("Ports", justify="left", ratio=3, min_width=15, overflow="fold") if not short else None
    table.add_column("Name", justify="left", ratio=2, min_width=15, overflow="fold")

    for pod in pods:
        executor = pod.executor
        if executor:
            config = f"{executor.gpu_count}×{executor.gpu_type}" if executor.gpu_count > 1 else executor.gpu_type
            price_str = f"${executor.price_per_hour:.2f}"
            price_per_hour = executor.price_per_hour
        else:
            config = "—"
            price_str = "—"
            price_per_hour = None

        status_color = console.pod_status_color(pod.status)
        status_text = f"[{status_color}]{pod.status.upper()}[/]"

        # Format template name and port mappings for this GPU pod
        template_name = _format_template_name(pod.template)
        ports_display = _format_ports(pod.ports)

        # Get scheduled termination status (support both field names)
        removal_scheduled_at = getattr(pod, 'removal_scheduled_at', None) or getattr(pod, 'removal_rescheduled_at', None)
        schedule_display = _format_scheduled_termination(removal_scheduled_at)

        # Get Jupyter status
        jupyter_display = _format_jupyter_status(pod)
        jupyter_color = "green" if jupyter_display == "Yes" else ("yellow" if jupyter_display == "Installing" else ("red" if jupyter_display == "Failed" else "dim"))

        row = [
            console.get_styled(pod.huid, 'pod_id'),
            status_text,
            config,
            console.get_styled(template_name, 'info'),
            price_str,
            _format_cost(pod.created_at, price_per_hour),
            _format_uptime(pod.created_at),
            console.get_styled(schedule_display, 'warning' if removal_scheduled_at else 'dim'),
            console.get_styled(jupyter_display, jupyter_color),
            console.get_styled(ports_display, 'info'),
            console.get_styled(pod.name or "—", 'info'),
        ]
        if short:
            row.pop(-2)  # Remove Ports column for short view
        table.add_row(
            *row
        )

    console.info(table)


@click.command("ps")
@click.argument("pod_id", required=False)
@click.option("--details", "-d", is_flag=True, help="Show detailed information including Jupyter URLs")
@handle_errors
def ps_command(pod_id: Optional[str], details: bool):
    """\b
    List active GPU pods.
    POD_ID: Optional specific pod ID/name to show details for
    \b
    Examples:
      lium ps                # Show all active pods
      lium ps eager-wolf-aa  # Show specific pod details
      lium ps --details      # Show all pods with detailed info
    """
    ensure_config()

    with loading_status("Loading pods", ""):
        pods = Lium().ps()
    
    if pod_id:
        # Filter for specific pod
        pod = next((p for p in pods if p.id == pod_id or p.huid == pod_id or p.name == pod_id), None)
        if pod:
            show_pods([pod])
            # Show Jupyter URL if available and details flag or specific pod
            if hasattr(pod, 'jupyter_url') and pod.jupyter_url:
                console.info(f"\nJupyter URL: {pod.jupyter_url}")
        else:
            console.error(f"Pod '{pod_id}' not found")
    else:
        show_pods(pods)

        # Show Jupyter URLs for all pods if details flag is set
        if details:
            jupyter_pods = [p for p in pods if hasattr(p, 'jupyter_url') and p.jupyter_url]
            if jupyter_pods:
                console.info("\nJupyter URLs:")
                for pod in jupyter_pods:
                    console.info(f"  {console.get_styled(pod.huid, 'pod_id')}: {pod.jupyter_url}")