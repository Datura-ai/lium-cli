"""List (ls) command implementation."""

from typing import Optional
import click

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors, store_executor_selection
from cli.completion import get_gpu_completions
from . import validation, display


@click.command("ls")
@click.argument("gpu_type", required=False, shell_complete=get_gpu_completions)
@click.option(
    "--sort",
    "sort_by",
    type=click.Choice(["price_gpu", "price_total", "loc", "id", "gpu"]),
    default="price_gpu",
    help="Sort result by the chosen field.",
)
@click.option("--limit", type=int, default=None, help="Limit number of rows shown.")
@handle_errors
def ls_command(gpu_type: Optional[str], sort_by: str, limit: Optional[int]):
    """List available GPU executors."""

    # Validate
    valid, error = validation.validate(sort_by, limit)
    if not valid:
        ui.error(error)
        return

    # Load data
    lium = Lium()
    executors = ui.load("Loading executors", lambda: lium.ls(gpu_type=gpu_type))

    # Check if empty
    if not executors:
        if gpu_type:
            ui.error(f"All {gpu_type} GPUs are currently rented out")
            ui.info(f"Tip: {ui.styled('lium ls', 'success')}")
        else:
            ui.error("All GPUs are currently rented out")
            ui.info("Check back later or contact support if this persists")
        return

    # Build table
    table, sorted_executors, header, tip = display.build_executors_table(
        executors,
        sort_by=sort_by,
        limit=limit
    )

    # Display
    ui.info(header)
    ui.print(table)
    ui.print("")
    ui.info(tip)

    # Store selection for index-based access in up command
    store_executor_selection(sorted_executors)
