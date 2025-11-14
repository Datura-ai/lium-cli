"""List (ls) command implementation."""

from typing import Optional, List
import click

from cli.lium_sdk import Lium, ExecutorInfo
from cli import ui
from cli.utils import handle_errors, store_executor_selection, calculate_pareto_frontier
from cli.completion import get_gpu_completions
from . import validation, display
from .actions import GetExecutorsAction


def ls_store_executor(gpu_type: Optional[str] = None, sort_by: str = "price_gpu") -> List[ExecutorInfo]:
    """Load and store executors without displaying them."""
    lium = Lium()
    executors = lium.ls(gpu_type=gpu_type)

    if not executors:
        return []

    pareto_flags = calculate_pareto_frontier(executors)
    executors_with_pareto = list(zip(executors, pareto_flags))

    executors_with_pareto = sorted(
        executors_with_pareto,
        key=lambda x: (not x[1], x[0].price_per_gpu_hour or 0.0)
    )

    sorted_executors = [e for e, _ in executors_with_pareto]
    store_executor_selection(sorted_executors)

    return sorted_executors


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
    _, error = validation.validate(sort_by, limit)
    if error:
        ui.error(error)
        return

    # Load data
    lium = Lium()
    ctx = {"lium": lium, "gpu_type": gpu_type}

    action = GetExecutorsAction()
    result = ui.load("Loading executors", lambda: action.execute(ctx))

    if not result.ok:
        ui.error(result.error)
        return

    executors = result.data["executors"]

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
