"""CLI utilities and decorators."""
from functools import wraps
from contextlib import contextmanager
from typing import List, Dict, Any, Tuple
from rich.console import Console
from rich.status import Status
from lium_sdk import LiumError, ExecutorInfo

console = Console()


@contextmanager
def loading_status(message: str, success_message: str = ""):
    """Universal context manager to show loading status."""
    status = Status(f"[cyan]{message}...[/cyan]", console=console)
    status.start()
    try:
        yield
        if success_message:
            console.print(f"[green]✓[/green] {success_message}")
    except Exception as e:
        console.print(f"[red]✗ Failed: {e}[/red]")
        raise
    finally:
        status.stop()


def handle_errors(func):
    """Decorator to handle CLI errors gracefully."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except LiumError as e:
            console.print(f"[red]Error: {e}[/red]")
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
    return wrapper


def extract_executor_metrics(executor: ExecutorInfo) -> Dict[str, float]:
    """Extract relevant metrics from an executor for Pareto comparison."""
    specs = executor.specs or {}
    
    # GPU metrics
    gpu_info = specs.get("gpu", {})
    gpu_details = gpu_info.get("details", [{}])[0] if gpu_info.get("details") else {}
    
    # System metrics
    ram_data = specs.get("ram", {})
    disk_data = specs.get("hard_disk", {})
    network = specs.get("network", {})
    
    return {
        'price_per_gpu_hour': executor.price_per_gpu_hour or float('inf'),
        'vram_gb': (gpu_details.get("capacity", 0) / 1024) if gpu_details else 0,  # MiB to GB
        'ram_gb': (ram_data.get("total", 0) / (1024 * 1024)) if ram_data else 0,  # KB to GB
        'disk_gb': (disk_data.get("total", 0) / (1024 * 1024)) if disk_data else 0,  # KB to GB
        'pcie_speed': gpu_details.get("pcie_speed", 0),
        'memory_bandwidth': gpu_details.get("memory_speed", 0),
        'tflops': gpu_details.get("graphics_speed", 0),
        'net_up': network.get("upload_speed", 0),
        'net_down': network.get("download_speed", 0),
    }


def dominates(metrics_a: Dict[str, float], metrics_b: Dict[str, float]) -> bool:
    """Check if executor A dominates executor B in Pareto sense."""
    # Metrics to minimize (lower is better)
    minimize_metrics = {'price_per_gpu_hour'}
    
    at_least_one_better = False
    
    for metric in metrics_a:
        val_a = metrics_a[metric]
        val_b = metrics_b.get(metric, 0)
        
        if metric in minimize_metrics:
            # For minimize metrics, A is better if it's lower
            if val_a < val_b:
                at_least_one_better = True
            elif val_a > val_b:
                return False  # B is better in this metric
        else:
            # For maximize metrics, A is better if it's higher
            if val_a > val_b:
                at_least_one_better = True
            elif val_a < val_b:
                return False  # B is better in this metric
    
    return at_least_one_better


def calculate_pareto_frontier(executors: List[ExecutorInfo]) -> List[bool]:
    """Calculate which executors are on the Pareto frontier.
    
    Returns a list of booleans indicating if each executor is Pareto-optimal.
    """
    # Extract metrics for all executors
    metrics_list = [extract_executor_metrics(e) for e in executors]
    
    # Mark each executor as Pareto-optimal or not
    is_pareto = []
    for i, metrics_i in enumerate(metrics_list):
        dominated = False
        for j, metrics_j in enumerate(metrics_list):
            if i != j and dominates(metrics_j, metrics_i):
                dominated = True
                break
        is_pareto.append(not dominated)
    
    return is_pareto