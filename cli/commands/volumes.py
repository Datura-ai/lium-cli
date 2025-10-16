"""List volumes command."""
from typing import List

import click
from rich.table import Table
from rich.text import Text

from lium_sdk import Lium, VolumeInfo
from ..utils import console, handle_errors, loading_status, ensure_config, mid_ellipsize, format_date


# Helper Functions


def _format_size(size_gb: float) -> str:
    """Format size in GB with appropriate precision."""
    if size_gb == 0:
        return "0"
    elif size_gb < 0.01:
        return f"{size_gb * 1024:.1f} MB"
    elif size_gb < 1:
        return f"{size_gb:.2f} GB"
    else:
        return f"{size_gb:.1f} GB"


def _format_file_count(count: int) -> str:
    """Format file count with K/M suffix if needed."""
    if count == 0:
        return "0"
    elif count < 1000:
        return str(count)
    elif count < 1000000:
        return f"{count / 1000:.1f}K"
    else:
        return f"{count / 1000000:.1f}M"


# Display Functions

def show_volumes(volumes: List[VolumeInfo]) -> None:
    """Display volumes in a clean table."""
    if not volumes:
        console.warning("No volumes found")
        console.info("")
        console.info(f"Tip: {console.get_styled('lium volume create <name>', 'success')} to create a new volume")
        return

    # Title
    console.info(Text("Volumes", style="bold"), end="")
    console.dim(f"  ({len(volumes)} total)")

    table = Table(
        show_header=True,
        header_style="dim",
        box=None,        # no ASCII borders
        pad_edge=False,
        expand=True,     # full terminal width
        padding=(0, 1),  # tight padding
    )

    # Add columns with fixed or ratio widths
    table.add_column("", justify="right", width=3, no_wrap=True, style="dim")  # Index
    table.add_column("ID", justify="left", ratio=3, min_width=20, overflow="fold")
    table.add_column("Name", justify="left", ratio=3, min_width=15, overflow="ellipsis")
    table.add_column("Size", justify="right", width=10, no_wrap=True)
    table.add_column("Files", justify="right", width=8, no_wrap=True)
    table.add_column("Description", justify="left", ratio=4, min_width=20, overflow="ellipsis")
    table.add_column("Created", justify="right", width=12, no_wrap=True)

    for idx, volume in enumerate(volumes, 1):
        table.add_row(
            str(idx),
            console.get_styled(mid_ellipsize(volume.huid), 'id'),
            console.get_styled(volume.name or "—", 'info'),
            _format_size(volume.current_size_gb),
            _format_file_count(volume.current_file_count),
            console.get_styled(volume.description or "—", 'dim'),
            format_date(volume.created_at),
        )

    console.info(table)
    console.info("")
    console.info(f"Tip: {console.get_styled('lium up <executor> --volume <index>', 'success')} {console.get_styled('# attach volume to pod', 'dim')}")


# Command Definition

@click.command("volumes")
@handle_errors
def volumes_command():
    """\b
    List all volumes for the current user.

    Volumes are persistent storage that can be attached to pods.
    \b
    Examples:
      lium volumes             # List all volumes
    """
    ensure_config()

    with loading_status("Loading volumes", ""):
        volumes = Lium().volumes()

    show_volumes(volumes)
