"""Create pod command."""

import os
import sys
import json
from typing import Dict, List, Optional

import click
from rich.prompt import Confirm, Prompt
from rich.text import Text

from ..completion import get_gpu_completions

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lium_sdk import ExecutorInfo, Lium, Template
from ..utils import (
    calculate_pareto_frontier,
    console,
    get_pytorch_template_id,
    handle_errors,
    loading_status,
    parse_volume_spec,
    resolve_executor_indices,
    timed_step_status,
    wait_ready_no_timeout,
    ensure_config
)
from .ssh import get_ssh_method_and_pod, ssh_to_pod


def _apply_executor_filters(
    executors: List[ExecutorInfo],
    gpu_count: Optional[int] = None,
    country_code: Optional[str] = None,
    ports: Optional[int] = None
) -> List[ExecutorInfo]:
    """Apply filters to executor list."""
    if gpu_count:
        executors = [e for e in executors if e.gpu_count == gpu_count]
    if country_code:
        executors = [
            e for e in executors
            if e.location and e.location.get('country_code', '').upper() == country_code.upper()
        ]
    if ports:
        executors = [
            e for e in executors
            if e.available_port_count and e.available_port_count >= ports
        ]
    return executors


def _build_filter_description(
    gpu: Optional[str] = None,
    count: Optional[int] = None,
    country: Optional[str] = None,
    ports: Optional[int] = None
) -> str:
    """Build a description of active filters."""
    filters = []
    if gpu:
        filters.append(f"GPU type={gpu}")
    if count:
        filters.append(f"GPU count={count}")
    if country:
        filters.append(f"country={country}")
    if ports:
        filters.append(f"min ports={ports}")
    return ', '.join(filters)


def _get_executor_id(executor_id: str) -> Optional[str]:
    """Resolve executor ID from index or return as-is."""
    if executor_id and executor_id.isdigit():
        resolved_ids, error_msg = resolve_executor_indices([executor_id])
        if error_msg:
            console.error(error_msg)
            if not resolved_ids:
                return None
        if resolved_ids:
            return resolved_ids[0]
    return executor_id


def _find_executor_by_id(lium: Lium, executor_id: str, ports: Optional[int] = None) -> Optional[ExecutorInfo]:
    """Find executor by ID with retry logic."""
    original_id = executor_id
    
    with loading_status(f"Finding executor '{executor_id}'", ""):
        executor_id = _get_executor_id(executor_id)
        
        if executor_id is None:
            return None
            
        executor = lium.get_executor(executor_id)
        
        # Single retry if not found
        if executor is None:
            from .ls import ls_store_executor
            ls_store_executor()
            executor_id = _get_executor_id(original_id)
            if executor_id is None:
                return None
            executor = lium.get_executor(executor_id)
            if executor is None:
                console.error(f"No executor found with ID '{original_id}'")
                console.info(f"Tip: {console.get_styled('lium ls', 'success')}")
                return None

    # Validate port count if specified
    if ports:
        if not executor.available_port_count or executor.available_port_count < ports:
            available = executor.available_port_count or 0
            console.error(
                f"Executor {executor.huid} has insufficient ports "
                f"(available: {available}, required: {ports})"
            )
            return None

    return executor


def _auto_select_executor(
    lium: Lium,
    gpu: Optional[str] = None,
    count: Optional[int] = None,
    country: Optional[str] = None,
    ports: Optional[int] = None
) -> Optional[ExecutorInfo]:
    """Automatically select best executor based on filters."""
    from .ls import ls_store_executor

    with loading_status("Finding best executor", ""):
        executors = lium.ls(gpu_type=gpu)
        executors = _apply_executor_filters(executors, gpu_count=count, country_code=country, ports=ports)

        if not executors:
            if gpu is not None and gpu not in lium.gpu_types():
                console.error(f"GPU '{gpu}' Not recognized")
            else:
                filter_desc = _build_filter_description(gpu, count, country, ports)
                console.error(f"All matching GPUs are currently rented out. (filters: {filter_desc})")
            console.info(f"Tip: {console.get_styled('lium ls', 'success')}")
            return None

        # Store for potential index reference
        ls_store_executor(gpu_type=gpu)

        # Calculate Pareto frontier to get the best executors
        pareto_flags = calculate_pareto_frontier(executors)
        pareto_executors = [e for e, is_pareto in zip(executors, pareto_flags) if is_pareto]

        # Pick the best executor
        executor = pareto_executors[0] if pareto_executors else executors[0]

    console.success(
        f"Selected: {executor.huid} ({executor.gpu_count}×{executor.gpu_type}) "
        f"at ${executor.price_per_hour:.2f}/h"
    )
    return executor


def select_executor(
    gpu_type: Optional[str] = None,
    gpu_count: Optional[int] = None,
    country_code: Optional[str] = None,
    ports: Optional[int] = None
) -> Optional[ExecutorInfo]:
    """Interactive executor selection with optional filters."""
    from .ls import show_executors

    console.warning("Select executor:")

    lium = Lium()
    with loading_status("Loading Executors", "Executors loaded"):
        executors = lium.ls(gpu_type=gpu_type)

    executors = _apply_executor_filters(executors, gpu_count=gpu_count, country_code=country_code, ports=ports)

    if not executors:
        filter_desc = _build_filter_description(gpu_type, gpu_count, country_code, ports)
        if filter_desc:
            console.error(f"No executors available with filters: {filter_desc}")
        else:
            console.error("No executors available")
        return None

    showed_executors = show_executors(executors, limit=20)

    choice = Prompt.ask(
        "[cyan]Select executor by number[/cyan]",
        choices=[str(i) for i in range(1, len(showed_executors) + 1)],
        default="1"
    )

    chosen_executor = showed_executors[int(choice) - 1]
    console.success(f"Selected: {chosen_executor.huid}")
    return chosen_executor


def select_template(filter_text: Optional[str] = None) -> Optional[Template]:
    """Interactive template selection."""
    from .templates import show_templates
    
    console.warning("Select template:")
    
    lium = Lium()
    with loading_status("Loading Templates", "Templates loaded"):
        templates = lium.templates(filter_text)
    
    if not templates:
        console.error("No templates available")
        return None
    
    show_templates(templates, numbered=True)
    
    choice = Prompt.ask(
        "Select template by number or enter text to filter",
        default="1"
    )
    
    if not choice.isnumeric():
        return select_template(choice)
    
    chosen_template = templates[int(choice) - 1]
    text = Text(
        f"Selected: {chosen_template.docker_image}:{chosen_template.docker_image_tag}", 
        style="dim"
    )
    console.dim(text, markup=False, highlight=False)
    return chosen_template


def _schedule_termination_if_needed(lium: Lium, pod_id: str, termination_time) -> None:
    with loading_status("Scheduling termination", ""):
        termination_time_str = termination_time.isoformat()
        lium.schedule_termination(pod_id, termination_time_str)

    from datetime import datetime, timezone
    time_str = termination_time.strftime("%Y-%m-%d %H:%M UTC")
    time_delta = termination_time - datetime.now(timezone.utc)
    hours_until = time_delta.total_seconds() / 3600
    console.success(f"Scheduled termination at {time_str} ({hours_until:.1f}h from now)")


def _install_jupyter_if_needed(lium: Lium, pod_id: str, jupyter_port: Optional[int]) -> None:
    """Install Jupyter Notebook on pod if requested."""
    if not jupyter_port:
        return

    import time

    console.info(f"Installing Jupyter Notebook on port {jupyter_port}...")

    try:
        # Start installation
        lium.install_jupyter(pod_id, jupyter_port)

        # Poll for completion
        max_wait = 120  # 2 minutes
        wait_interval = 3  # Check every 3 seconds
        elapsed = 0

        with loading_status("Waiting for Jupyter installation to complete", ""):
            while elapsed < max_wait:
                time.sleep(wait_interval)
                elapsed += wait_interval

                all_pods = lium.ps()
                updated_pod = next((p for p in all_pods if p.id == pod_id or p.huid == pod_id or p.name == pod_id), None)

                if updated_pod and hasattr(updated_pod, 'jupyter_installation_status'):
                    if updated_pod.jupyter_installation_status == "SUCCESS":
                        break
                    elif updated_pod.jupyter_installation_status == "FAILED":
                        console.error("Jupyter installation failed")
                        return

        # Get final pod info
        all_pods = lium.ps()
        updated_pod = next((p for p in all_pods if p.id == pod_id or p.huid == pod_id or p.name == pod_id), None)

        # Display success and URL
        if updated_pod and hasattr(updated_pod, 'jupyter_url') and updated_pod.jupyter_url:
            console.success("Jupyter Notebook installed successfully!")
            console.info(f"Jupyter URL: {updated_pod.jupyter_url}")
        else:
            console.warning("Jupyter installation timed out. Run 'lium ps' to check status")

    except Exception as e:
        # Try to extract clean error message from API response
        error_msg = str(e)

        try:
            # Try to parse the error message as JSON
            error_json = json.loads(error_msg)
            if isinstance(error_json, dict) and 'message' in error_json:
                console.error(error_json['message'])
            else:
                console.error("Failed to install Jupyter Notebook. Ensure port is available on the pod")
        except (json.JSONDecodeError, TypeError):
            # Fallback to regex parsing if JSON parsing fails
            json_match = re.search(r'"message"\s*:\s*"([^"]+)"', error_msg)
            if json_match:
                clean_message = json_match.group(1)
                console.error(clean_message)
            else:
                # Fallback to generic message if we can't parse it
                console.error("Failed to install Jupyter Notebook. Ensure port is available on the pod")

        return


def _confirm_pod_creation(executor: ExecutorInfo, skip_confirm: bool = False) -> bool:
    """Confirm pod creation with user."""
    if skip_confirm:
        return True
    
    confirm_msg = (
        f"Acquire pod on {executor.huid} "
        f"({executor.gpu_count}×{executor.gpu_type}) "
        f"at ${executor.price_per_hour:.2f}/h?"
    )
    
    if not Confirm.ask(confirm_msg, default=False):
        console.warning("Cancelled")
        return False
    return True


def _create_and_connect_pod(
    lium: Lium,
    executor: ExecutorInfo,
    name: Optional[str],
    template_id: Optional[str],
    volume_id: Optional[str],
    volume_create_params: Optional[Dict[str, str]],
    interactive_mode: bool = False,
    initial_port_count: Optional[int] = None,
    termination_time = None,
    jupyter_port: Optional[int] = None
) -> None:
    """Create pod and connect via SSH."""
    # Set defaults
    if not name:
        name = executor.huid

    if interactive_mode:
        # Interactive mode with template selection
        template = None
        if template_id:
            template = lium.get_template(template_id)
        if not template:
            template = select_template()
            if not template:
                return

        # Create volume if needed
        if volume_create_params:
            with loading_status(f"Creating volume '{volume_create_params['name']}'", ""):
                new_volume = lium.volume_create(
                    name=volume_create_params['name'],
                    description=volume_create_params['description']
                )
                volume_id = new_volume.id
            console.success(f"Created volume: {new_volume.huid} ({new_volume.name})")

        # Create pod
        with loading_status(f"Creating pod {name}", ""):
            pod_info = lium.up(executor_id=executor.id, pod_name=name, template_id=template.id, volume_id=volume_id, initial_port_count=initial_port_count)

        # Wait for pod to be ready
        with loading_status("Waiting for pod to be ready..."):
            pod_id = pod_info.get('id') or pod_info.get('name', '')
            pod = wait_ready_no_timeout(lium, pod_id)

        # Schedule termination if requested
        if termination_time:
            _schedule_termination_if_needed(lium, pod_id, termination_time)

        # Install Jupyter if requested
        _install_jupyter_if_needed(lium, pod_id, jupyter_port)

        # Connect via SSH
        with loading_status("Connecting ssh"):
            ssh_cmd, pod = get_ssh_method_and_pod(name)
    else:
        # Auto mode with timed steps
        total_steps = 4 if volume_create_params else 3
        current_step = 1

        # Create volume if needed
        if volume_create_params:
            with timed_step_status(current_step, total_steps, "Creating volume"):
                new_volume = lium.volume_create(
                    name=volume_create_params['name'],
                    description=volume_create_params['description']
                )
                volume_id = new_volume.id
            current_step += 1

        with timed_step_status(current_step, total_steps, "Renting machine"):
            template = lium.get_template(get_pytorch_template_id())
            pod_info = lium.up(executor_id=executor.id, pod_name=name, template_id=template.id, volume_id=volume_id, initial_port_count=initial_port_count)

        with timed_step_status(current_step + 1, total_steps, "Loading image"):
            template = lium.default_docker_template(executor)
            if not template:
                template = lium.get_template(get_pytorch_template_id())
            pod_info = lium.up(executor_id=executor.id, pod_name=name, template_id=template.id)
            pod_id = pod_info.get('id') or pod_info.get('name', '')
            pod = wait_ready_no_timeout(lium, pod_id)

        # Schedule termination if requested
        if termination_time:
            _schedule_termination_if_needed(lium, pod_id, termination_time)

        # Install Jupyter if requested
        _install_jupyter_if_needed(lium, pod_id, jupyter_port)

        with timed_step_status(current_step + 2, total_steps, "Connecting ssh"):
            ssh_cmd, pod = get_ssh_method_and_pod(name)

    ssh_to_pod(ssh_cmd, pod)


@click.command("up")
@click.argument("executor_id", required=False)
@click.option("--name", "-n", help="Custom pod name")
@click.option("--template_id", "-t", help="Template ID")
@click.option("--volume", "-v", help="Volume spec: 'id:<HUID>' or 'new:name=<NAME>[,desc=<DESC>]'")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with template selection")
@click.option("--gpu", help="Filter executors by GPU type (e.g., H200, A6000)", shell_complete=get_gpu_completions)
@click.option("--count", "-c", type=int, help="Number of GPUs per pod")
@click.option("--country", help="Filter executors by ISO country code (e.g., US, FR)")
@click.option("--ports", "-p", type=int, help="Minimum number of available ports required")
@click.option("--ttl", help="Auto-terminate after duration (e.g., 6h, 45m, 2d)")
@click.option("--until", help="Auto-terminate at time in local timezone (e.g., 'today 23:00', 'tomorrow 01:00', '2025-10-20 15:30')")
@click.option("--jupyter", type=int, help="Install Jupyter Notebook on specified internal port")
@handle_errors
def up_command(
    executor_id: Optional[str],
    name: Optional[str],
    template_id: Optional[str],
    volume: Optional[str],
    yes: bool,
    interactive: bool,
    gpu: Optional[str],
    count: Optional[int],
    country: Optional[str],
    ports: Optional[int],
    ttl: Optional[str],
    until: Optional[str],
    jupyter: Optional[int]
):
    """\b
    Create a new GPU pod on an executor.
    \b
    EXECUTOR_ID: Executor UUID, HUID, or index from last 'lium ls'.
    If not provided, shows interactive selection.
    \b
    Examples:
      lium up                               # Interactive executor selection
      lium up cosmic-hawk-f2                # Create pod on specific executor
      lium up 1                             # Create pod on executor #1 from last ls
      lium up --name my-pod                 # Create with custom name
      lium up --gpu H200                    # Filter by GPU type
      lium up --gpu A6000 -c 2              # Filter by GPU type and count
      lium up --country US                  # Filter by country code
      lium up --gpu H200 --country FR       # Combine multiple filters
      lium up --ports 5             # Filter by minimum available ports + set this amount of ports on up.
      lium up 1 --volume id:brave-fox-3a    # Attach existing volume by HUID
      lium up 1 --volume new:name=my-data   # Create and attach new volume
      lium up 1 --volume new:name=my-data,desc="Training data"  # With description
      lium up 1 --ttl 6h                    # Auto-terminate after 6 hours
      lium up 1 --until "today 23:00"       # Auto-terminate at 23:00 local time today
      lium up 1 --until "tomorrow 01:00"    # Auto-terminate at 01:00 local time tomorrow
      lium up 1 --jupyter 8888              # Install Jupyter Notebook on port 8888
    """
    ensure_config()
    lium = Lium()

    # Validate TTL/until options (mutually exclusive)
    if ttl and until:
        console.error("Cannot specify both --ttl and --until")
        return

    # Parse TTL/until to get termination time
    termination_time = None
    if ttl:
        from .schedule import parse_duration
        from datetime import datetime, timezone
        duration = parse_duration(ttl)
        if not duration:
            console.error(f"Invalid TTL format: '{ttl}'. Use format like '6h', '45m', '2d'")
            return
        termination_time = datetime.now(timezone.utc) + duration

    if until:
        from .schedule import parse_time_spec
        termination_time = parse_time_spec(until)
        if not termination_time:
            # Check if it's a "today" time that has passed
            if until.strip().lower().startswith('today '):
                console.error(f"Time '{until}' has already passed today. Use 'tomorrow HH:MM' or a future time.")
            else:
                console.error(f"Invalid time format: '{until}'. Use 'today HH:MM', 'tomorrow HH:MM', or 'YYYY-MM-DD HH:MM'")
            return

        # Validate it's in the future
        from datetime import datetime, timezone
        if termination_time <= datetime.now(timezone.utc):
            console.error("Termination time must be in the future")
            return

    # Parse volume specification if provided
    volume_id = None
    volume_create_params = None
    if volume:
        vol_id, create_params, error_msg = parse_volume_spec(volume)
        if error_msg:
            console.error(error_msg)
            return

        # Store whether we need to create a volume or use existing
        if create_params:
            volume_create_params = create_params
        else:
            volume_id = vol_id

    # Resolve executor
    if executor_id:
        # Validate that filters aren't used with explicit executor ID
        if gpu or count or country:
            console.error("Cannot use filters (--gpu, --count, --country) when specifying an executor ID")
            return

        executor = _find_executor_by_id(lium, executor_id, ports=ports)
        if not executor:
            return
    else:
        # No executor provided - use filters or interactive selection
        if gpu or count or country:
            executor = _auto_select_executor(lium, gpu, count, country, ports)
        else:
            executor = select_executor(ports=ports)
        if not executor:
            return

    # Confirm creation
    if not _confirm_pod_creation(executor, skip_confirm=yes):
        return

    # Create pod and connect
    _create_and_connect_pod(lium, executor, name, template_id, volume_id, volume_create_params, interactive_mode=interactive, initial_port_count=ports, termination_time=termination_time, jupyter_port=jupyter)
