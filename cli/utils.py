"""CLI utilities and decorators."""
from functools import wraps
from contextlib import contextmanager
from typing import List, Dict, Any, Tuple, Optional
import json
from pathlib import Path
from cli.config import config
from datetime import datetime
from rich.status import Status
from lium_sdk import LiumError, ExecutorInfo, PodInfo,Lium
from .themed_console import ThemedConsole

console = ThemedConsole()


@contextmanager
def loading_status(message: str, success_message: str = ""):
    """Universal context manager to show loading status."""
    status = Status(f"{console.get_styled(message + '...', 'info')}", console=console)
    status.start()
    try:
        yield
        if success_message:
            console.success(f"✓ {success_message}")
    except Exception as e:
        console.error(f"✗ Failed: {e}")
        raise
    finally:
        status.stop()


def _update_spinner_display(step_prefix: str, message: str, start_time: float, running_flag):
    """Internal function to update spinner display with time."""
    import time
    import sys
    
    # Spinner characters (dots spinner)
    spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    spinner_index = 0
    
    # Get green color code from console theme
    green_color = console.theme.get('success', 'green')
    # Convert Rich color to ANSI escape sequence
    if green_color == 'green':
        green_code = '\033[32m'  # ANSI green
    else:
        green_code = '\033[32m'  # fallback to green
    reset_code = '\033[0m'  # ANSI reset
    
    while running_flag[0]:  # Use list for mutable reference
        elapsed = time.time() - start_time
        spinner_char = spinner_chars[spinner_index % len(spinner_chars)]
        
        # Use carriage return to overwrite the line smoothly with green spinner
        line = f"{step_prefix}{message}... {green_code}{spinner_char}{reset_code} ({elapsed:.1f}s)"
        sys.stdout.write(f"\r{line}")
        sys.stdout.flush()
        spinner_index += 1
        time.sleep(0.1)


def _handle_step_completion(step_prefix: str, message: str, elapsed: float, exception: Exception = None):
    """Internal function to handle step completion display."""
    import sys
    
    # Clear the line and print final result
    sys.stdout.write('\r\033[K')  # Clear entire line
    
    if exception is None:
        # Success case
        done_styled = console.get_styled("done", 'success')
        console.print(f"{step_prefix}{message}... {done_styled} ({elapsed:.1f}s)", highlight=False)
    else:
        # General failure case
        failed_styled = console.get_styled("failed", 'error')
        console.print(f"{step_prefix}{message}... {failed_styled} ({elapsed:.1f}s)", highlight=False)


@contextmanager
def timed_step_status(step: int = 0, total_steps: int = 0, message: str = ""):
    """Context manager to show timed step status like [1/3] Renting machine... ⠋ (3.2s) -> [1/3] Renting machine... done (3.2s)."""
    import time
    import threading
    import sys
    
    start_time = time.time()
    # Only show step prefix if steps > 0
    step_prefix = f"[{step}/{total_steps}] " if step > 0 and total_steps > 0 else ""
    running = [True]  # Use list for mutable reference
    
    # Hide cursor during animation
    sys.stdout.write('\033[?25l')  # Hide cursor
    sys.stdout.flush()
    
    # Start the update thread
    update_thread = threading.Thread(target=_update_spinner_display, args=(step_prefix, message, start_time, running), daemon=True)
    update_thread.start()
    
    try:
        yield
        # Stop the update and show success
        running[0] = False
        update_thread.join(timeout=0.1)
        
        # Show cursor again
        sys.stdout.write('\033[?25h')  # Show cursor
        
        elapsed = time.time() - start_time
        _handle_step_completion(step_prefix, message, elapsed)
        
    except Exception as e:
        # Stop the update and show appropriate message
        running[0] = False
        update_thread.join(timeout=0.1)
        
        # Show cursor again
        sys.stdout.write('\033[?25h')  # Show cursor
        
        elapsed = time.time() - start_time
        _handle_step_completion(step_prefix, message, elapsed, e)
        raise


def handle_errors(func):
    """Decorator to handle CLI errors gracefully."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            # Check if it's the API key error from SDK
            if "No API key found" in str(e):
                console.error("No API key configured")
                console.warning("Please run 'lium init' to set up your API key")
                console.dim("Or set LIUM_API_KEY environment variable")
            else:
                console.error(f"Error: {e}")
        except LiumError as e:
            console.error(f"Error: {e}")
        except Exception as e:
            console.error(f"Unexpected error: {e}")
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
    
    # Location preference (US gets a bonus)
    location = executor.location or {}
    country = location.get("country", "").upper()
    country_code = location.get("country_code", "").upper()
    is_us = country == "UNITED STATES" or country_code == "US"
    
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
        'location_score': 1.0 if is_us else 0.0,  # US locations get higher score
        'total_bandwidth': network.get("upload_speed", 0) + network.get("download_speed", 0),  # Combined bandwidth
    }


def dominates(metrics_a: Dict[str, float], metrics_b: Dict[str, float]) -> bool:
    """Check if executor A dominates executor B in Pareto sense."""
    # Metrics to minimize (lower is better)
    minimize_metrics = {'price_per_gpu_hour'}
    
    # Priority metrics when prices are equal
    priority_metrics = ['total_bandwidth', 'location_score', 'net_down', 'net_up']
    
    price_a = metrics_a.get('price_per_gpu_hour', float('inf'))
    price_b = metrics_b.get('price_per_gpu_hour', float('inf'))
    
    # Special handling when prices are equal (common with GPU filtering)
    if abs(price_a - price_b) < 0.01:  # Prices are effectively equal
        # Compare based on priority metrics
        for metric in priority_metrics:
            val_a = metrics_a.get(metric, 0) or 0
            val_b = metrics_b.get(metric, 0) or 0
            
            # Significant difference threshold (10% for bandwidth, any diff for location)
            threshold = 0.1 * max(val_a, val_b) if metric != 'location_score' else 0
            
            if val_a > val_b + threshold:
                # A is significantly better in this priority metric
                return True
            elif val_b > val_a + threshold:
                # B is significantly better in this priority metric
                return False
        
        # If all priority metrics are similar, compare all metrics
        at_least_one_better = False
        for metric in metrics_a:
            if metric in priority_metrics:
                continue  # Already checked
            
            val_a = metrics_a[metric] or 0
            val_b = metrics_b.get(metric, 0) or 0
            
            if val_a > val_b:
                at_least_one_better = True
            elif val_a < val_b:
                return False
        
        return at_least_one_better
    
    # Standard Pareto domination when prices differ
    at_least_one_better = False
    
    for metric in metrics_a:
        val_a = metrics_a[metric] or 0
        val_b = metrics_b.get(metric, 0) or 0

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


def store_executor_selection(executors: List[ExecutorInfo]) -> None:
    """Store the last executor selection for index-based selection."""
    from .config import config
    
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
    config_file = config.config_dir / "last_selection.json"
    with open(config_file, 'w') as f:
        json.dump(selection_data, f, indent=2)


def get_last_executor_selection() -> Optional[Dict[str, Any]]:
    """Retrieve the last executor selection."""
    from .config import config
    
    config_file = config.config_dir / "last_selection.json"
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
        return [], None
    
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
                failed_resolutions.append(f"Index {index_str} is out of range (1..{len(executors)}). Try: lium ls")
        except ValueError:
            failed_resolutions.append(f"{index_str} (not a valid index)")
    
    error_msg = None
    if failed_resolutions:
        error_msg = f"Could not resolve indices: {', '.join(failed_resolutions)}"
    
    return resolved_ids, error_msg


def parse_targets(targets: str, all_pods: List[PodInfo]) -> List[PodInfo]:
    """Parse target specification and return matching pods."""
    if targets.lower() == "all":
        return all_pods
    
    selected = []
    for target in targets.split(","):
        target = target.strip()
        
        # Try as index (1-based from ps output)
        try:
            idx = int(target) - 1
            if 0 <= idx < len(all_pods):
                selected.append(all_pods[idx])
                continue
        except ValueError:
            pass
        
        # Try as pod ID/name/huid
        for pod in all_pods:
            if target in (pod.id, pod.name, pod.huid):
                selected.append(pod)
                break
    
    return selected


def wait_ready_no_timeout(lium_client, pod_id: str):
    """Wait indefinitely for pod to be ready (RUNNING with SSH)."""
    import time
    
    while True:
        fresh_pods = lium_client.ps()
        pod = next((p for p in fresh_pods if p.id == pod_id), None)
        
        if pod and pod.status.upper() == "RUNNING" and pod.ssh_cmd:
            return pod
        
        time.sleep(10)  # Check every 10 seconds


def get_pytorch_template_id() -> Optional[str]:
    """Get the template ID for the newest PyTorch template."""
    
    lium = Lium()
    templates = lium.templates()

    if config.default_template_id in {t.id for t in templates}:
        return config.default_template_id
    
    # Filter PyTorch templates from daturaai/pytorch
    pytorch_templates = [
        t for t in templates 
        if t.category.upper() == "PYTORCH" 
        and t.docker_image == "daturaai/pytorch"
        and t.name.startswith("Pytorch (Cuda)")
    ]
    
    if not pytorch_templates:
        return None
    
    # Sort by PyTorch version (extract version from tag)
    def extract_pytorch_version(template):
        tag = template.docker_image_tag
        # Extract version like "2.6.0" from "2.6.0-py3.11-cuda12.5.1-devel-ubuntu24.04"
        version_part = tag.split('-')[0]
        try:
            # Split version into major.minor.patch for proper sorting
            parts = [int(x) for x in version_part.split('.')]
            return tuple(parts)
        except:
            return (0, 0, 0)

    # Get the template with highest version
    newest_template = max(pytorch_templates, key=extract_pytorch_version)
    return newest_template.id


def ensure_config():
    from .commands.init import setup_api_key, setup_ssh_key
    from .config import config

    if not config.get('api.api_key'):
        # Setup API key
        setup_api_key()

    if not config.get('ssh.key_path'):
        # Setup SSH key
        setup_ssh_key()