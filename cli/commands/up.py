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

def select_executor() -> Optional[ExecutorInfo]:
    """Interactive executor selection."""
    from .ls import show_executors
    
    console.warning("Select executor:")
    
    lium = Lium()
    with loading_status("Loading Executors", "Executors loaded"):
        executors = lium.ls()

    if not executors:
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
@click.option("--wait", "-w", is_flag=True, help="Wait for pod to be ready")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with template selection and confirmation prompts")
@handle_errors
def up_command(executor_id: Optional[str], name: Optional[str], template_id: Optional[str], wait: bool, yes: bool, interactive: Optional[bool]):
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
      lium up -w cosmic-hawk-f2     # Create and wait for pod to be ready
      lium up --name my-pod         # Create with custom name
    """
    lium = Lium()
    executor = None
    
    # Resolve executor (from ID, index, or interactive selection)
    if executor_id:
        original_executor_id = executor_id
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
                console.error(f"Executor '{executor_id}' not found")
                return
    else:
        # No executor provided - user needs to select
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

        # Wait for pod to be ready if requested
        if wait:
            with loading_status("Waiting for pod to be ready..."):
                pod_id = pod_info.get('id') or pod_info.get('name', '')
                pod = wait_ready_no_timeout(lium, pod_id)
            
            show_pod_created({"huid": pod.huid, "name": pod.name, "status": pod.status, "ssh_cmd": pod.ssh_cmd})
        else:
            show_pod_created(pod_info)
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
