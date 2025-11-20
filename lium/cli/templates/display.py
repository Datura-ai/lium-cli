"""Templates display formatting."""

from typing import List
from rich.table import Table
from rich.text import Text

from lium.sdk import Template
from lium.cli import ui


def status_icon(status: str) -> str:
    if status == 'VERIFY_SUCCESS':
        return ui.styled("✓", 'success')
    elif status == 'VERIFY_FAILED':
        return ui.styled("✗", 'error')
    else:
        return ui.styled("?", 'dim')


def build_templates_table(templates: List[Template]) -> tuple[Table, str]:
    header = f"{Text('Templates', style='bold')}  ({len(templates)} shown)"

    table = Table(
        show_header=True,
        header_style="dim",
        box=None,
        pad_edge=False,
        expand=True,
        padding=(0, 1),
    )

    table.add_column("Name", justify="left", ratio=3, min_width=20, overflow="fold")
    table.add_column("Image", justify="left", ratio=4, min_width=25, overflow="fold")
    table.add_column("Tag", justify="left", ratio=3, min_width=20, overflow="fold")
    table.add_column("Type", justify="left", width=10, no_wrap=True)
    table.add_column("Status", justify="center", width=6, no_wrap=True)

    for t in templates:
        table.add_row(
            t.name or '—',
            ui.styled(f"{t.docker_image or '—'}", 'id'),
            t.docker_image_tag or "latest",
            t.category.upper() if t.category else "—",
            status_icon(t.status),
        )

    return table, header
