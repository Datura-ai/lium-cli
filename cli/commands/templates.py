"""List templates command using Lium SDK (tight table design)."""
from __future__ import annotations

import os
import sys
from typing import List, Optional, Dict, Any

import click
from rich.table import Table
from rich.text import Text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, Template
from ..utils import console, handle_errors, loading_status


def _mid_ellipsize(s: str, width: int = 20) -> str:
    """Middle-ellipsize strings that are too long."""
    if not s:
        return "—"
    if len(s) <= width:
        return s
    keep = width - 1
    left = keep // 2
    right = keep - left
    return f"{s[:left]}…{s[-right:]}"


def _status_icon(status: Optional[str]) -> str:
    """Convert status to icon."""
    if status == 'VERIFY_SUCCESS':
        return "[green]✓[/]"
    elif status == 'VERIFY_FAILED':
        return "[red]✗[/]"
    else:
        return "[dim]?[/]"


def show_templates(templates: List[Template], numbered: bool = False) -> None:
    """Display templates in a tight, well-engineered table."""
    if not templates:
        console.print("[yellow]No templates available.[/yellow]")
        return

    # Title
    console.print(Text("Templates", style="bold"), end="")
    console.print(f"  [dim]({len(templates)} shown)[/dim]")

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
        table.add_column("#", justify="right", width=3, no_wrap=True)
    
    table.add_column("Name", justify="left", ratio=3, min_width=20, overflow="fold")
    table.add_column("Image", justify="left", ratio=4, min_width=25, overflow="fold")
    table.add_column("Tag", justify="left", width=12, no_wrap=True)
    table.add_column("Type", justify="left", width=10, no_wrap=True)
    table.add_column("S", justify="center", width=3, no_wrap=True)
    table.add_column("Id", justify="left", ratio=2, min_width=15, overflow="fold")

    for i, t in enumerate(templates, 1):
        row = [
            f"[cyan]{t.name or '—'}[/]",
            f"[blue]{t.docker_image or '—'}[/]",
            t.docker_image_tag or "latest",
            t.category or "—",
            _status_icon(t.status),
            f"[dim]{_mid_ellipsize(t.huid or '', 20)}[/]",
        ]

        if numbered:
            row.insert(0, f"[dim]{i}[/]")

        table.add_row(*row)
    
    console.print(table)


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