"""Volumes new command."""

from typing import Optional
import click

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors, ensure_config
from .actions import CreateVolumeAction


@click.command("new")
@click.argument("name")
@click.option("--desc", "-d", help="Volume description")
@handle_errors
def volumes_new_command(name: str, desc: Optional[str]):
    """Create a new volume."""
    ensure_config()

    lium = Lium()
    ctx = {"lium": lium, "name": name, "description": desc or ""}

    action = CreateVolumeAction()
    result = ui.load(f"Creating volume '{name}'", lambda: action.execute(ctx))

    if not result.ok:
        ui.error(result.error)
