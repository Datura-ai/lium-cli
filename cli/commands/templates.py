"""List templates command using Lium SDK."""
import os
import sys
from typing import List, Optional, Dict, Any

import click
from rich.table import Table

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, Template
from ..utils import console, handle_errors, loading_status


def show_templates(templates: List[Template], numbered: bool = False) -> None:
    """Display templates in a clean table."""
    if not templates:
        console.print("[yellow]No templates available.[/yellow]")
        return

    table = Table(title="Available Templates")

    if numbered:
        table.add_column("#", style="dim", justify="right")

    table.add_column("Id", style="dim", justify="left", max_width=20, no_wrap=True, overflow="ellipsis")
    table.add_column("Name", style="cyan", justify="left", max_width=20, no_wrap=True, overflow="ellipsis")
    table.add_column("Image", style="green", justify="left", max_width=20, no_wrap=True, overflow="ellipsis")
    table.add_column("Tag", style="yellow", justify="left", max_width=15, no_wrap=True, overflow="ellipsis")
    table.add_column("Type", style="blue", justify="left", no_wrap=True, overflow="ellipsis")
    table.add_column("S", style="magenta", justify="center", no_wrap=True, overflow="ellipsis")

    for i, t in enumerate(templates, 1):
        status = t.status
        if status == 'VERIFY_SUCCESS':
            status = "✓"
        elif status == 'VERIFY_FAILED':  
            status = "✗"
        else:
            status = "?"
            
        row = [
            t.huid,
            t.name,
            t.docker_image,
            t.docker_image_tag,
            t.category,
            status,
        ]

        if numbered:
            row.insert(0, str(i))

        table.add_row(*row)
    
    console.print(table)
    console.print(f"[dim]Total: {len(templates)} templates[/dim]")


@click.command("templates")
@click.argument("search", required=False)
@handle_errors
def templates_command(search: Optional[str]):
    """List available Docker templates and images.
    
    SEARCH: Optional search text to filter by name or docker image
    
    Examples:
      lium templates            # Show all templates
      lium templates pytorch    # Filter by 'pytorch' in name/image
      lium templates ubuntu     # Filter by 'ubuntu' in name/image
    """
    with loading_status("Loading templates", "Templates loaded"):
        templates = Lium().templates(search)

    show_templates(templates)