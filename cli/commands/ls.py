"""List executors command."""

import os
import sys
from typing import Any, Callable, Dict, List, Optional

import click
from rich.table import Table
from rich.text import Text

# Add parent directory to path for lium_sdk import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lium_sdk import ExecutorInfo, Lium
from ..utils import (calculate_pareto_frontier, console, handle_errors,
                     loading_status, store_executor_selection)


# Helper Functions

def _mid_ellipsize(s: str, width: int = 28) -> str:
    if not s:
        return "—"
    if len(s) <= width:
        return s
    keep = width - 1
    left = keep // 2
    right = keep - left
    return f"{s[:left]}…{s[-right:]}"


def _cfg(exe: ExecutorInfo) -> str:
    """Format GPU configuration string."""
    return f"{exe.gpu_count}×{exe.gpu_type}"


def _country_name(loc: Optional[Dict]) -> str:
    if not loc:
        return "—"
    country = (loc.get("country") or "").strip()
    if country:
        return country
    code = (loc.get("country_code") or loc.get("iso_code") or "").strip()
    return code.upper() if code else "—"


def _money(v: Optional[float]) -> str:
    """Format money value with fixed width."""
    return f"{v:>6.2f}" if v is not None else "—"


def _intish(x: Any) -> Optional[int]:
    """Convert to int safely."""
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def _maybe_int(x: Any) -> str:
    """Convert to int string or dash."""
    v = _intish(x)
    return str(v) if v is not None else "—"


def _maybe_gi_from_capacity(capacity: Any) -> str:
    """Convert MiB to GiB."""
    v = _intish(capacity)
    return str(round(v / 1024)) if v else "—"


def _maybe_gi_from_big_number(n: Any) -> str:
    """Convert KiB to GiB."""
    v = _intish(n)
    if v is None:
        return "—"
    if v < 8192:  # Already GiB
        return str(v)
    return str(round(v / (1024 * 1024)))


def _first_gpu_detail(specs: Optional[Dict]) -> Dict:
    """Get first GPU detail from specs."""
    if not specs:
        return {}
    gpu = specs.get("gpu", {})
    details = gpu.get("details", [])
    return details[0] if details else {}


def _specs_row(specs: Optional[Dict]) -> Dict[str, str]:
    """Extract display fields from specs."""
    if not specs:
        return {k: "—" for k in ["VRAM", "RAM", "Disk", "PCIe", "Mem", "TFLOPs", "NetUp", "NetDn"]}
    
    d = _first_gpu_detail(specs)
    ram = specs.get("ram", {})
    disk = specs.get("hard_disk", {})
    net = specs.get("network", {})
    
    return {
        "VRAM": _maybe_gi_from_capacity(d.get("capacity")),
        "RAM": _maybe_gi_from_big_number(ram.get("total")),
        "Disk": _maybe_gi_from_big_number(disk.get("total")),
        "PCIe": _maybe_int(d.get("pcie_speed")),
        "Mem": _maybe_int(d.get("memory_speed")),
        "TFLOPs": _maybe_int(d.get("graphics_speed")),
        "NetUp": _maybe_int(net.get("upload_speed")),
        "NetDn": _maybe_int(net.get("download_speed")),
    }


def _sort_key_factory(name: str) -> Callable[[ExecutorInfo], Any]:
    """Get sort key function by name."""
    mapping = {
        "price_gpu": lambda e: e.price_per_gpu_hour or 0.0,
        "price_total": lambda e: e.price_per_hour or 0.0,
        "loc": lambda e: _country_name(e.location),
        "id": lambda e: e.huid,
        "gpu": lambda e: (e.gpu_type, e.gpu_count),
    }
    return mapping.get(name, mapping["price_gpu"])


# Table Configuration

def _add_long_columns(t: Table) -> None:
    """
    Use fixed widths for all numeric columns to avoid airy gaps.
    Only Id and Location get ratios to absorb extra width.
    """
    # Index column for selection
    t.add_column("", justify="right", width=3, no_wrap=True, style="dim")
    # absorb width on the left with Id
    t.add_column("Id", justify="left", ratio=8, min_width=24, overflow="fold")
    t.add_column("Config", justify="left", width=12, no_wrap=True)          # e.g., 8×H100

    # fixed widths for numerics
    t.add_column("$/GPU·h", justify="right", width=8, no_wrap=True)
    t.add_column("VRAM",    justify="right", width=8, no_wrap=True)
    t.add_column("RAM",     justify="right", width=8, no_wrap=True)
    t.add_column("Disk",    justify="right", width=8, no_wrap=True)
    t.add_column("PCIe",    justify="right", width=8, no_wrap=True)
    t.add_column("Mem",     justify="right", width=8, no_wrap=True)
    t.add_column("TFLOPs",  justify="right", width=8, no_wrap=True)
    t.add_column("Net ↑",   justify="right", width=8, no_wrap=True)  # note the space
    t.add_column("Net ↓",   justify="right", width=8, no_wrap=True)

    # absorb remaining width on the right with Location
    t.add_column("Location", justify="left", ratio=4, min_width=10, overflow="fold")


# Display Functions

def show_executors(
    executors: List[ExecutorInfo],
    *,
    sort_by: str = "price_gpu",
    limit: Optional[int] = None,
    show_pareto: bool = True,
) -> List[ExecutorInfo]:
    if not executors:
        return []

    # Calculate Pareto frontier before sorting/limiting
    pareto_flags = calculate_pareto_frontier(executors) if show_pareto else [False] * len(executors)
    
    # Combine executors with their Pareto status for sorting
    executors_with_pareto = list(zip(executors, pareto_flags))
    
    # Sort with Pareto-optimal first, then by chosen criteria
    if show_pareto:
        executors_with_pareto = sorted(
            executors_with_pareto,
            key=lambda x: (not x[1], _sort_key_factory(sort_by)(x[0]))
        )
    else:
        executors_with_pareto = sorted(
            executors_with_pareto,
            key=lambda x: _sort_key_factory(sort_by)(x[0])
        )
    
    # Apply limit
    if isinstance(limit, int) and limit > 0:
        executors_with_pareto = executors_with_pareto[:limit]
    
    # Extract sorted executors and their Pareto flags
    executors = [e for e, _ in executors_with_pareto]
    pareto_flags = [p for _, p in executors_with_pareto]
    
    # Count Pareto-optimal in shown results
    pareto_count = sum(pareto_flags)

    # Title
    console.info(Text("Executors", style="bold"), end="")
    if show_pareto and pareto_count > 0:
        console.dim(f"  ({len(executors)} shown, ★ {pareto_count} optimal)")
    else:
        console.dim(f"  ({len(executors)} shown)")

    table = Table(
        show_header=True,
        header_style="dim",
        box=None,        # no ASCII borders
        pad_edge=False,
        expand=True,     # full terminal width
        padding=(0, 1),  # (vertical, horizontal) — keep it tight
    )
    _add_long_columns(table)

    for idx, (exe, is_pareto) in enumerate(zip(executors, pareto_flags), 1):
        s = _specs_row(exe.specs)
        
        # Format HUID with Pareto star
        huid = _mid_ellipsize(exe.huid)
        huid += " (DinD)" if exe.docker_in_docker else ""
        huid_display = f"{console.get_styled('★', 'success')} {console.get_styled(huid, 'id')}" if is_pareto else f"  {console.get_styled(huid, 'id')}"


        table.add_row(
            str(idx),
            huid_display,
            _cfg(exe),
            console.get_styled(_money(exe.price_per_gpu_hour), 'success'),
            s["VRAM"],
            s["RAM"],
            s["Disk"],
            s["PCIe"],
            s["Mem"],
            s["TFLOPs"],
            s["NetUp"],
            s["NetDn"],
            _country_name(exe.location),
        )

    console.info(table)
    
    # Add helpful tip with divider
    console.info("")
    console.info(f"Tip: {console.get_styled('lium up <index>', 'success')} {console.get_styled('# e.g. lium up 1', 'dim')}")
    
    return [exe for exe, _ in executors_with_pareto]  # Return sorted executors


# Utility Function

def ls_store_executor(gpu_type: Optional[str] = None,sort_by: str = "price_gpu") -> List[ExecutorInfo]:
    """Load and store executors without displaying them."""
    executors = Lium().ls(gpu_type=gpu_type)
    
    # Process executors similar to show_executors but without display
    if not executors:
        return []
    
    # Calculate Pareto frontier and sort (same logic as show_executors)
    pareto_flags = calculate_pareto_frontier(executors)
    executors_with_pareto = list(zip(executors, pareto_flags))
    
    # Sort with Pareto-optimal first, then by price_gpu
    executors_with_pareto = sorted(
        executors_with_pareto,
        key=lambda x: (not x[1], _sort_key_factory(sort_by)(x[0]))
    )
    
    # Extract sorted executors
    showed_executors = [e for e, _ in executors_with_pareto]
    
    # Store the selection for index-based access in up command
    store_executor_selection(showed_executors)
    
    return showed_executors


# Command Definition

@click.command("ls")
@click.argument("gpu_type", required=False)
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
    """\b
    List available GPU executors.
    \b
    Examples:
      lium ls                 # List all executors
      lium ls H100            # Filter by GPU type
      lium ls --sort loc      # Sort by location
      lium ls --limit 20      # Show first 20 rows
    """
    with loading_status("Loading executors", ""):
        executors = Lium().ls(gpu_type=gpu_type)

    if not executors:
        if gpu_type:
            console.error(f"All {gpu_type} GPUs are currently rented out.")
            console.info(f"Tip: {console.get_styled('lium ls', 'success')}")
        else:
            console.error("All GPUs are currently rented out.")
            console.info("Check back later or contact support if this persists.")
        return

    showed_executors = show_executors(executors, sort_by=sort_by, limit=limit)
    
    # Store the selection for index-based access in up command
    store_executor_selection(showed_executors)
