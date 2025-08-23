"""Create pod command."""

import os
import sys
from typing import Optional

import click
from rich.prompt import Confirm, Prompt
from rich.text import Text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lium_sdk import ExecutorInfo, Lium, Template
from ..utils import (console, handle_errors, loading_status, timed_step_status,
                     resolve_executor_indices, get_pytorch_template_id, wait_ready_no_timeout)
from .ssh import ssh_to_pod,get_ssh_method_and_pod

def select_executor(gpu_type: Optional[str] = None, gpu_count: Optional[int] = None, country_code: Optional[str] = None) -> Optional[ExecutorInfo]:
    """Interactive executor selection with filters."""
    from .ls import show_executors
    
    console.warning("Select executor:")
    
    lium = Lium()
    with loading_status("Loading Executors", "Executors loaded"):
        executors = lium.ls(gpu_type=gpu_type)
    
    # Apply additional filters
    if gpu_count:
        executors = [e for e in executors if e.gpu_count == gpu_count]
    
    if country_code:
        executors = [e for e in executors if e.location and e.location.get('country_code', '').upper() == country_code.upper()]

    if not executors:
        filters_desc = []
        if gpu_type:
            filters_desc.append(f"GPU type: {gpu_type}")
        if gpu_count:
            filters_desc.append(f"GPU count: {gpu_count}")
        if country_code:
            filters_desc.append(f"Country: {country_code}")
        
        if filters_desc:
            console.error(f"No executors available with filters: {', '.join(filters_desc)}")
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
    text = Text(f"Selected: {chosen_template.docker_image}:{chosen_template.docker_image_tag}", style="dim")
    console.dim(text, markup=False, highlight=False)
    return chosen_template

def show_pod_created(pod_info: dict) -> None:
    """Display created pod info."""
    pod_id = pod_info.get('huid', pod_info.get('id', pod_info.get('name', 'N/A')))
    console.success(f"✓ Pod '{pod_id}' created")
    
    if pod_info.get('ssh_cmd'):
        console.info(f"SSH: {pod_info['ssh_cmd']}")
    elif "ssh" in pod_info:
        console.info(f"SSH: {pod_info['ssh']}")
    
    console.dim("Use 'lium ps' to check status")

def _get_executor_id(executor_id):
    if executor_id and executor_id.isdigit():
        resolved_ids, error_msg = resolve_executor_indices([executor_id])
        if error_msg:
            console.error(f"{error_msg}")
            if not resolved_ids:
                return None
        if resolved_ids:
            executor_id = resolved_ids[0]
    return executor_id

@click.command("up")
@click.argument("executor_id", required=False)
@click.option("--name", "-n", help="Custom pod name")
@click.option("--template_id", "-t", help="Template ID")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with template selection and confirmation prompts")
@click.option("--gpu", help="Filter executors by GPU type (e.g., H200, A6000)")
@click.option("--count", "-c", type=int, help="Number of GPUs per pod")
@click.option("--country", help="Filter executors by ISO country code (e.g., US, FR)")
@handle_errors
def up_command(executor_id: Optional[str], name: Optional[str], template_id: Optional[str], yes: bool, interactive: Optional[bool], gpu: Optional[str], count: Optional[int], country: Optional[str]):
    """\b
    Create a new GPU pod on an executor.
    \b
    EXECUTOR_ID: Executor UUID, HUID, or index from last 'lium ls'. 
    If not provided, shows interactive selection.
    \b
    Examples:
      lium up                       # Interactive executor selection
      lium up cosmic-hawk-f2        # Create pod on specific executor
      lium up 1                     # Create pod on executor #1 from last ls
      lium up --name my-pod         # Create with custom name
      lium up --gpu H200            # Filter by GPU type
      lium up --gpu A6000 -c 2      # Filter by GPU type and count
      lium up --country US          # Filter by country code
      lium up --gpu H200 --country FR  # Combine multiple filters
    """
    lium = Lium()
    executor = None
    
    # Resolve executor (from ID, index, or interactive selection)
    if executor_id:
        # Validate that filters aren't used with explicit executor ID
        if gpu or count or country:
            console.error("Cannot use filters (--gpu, --count, --country) when specifying an executor ID")
            return
            
        original_executor_id = executor_id
        
        with loading_status(f"Finding executor '{executor_id}'", ""):
            executor_id = _get_executor_id(executor_id)
            
            if executor_id is None:  # Resolution failed (invalid index, etc.)
                return
                
            executor = lium.get_executor(executor_id)
            
            # Single retry if not found
            if executor is None:
                from .ls import ls_store_executor
                ls_store_executor()
                executor_id = _get_executor_id(original_executor_id)
                if executor_id is None:
                    return
                executor = lium.get_executor(executor_id)
                if executor is None:
                    console.error(f"No executor found with ID '{original_executor_id}'")
                    console.info(f"Tip: Run {console.get_styled('lium ls', 'success')} to see available executors.")
                    return
    else:
        # No explicit executor provided - either use filters or interactive selection
        if gpu or count or country:
            # Filters provided - automatically select the best executor
            from .ls import ls_store_executor
            
            with loading_status("Finding best executor", ""):
                # Get filtered executors
                executors = lium.ls(gpu_type=gpu)
                
                # Apply additional filters
                if count:
                    executors = [e for e in executors if e.gpu_count == count]
                
                if country:
                    executors = [e for e in executors if e.location and e.location.get('country_code', '').upper() == country.upper()]
                
                if not executors:
                    filters_desc = []
                    if gpu:
                        filters_desc.append(f"GPU type={gpu}")
                    if count:
                        filters_desc.append(f"GPU count={count}")
                    if country:
                        filters_desc.append(f"country={country}")
                    
                    console.error(f"All matching GPUs are currently rented out. (filters: {', '.join(filters_desc)})")
                    console.info( f"Tip: Run {console.get_styled('lium ls', 'success')} to see what's available now.")
                    return
                
                # Store for potential index reference
                ls_store_executor(gpu_type=gpu)
                
                # Calculate Pareto frontier to get the best executors
                from ..utils import calculate_pareto_frontier
                pareto_flags = calculate_pareto_frontier(executors)
                
                # Get Pareto-optimal executors, sorted by price
                pareto_executors = [e for e, is_pareto in zip(executors, pareto_flags) if is_pareto]
                if pareto_executors:
                    # Pick the first Pareto-optimal executor (best by our metrics)
                    executor = pareto_executors[0]
                else:
                    # Fallback to first executor if no Pareto-optimal found
                    executor = executors[0]
                
                executor_id = executor.id
            
            # Show which executor was selected
            console.success(f"Selected: {executor.huid} ({executor.gpu_count}×{executor.gpu_type}) at ${executor.price_per_hour:.2f}/h")
        else:
            # No filters - show interactive selection
            executor = select_executor()
            if not executor:
                return
            executor_id = executor.id
    # Interactive mode
    if interactive:
        # Get or select template
        template = None
        if template_id:
            template = lium.get_template(template_id)
        if not template:
            template = select_template()
            if not template:
                return

        if not name:
                name = executor.huid       
        # Confirm creation
        if not yes:
            confirm_msg = f"Acquire pod on {executor.huid} ({executor.gpu_count}×{executor.gpu_type}) at ${executor.price_per_hour:.2f}/h?"
            if not Confirm.ask(confirm_msg, default=False):
                console.warning("Cancelled")
                return
        
        with loading_status(f"Creating pod {name}", ""):
            pod_info = lium.up(executor_id=executor.id, pod_name=name, template_id=template.id)

        # Always wait for pod to be ready in interactive mode
        with loading_status("Waiting for pod to be ready..."):
            pod_id = pod_info.get('id') or pod_info.get('name', '')
            pod = wait_ready_no_timeout(lium, pod_id)
        
        # Connect via SSH
        with loading_status("Connecting ssh"):
            ssh_cmd, pod = get_ssh_method_and_pod(name)
        
        ssh_to_pod(ssh_cmd, pod)
    else:
        if not yes:
            confirm_msg = f"Acquire pod on {executor.huid} ({executor.gpu_count}×{executor.gpu_type}) at ${executor.price_per_hour:.2f}/h?"
            if not Confirm.ask(confirm_msg, default=False):
                console.warning("Cancelled")
                return
        # Auto logic with timed steps
        with timed_step_status(1, 3, "Renting machine"):
            # Select default PYTORCH tempalte 
            template = lium.get_template(get_pytorch_template_id())
            # Use executor HUID as default name
            if not name:
                name = executor.huid
            
            pod_info = lium.up(executor_id=executor.id, pod_name=name, template_id=template.id)
        
        # Wait for pod to be ready if requested
        with timed_step_status(2, 3, "Loading image"):
            pod_id = pod_info.get('id') or pod_info.get('name', '')
            pod = wait_ready_no_timeout(lium, pod_id)
        
        with timed_step_status(3, 3, "Connecting ssh"):
            ssh_cmd,pod = get_ssh_method_and_pod(name)
        
        ssh_to_pod(ssh_cmd,pod)
