"""CLI utilities and decorators."""
from functools import wraps
from contextlib import contextmanager
from typing import List, Dict, Any, Tuple, Optional
import json
from pathlib import Path
from datetime import datetime
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
        except ValueError as e:
            # Check if it's the API key error from SDK
            if "No API key found" in str(e):
                console.print("[red]No API key configured[/red]")
                console.print("[yellow]Please run 'lium init' to set up your API key[/yellow]")
                console.print("[dim]Or set LIUM_API_KEY environment variable[/dim]")
            else:
                console.print(f"[red]Error: {e}[/red]")
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


def get_config_dir() -> Path:
    """Get the configuration directory for lium-cli."""
    config_dir = Path.home() / ".lium"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def store_executor_selection(executors: List[ExecutorInfo]) -> None:
    """Store the last executor selection for index-based selection."""
    selection_data = {
        'timestamp': datetime.now().isoformat(),
        'executors': []
    }
    
    for executor in executors:
        selection_data['executors'].append({
            'id': executor.id,
            'huid': executor.huid,
            'gpu_type': executor.gpu_type,
            'gpu_count': executor.gpu_count,
            'price_per_hour': executor.price_per_hour,
            'location': executor.location.get('country', 'Unknown') if executor.location else 'Unknown'
        })
    
    # Store in config directory
    config_file = get_config_dir() / "last_selection.json"
    with open(config_file, 'w') as f:
        json.dump(selection_data, f, indent=2)


def get_last_executor_selection() -> Optional[Dict[str, Any]]:
    """Retrieve the last executor selection."""
    config_file = get_config_dir() / "last_selection.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def resolve_executor_indices(indices: List[str]) -> Tuple[List[str], Optional[str]]:
    """
    Resolve executor indices from the last selection.
    Returns (resolved_executor_ids, error_message)
    """
    last_selection = get_last_executor_selection()
    if not last_selection:
        return [], "No previous executor selection found. Please run 'lium ls' first."
    
    executors = last_selection.get('executors', [])
    if not executors:
        return [], "No executors in last selection."
    
    resolved_ids = []
    failed_resolutions = []
    
    for index_str in indices:
        try:
            index = int(index_str)
            if 1 <= index <= len(executors):
                executor_data = executors[index - 1]
                resolved_ids.append(executor_data['id'])
            else:
                failed_resolutions.append(f"{index_str} (index out of range 1-{len(executors)})")
        except ValueError:
            failed_resolutions.append(f"{index_str} (not a valid index)")
    
    error_msg = None
    if failed_resolutions:
        error_msg = f"Could not resolve indices: {', '.join(failed_resolutions)}"
    
    return resolved_ids, error_msg