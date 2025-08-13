"""List templates command."""

import os
import sys
from typing import List, Optional

import click
from rich.table import Table
from rich.text import Text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lium_sdk import Lium, Template
from ..utils import console, handle_errors, loading_status




def _status_icon(status: Optional[str]) -> str:
    """Convert status to icon."""
    if status == 'VERIFY_SUCCESS':
        return console.get_styled("✓", 'success')
    elif status == 'VERIFY_FAILED':
        return console.get_styled("✗", 'error')
    else:
        return console.get_styled("?", 'dim')


def show_templates(templates: List[Template], numbered: bool = False) -> None:
    """Display templates in a tight, well-engineered table."""
    if not templates:
        console.warning("No templates available.")
        return

    # Title
    console.info(Text("Templates", style="bold"), end="")
    console.dim(f"  ({len(templates)} shown)")

    table = Table(
        show_header=True,
        header_style="dim",
        box=None,        # no ASCII borders
        pad_edge=False,
        expand=True,     # full terminal width
        padding=(0, 1),  # (vertical, horizontal) — keep it tight
    )

    # Add columns with fixed or ratio widths
    if numbered:
        table.add_column("", justify="right", width=3, no_wrap=True, style="dim")
    
    table.add_column("Name", justify="left", ratio=3, min_width=20, overflow="fold")
    table.add_column("Image", justify="left", ratio=4, min_width=25, overflow="fold")
    table.add_column("Tag", justify="left", ratio=3, min_width=20, overflow="fold")
    table.add_column("Type", justify="left", width=10, no_wrap=True)
    table.add_column("Status", justify="center", width=6, no_wrap=True)

    for i, t in enumerate(templates, 1):
        row = [
            t.name or '—',
            console.get_styled(f"{t.docker_image or '—'}", 'id'),
            t.docker_image_tag or "latest",
            t.category.upper() if t.category else "—",
            _status_icon(t.status),
        ]

        if numbered:
            row.insert(0, str(i))

        table.add_row(*row)
    
    console.info(table)


@click.command("templates")
@click.argument("search", required=False)
@handle_errors
def templates_command(search: Optional[str]):
    """List available Docker templates and images.
    
    \b
    SEARCH: Optional search text to filter by name or docker image
    
    \b
    Examples:
      lium templates            # Show all templates
      lium templates pytorch    # Filter by 'pytorch' in name/image
      lium templates ubuntu     # Filter by 'ubuntu' in name/image
    """
    with loading_status("Loading templates", "Templates loaded"):
        templates = Lium().templates(search)

    show_templates(templates)