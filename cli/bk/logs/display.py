"""Display formatting for bk logs command."""

from datetime import datetime
from rich.table import Table

from cli.utils import console


def format_logs_table(logs: list) -> Table:
    """Format logs as a table."""
    table = Table(
        show_header=True,
        header_style="dim",
        box=None,
        padding=(0, 2)
    )

    table.add_column("#", style="dim")
    table.add_column("Backup ID", style="cyan")
    table.add_column("Status")
    table.add_column("Created")
    table.add_column("Size", justify="right")

    for idx, log in enumerate(logs, 1):
        backup_id_full = getattr(log, 'id', 'unknown')
        status = getattr(log, 'status', 'Unknown')

        # Color status
        if status.upper() == 'COMPLETED':
            status = f"[green]{status}[/green]"
        elif status.upper() in ['FAILED', 'ERROR']:
            status = f"[red]{status}[/red]"
        else:
            status = f"[yellow]{status}[/yellow]"

        created = getattr(log, 'created_at', 'Unknown')
        if created != 'Unknown':
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                created = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass

        size = ""
        if hasattr(log, 'size_bytes') and log.size_bytes:
            size_mb = log.size_bytes / (1024 * 1024)
            size = f"{size_mb:.1f} MB"

        table.add_row(
            str(idx),
            backup_id_full,
            status,
            created,
            size
        )

    return table


def format_single_backup(pod_name: str, log) -> str:
    """Format single backup details."""
    lines = [f"Pod: {pod_name}"]
    lines.append(f"Status: {getattr(log, 'status', 'Unknown')}")
    lines.append(f"Created: {getattr(log, 'created_at', 'Unknown')}")

    if hasattr(log, 'completed_at') and log.completed_at:
        lines.append(f"Completed: {log.completed_at}")

    if hasattr(log, 'size_bytes') and log.size_bytes:
        size_mb = log.size_bytes / (1024 * 1024)
        lines.append(f"Size: {size_mb:.2f} MB")

    if hasattr(log, 'error') and log.error:
        lines.append(f"Error: {log.error}")

    return "\n".join(lines)
