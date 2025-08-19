"""Create pod command."""

import os
import sys
from typing import Optional

import click
from rich.prompt import Confirm, Prompt
from rich.text import Text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lium_sdk import ExecutorInfo, Lium, Template
from ..utils import (console, handle_errors, loading_status,
                     resolve_executor_indices,get_pytorch_template_id)
from .ssh import ssh_command

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


@click.command("up")
@click.argument("executor_id", required=False)
@click.option("--name", "-n", help="Custom pod name")
@click.option("--template_id", "-t", help="Template ID")
@click.option("--wait", "-w", is_flag=True, help="Wait for pod to be ready")
@click.option("--timeout", default=300, help="Wait timeout in seconds (default: 300)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def up_command(executor_id: Optional[str], name: Optional[str], template_id: Optional[str], wait: bool, timeout: int, yes: bool):
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

    # Resolve executor ID if it's an index
    executor = None
    if executor_id and executor_id.isdigit():
        resolved_ids, error_msg = resolve_executor_indices([executor_id])
        if error_msg:
            console.error(f"{error_msg}")
            if not resolved_ids:
                return
        if resolved_ids:
            executor_id = resolved_ids[0]
    
    # Check if executor id is not empty if is user need to pick 
    if not executor_id:
        executor = select_executor()
        if not executor:
            return

    # Get or select template
    """
    template = None
    if template_id:
        template = lium.get_template(template_id)
    if not template:
        template = select_template()
        if not template:
            return
    """
    with loading_status("renting machine",""):
        # Select executor ID 
        executor = lium.get_executor(executor_id)
        # Select default PYTORCH tempalte 
        template = lium.get_template(get_pytorch_template_id())
        # Use executor HUID as default name
        if not name:
            name = executor.huid
        
        pod_info = lium.up(executor_id=executor.id, pod_name=name, template_id=template.id)
    # Wait for pod to be ready if requested
    with loading_status("loading image"):
        pod_id = pod_info.get('id') or pod_info.get('name', '')
        pod = lium.wait_ready(pod_id, timeout=timeout)       
        if pod:
            with loading_status("Making ssh connection", ""):
                ssh_command(name)
        else:
            console.warning(f"⚠ Pod not ready after {timeout}s timeout")
            show_pod_created(pod_info)
