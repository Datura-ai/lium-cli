"""List executors command using Lium SDK."""
import click
from typing import List, Optional
from rich.console import Console
from rich.table import Table

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, ExecutorInfo
from ..utils import console, handle_errors, loading_status


def show_executors(executors: List[ExecutorInfo], numbered: bool = False) -> None:
    """Display executors in a clean table."""
    if not executors:
        console.print("[yellow]No executors available.[/yellow]")
        return

    table = Table(title="Available GPU Executors")
    
    if numbered:
        table.add_column("#", style="dim", justify="right")
    
    table.add_column("Id", justify="left")
    table.add_column("GPU", style="cyan", no_wrap=True)
    table.add_column("Count", style="green", justify="right")
    table.add_column("Price/h", style="yellow", justify="right")
    table.add_column("Price/GPU", style="yellow", justify="right")
    table.add_column("Location", style="blue")

    for i, executor in enumerate(executors, 1):
        row = [
            executor.huid,
            executor.gpu_type,
            str(executor.gpu_count),
            f"${executor.price_per_hour:.2f}",
            f"${executor.price_per_gpu_hour:.2f}",
            executor.location.get('country', 'Unknown'),
        ]
        
        if numbered:
            row.insert(0, str(i))
            
        table.add_row(*row)
    
    console.print(table)
    console.print(f"[dim]Total: {len(executors)} executors[/dim]")


@click.command("ls")
@click.argument("gpu_type", required=False)
@handle_errors
def ls_command(gpu_type: Optional[str]):
    """List available GPU executors and their pricing.
    
    GPU_TYPE: Optional filter by GPU type (e.g., '4090', 'H100', 'A100')
    
    Examples:
      lium ls          # Show all executors
      lium ls H100     # Show only H100 executors
      lium ls 4090     # Show only RTX 4090 executors
    """
    with loading_status("Loading executors", "Executors loaded"):
        executors = Lium().ls(gpu_type=gpu_type)
    show_executors(executors)