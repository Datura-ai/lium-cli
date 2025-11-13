"""Display formatting logic for schedules command."""

from datetime import datetime, timezone
from typing import List
from rich.table import Table

from cli.lium_sdk import PodInfo
from cli.utils import console, mid_ellipsize


def format_header(count: int) -> str:
    """Format header text for schedules list."""
    return f"Scheduled Terminations  ({count} total)"


def format_tip() -> str:
    """Format tip message."""
    return f"Tip: {console.get_styled('lium schedules rm <index>', 'success')} {console.get_styled('# cancel scheduled termination', 'dim')}"


def build_schedules_table(pods: List[PodInfo]) -> tuple[Table | None, str, str]:
    """Build schedules table, returns (table, header, tip)."""

    # Filter to only pods with scheduled terminations
    scheduled_pods = [pod for pod in pods if getattr(pod, 'removal_scheduled_at', None)]

    if not scheduled_pods:
        return None, "", ""

    table = Table(
        show_header=True,
        header_style="dim",
        box=None,
        pad_edge=False,
        expand=True,
        padding=(0, 1),
    )

    # Add columns
    table.add_column("", justify="right", width=3, no_wrap=True, style="dim")
    table.add_column("Pod ID", justify="left", ratio=3, min_width=20, overflow="fold")
    table.add_column("Status", justify="left", width=12, no_wrap=True)
    table.add_column("Scheduled At", justify="left", ratio=2, min_width=18, no_wrap=True)
    table.add_column("Time Until", justify="right", width=12, no_wrap=True)

    for idx, pod in enumerate(scheduled_pods, 1):
        removal_scheduled_at = getattr(pod, 'removal_scheduled_at', None)

        # Format scheduled time
        try:
            if removal_scheduled_at.endswith('Z'):
                scheduled_time = datetime.fromisoformat(removal_scheduled_at.replace('Z', '+00:00'))
            else:
                scheduled_time = datetime.fromisoformat(removal_scheduled_at).replace(tzinfo=timezone.utc)

            local_time = scheduled_time.astimezone()
            scheduled_str = local_time.strftime("%b %d at %I:%M %p")
            time_delta = scheduled_time - datetime.now(timezone.utc)
            hours_until = time_delta.total_seconds() / 3600

            if hours_until > 24:
                time_until = f"{hours_until / 24:.1f}d"
            elif hours_until > 0:
                time_until = f"{hours_until:.1f}h"
            else:
                time_until = console.get_styled("overdue", 'warning')
        except Exception:
            scheduled_str = removal_scheduled_at
            time_until = "—"

        table.add_row(
            str(idx),
            console.get_styled(mid_ellipsize(pod.huid), 'id'),
            console.get_styled(pod.status, 'info'),
            scheduled_str,
            time_until,
        )

    header = format_header(len(scheduled_pods))
    tip = format_tip()

    return table, header, tip
