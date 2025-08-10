"""List executors command using Lium SDK (btcli-style, long-by-default, fixed-width numerics)."""
from __future__ import annotations

import os
import sys
from typing import List, Optional, Callable, Any, Dict

import click
from rich.table import Table
from rich.text import Text

# Project imports (keep your relative path trick)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, ExecutorInfo  # type: ignore
from ..utils import console, handle_errors, loading_status, calculate_pareto_frontier  # type: ignore


# ───────────────────────────── helpers ───────────────────────────── #

def _mid_ellipsize(s: str, width: int = 28) -> str:
    if not s:
        return "—"
    if len(s) <= width:
        return s
    keep = width - 1
    left = keep // 2
    right = keep - left
    return f"{s[:left]}…{s[-right:]}"


def _cfg(exe: "ExecutorInfo") -> str:
    # 8×H100 (typographic ×)
    return f"{getattr(exe, 'gpu_count', '?')}×{getattr(exe, 'gpu_type', 'GPU')}"


def _country_name(loc: Optional[Dict]) -> str:
    if not loc:
        return "—"
    country = (loc.get("country") or "").strip()
    if country:
        return country
    code = (loc.get("country_code") or loc.get("iso_code") or "").strip()
    return code.upper() if code else "—"


def _money(v: Optional[float]) -> str:
    if v is None:
        return "—"
    # fixed width so decimals line up nicely
    return f"{v:>6.2f}"


def _intish(x: Any) -> Optional[int]:
    try:
        return int(float(x))
    except Exception:
        return None


def _maybe_int(x: Any) -> str:
    v = _intish(x)
    return f"{v}" if v is not None else "—"


def _maybe_gi_from_capacity(capacity: Any) -> str:
    """details[*].capacity appears to be MiB => Gi."""
    v = _intish(capacity)
    if v is None:
        return "—"
    gi = round(v / 1024)  # assume MiB -> Gi
    return f"{gi}"


def _maybe_gi_from_big_number(n: Any) -> str:
    """
    Heuristically convert big numbers (likely KiB) to Gi.
    RAM/hard_disk totals in sample look like KiB-scale ints.
    """
    v = _intish(n)
    if v is None:
        return "—"
    if v < 8192:  # already Gi-ish
        return f"{v}"
    gi = round(v / (1024 * 1024))
    return f"{gi}"


def _first_gpu_detail(specs: Optional[Dict]) -> Dict:
    if not specs:
        return {}
    gpu = specs.get("gpu") or {}
    details = gpu.get("details") or []
    return details[0] if details else {}


def _specs_row(specs: Optional[Dict]) -> Dict[str, str]:
    """
    Extract long-view fields from specs:
    VRAM (MiB→Gi), RAM (KiB→Gi), Disk (KiB→Gi), PCIe/mem/tflops from details[0],
    and Net ↑/Net ↓ from specs.network.
    """
    d = _first_gpu_detail(specs)
    vram = _maybe_gi_from_capacity(d.get("capacity"))

    ram_total = None
    disk_total = None
    net_up = None
    net_down = None
    if specs:
        ram_total = (specs.get("ram") or {}).get("total")
        disk_total = (specs.get("hard_disk") or {}).get("total")
        net = specs.get("network") or {}
        net_up = net.get("upload_speed")
        net_down = net.get("download_speed")

    return {
        "VRAM": vram,
        "RAM": _maybe_gi_from_big_number(ram_total),
        "Disk": _maybe_gi_from_big_number(disk_total),
        "PCIe": _maybe_int(d.get("pcie_speed")),
        "Mem": _maybe_int(d.get("memory_speed")),
        "TFLOPs": _maybe_int(d.get("graphics_speed")),
        "NetUp": _maybe_int(net_up),
        "NetDn": _maybe_int(net_down),
    }


def _sort_key_factory(name: str) -> Callable[[ExecutorInfo], Any]:
    def cc(e: ExecutorInfo) -> str:
        return _country_name(getattr(e, "location", None))
    mapping = {
        "price_gpu": lambda e: getattr(e, "price_per_gpu_hour", None) or 0.0,
        "price_total": lambda e: getattr(e, "price_per_hour", None) or 0.0,
        "loc": cc,
        "id": lambda e: getattr(e, "huid", "") or "",
        "gpu": lambda e: (getattr(e, "gpu_type", "") or "", getattr(e, "gpu_count", 0) or 0),
    }
    return mapping.get(name, mapping["price_gpu"])


# ───────────────────────────── columns ───────────────────────────── #

def _add_long_columns(t: Table) -> None:
    """
    Use fixed widths for all numeric columns to avoid airy gaps.
    Only Id and Location get ratios to absorb extra width.
    """
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


# ───────────────────────────── rendering ───────────────────────────── #

def show_executors(
    executors: List[ExecutorInfo],
    *,
    sort_by: str = "price_gpu",
    limit: Optional[int] = None,
    show_pareto: bool = True,
) -> None:
    if not executors:
        console.print("[yellow]No executors available.[/yellow]")
        return

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
    console.print(Text("Executors", style="bold"), end="")
    if show_pareto and pareto_count > 0:
        console.print(f"  [dim]({len(executors)} shown, [green]★ {pareto_count} optimal[/green])[/dim]")
    else:
        console.print(f"  [dim]({len(executors)} shown)[/dim]")

    table = Table(
        show_header=True,
        header_style="dim",
        box=None,        # no ASCII borders
        pad_edge=False,
        expand=True,     # full terminal width
        padding=(0, 1),  # (vertical, horizontal) — keep it tight
    )
    _add_long_columns(table)

    for exe, is_pareto in zip(executors, pareto_flags):
        loc = getattr(exe, "location", None)
        specs = getattr(exe, "specs", None)
        s = _specs_row(specs)
        
        # Add star for Pareto-optimal executors
        huid = _mid_ellipsize(getattr(exe, 'huid', '') or '')
        if is_pareto:
            huid_display = f"[green]★[/green] [cyan]{huid}[/]"
        else:
            huid_display = f"  [cyan]{huid}[/]"

        row = [
            huid_display,
            _cfg(exe),
            f"[green]{_money(getattr(exe, 'price_per_gpu_hour', None))}[/]",
            s["VRAM"],
            s["RAM"],
            s["Disk"],
            s["PCIe"],
            s["Mem"],
            s["TFLOPs"],
            s["NetUp"],
            s["NetDn"],
            _country_name(loc),
        ]
        table.add_row(*row)

    console.print(table)


# ───────────────────────────── command ───────────────────────────── #

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
    """
    List available GPU executors (long view by default).

    Examples:
      lium ls                 # Long, full-bleed list
      lium ls H100            # Filter by GPU type
      lium ls --sort loc      # Sort by location name
      lium ls --limit 20      # Show first 20 rows
    """
    with loading_status("Loading executors", "Executors loaded"):
        executors = Lium().ls(gpu_type=gpu_type)

    show_executors(executors, sort_by=sort_by, limit=limit)

