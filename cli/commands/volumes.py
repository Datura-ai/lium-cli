"""Volume management commands."""
from typing import List, Optional

import click
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

from cli.lium_sdk import Lium, VolumeInfo
from ..utils import console, handle_errors, loading_status, ensure_config, mid_ellipsize, format_date, store_volume_selection, get_last_volume_selection


# Helper Functions


def _format_size(size_gb: float) -> str:
    """Format size in GB with appropriate precision."""
    if size_gb is None or size_gb == 0:
        return "0"
    elif size_gb < 0.01:
        return f"{size_gb * 1024:.1f} MB"
    elif size_gb < 1:
        return f"{size_gb:.2f} GB"
    else:
        return f"{size_gb:.1f} GB"


def _format_file_count(count: int) -> str:
    """Format file count with K/M suffix if needed."""
    if count is None or count == 0:
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
    console.info(f"Tip: {console.get_styled('lium up <executor> --volume id:<HUID>', 'success')} {console.get_styled('# attach volume to pod', 'dim')}")


# Command Definitions

@click.command("list")
@handle_errors
def volumes_list_command():
    """\b
    List all volumes for the current user.

    Volumes are persistent storage that can be attached to pods.
    \b
    Examples:
      lium volumes list        # List all volumes
      lium volumes             # Same as list (default)
    """
    ensure_config()

    with loading_status("Loading volumes", ""):
        volumes = Lium().volumes()

    show_volumes(volumes)

    # Store volume selection for HUID-based lookup in other commands
    if volumes:
        store_volume_selection(volumes)


@click.command("new")
@click.argument("name")
@click.option("--desc", "-d", help="Volume description")
@handle_errors
def volumes_new_command(name: str, desc: Optional[str]):
    """\b
    Create a new volume.

    \b
    NAME: Volume name

    \b
    Examples:
      lium volumes new my-data                      # Create volume with name
      lium volumes new training-data --desc "ML datasets"  # With description
    """
    ensure_config()
    lium = Lium()

    description = desc or ""

    with loading_status(f"Creating volume '{name}'", ""):
        new_volume = lium.volume_create(name=name, description=description)

    console.success(f"Volume created: {new_volume.huid} ({new_volume.name})")


@click.command("rm")
@click.argument("indices")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def volumes_rm_command(indices: str, yes: bool):
    """\b
    Remove volumes by index from last 'lium volumes' list.

    \b
    INDICES: Volume index or comma-separated indices (1, 2, 3, or 1,2,3)

    \b
    Examples:
      lium volumes rm 1          # Remove volume #1
      lium volumes rm 1,2,3      # Remove volumes #1, #2, and #3
      lium volumes rm 2 --yes    # Remove without confirmation
    """
    ensure_config()
    lium = Lium()

    # Get cached volumes
    last_selection = get_last_volume_selection()
    if not last_selection:
        console.error("No volumes cached. Run 'lium volumes' first.")
        return

    volumes_data = last_selection.get('volumes', [])
    if not volumes_data:
        console.error("No volumes in cache. Run 'lium volumes' first.")
        return

    # Parse comma-separated indices
    index_list = [idx.strip() for idx in indices.split(',')]
    volumes_to_remove = []

    for index_str in index_list:
        try:
            idx = int(index_str)
            if idx < 1 or idx > len(volumes_data):
                console.error(f"Index {index_str} out of range (1..{len(volumes_data)})")
                console.info("Tip: Run 'lium volumes' to see available volumes")
                return
            volumes_to_remove.append((idx, volumes_data[idx - 1]))
        except ValueError:
            console.error(f"Invalid index: {index_str}. Must be a number.")
            return

    # Confirm deletion
    if not yes:
        if len(volumes_to_remove) == 1:
            volume_data = volumes_to_remove[0][1]
            display_name = f"{volume_data['huid']} ({volume_data['name']})" if volume_data['name'] else volume_data['huid']
            if not Confirm.ask(f"Remove volume {display_name}?"):
                console.warning("Cancelled")
                return
        else:
            console.info(f"Volumes to remove:")
            for idx, vol_data in volumes_to_remove:
                display_name = f"{vol_data['huid']} ({vol_data['name']})" if vol_data['name'] else vol_data['huid']
                console.info(f"  [{idx}] {display_name}")
            if not Confirm.ask(f"Remove {len(volumes_to_remove)} volumes?"):
                console.warning("Cancelled")
                return

    # Delete volumes
    for idx, volume_data in volumes_to_remove:
        volume_id = volume_data['id']
        volume_huid = volume_data['huid']

        with loading_status(f"Removing volume {volume_huid}", ""):
            lium.volume_delete(volume_id)

        console.success(f"Volume removed: {volume_huid}")

    if len(volumes_to_remove) > 1:
        console.success(f"Removed {len(volumes_to_remove)} volumes")


@click.group(invoke_without_command=True)
@click.pass_context
def volumes_command(ctx):
    """Manage persistent volumes.

    \b
    Commands:
      list - List all volumes (default)
      new  - Create a new volume
      rm   - Remove a volume
    """
    # If no subcommand is provided, default to list
    if ctx.invoked_subcommand is None:
        ctx.invoke(volumes_list_command)


# Add subcommands to the volumes group
volumes_command.add_command(volumes_list_command)
volumes_command.add_command(volumes_new_command)
volumes_command.add_command(volumes_rm_command)
