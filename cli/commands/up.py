"""Create pod command using Lium SDK."""
import os
import sys
from typing import Optional

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, ExecutorInfo, Template
from ..utils import console, handle_errors, loading_status


def select_executor() -> Optional[ExecutorInfo]:
    """Interactive executor selection - reuse ls() + choose."""
    from rich.prompt import Prompt
    from .ls import show_executors
    
    console.print("[yellow]Select executor:[/yellow]")
    
    lium = Lium()
    search_text = None

    with loading_status("Loading Executors", "Executors loaded"):
        executors = lium.ls(gpu_type=search_text)

    if not executors:
        console.print(f"[red]No executors available{' for ' + search_text if search_text else ''}[/red]")
        return None

    # Reuse show_executors from ls command with numbers
    show_executors(executors, numbered=True)

    # Choose one
    choice = Prompt.ask(
        "[cyan]Select executor by number or executor[/cyan]",
        choices=[str(i) for i in range(1, len(executors) + 1)],
        default="1"
    )

    # Check if it's a number (executor selection)
    chosen_executor = executors[int(choice) - 1]
    console.print(f"[green]Selected: {chosen_executor.huid}[/green]")
    return chosen_executor


def select_template(filter: Optional[str] = None) -> Template:
    """request user to select a template interactively."""
    from rich.prompt import Prompt
    from .templates import show_templates

    console.print("[yellow]Select template:[/yellow]")

    lium = Lium()

    with loading_status("Loading Templates", "Templates loaded"):
        templates = lium.templates(filter)

    if not templates:
        console.print("[red]No templates available[/red]")
        return None

    # Show templates with numbers
    show_templates(templates, numbered=True)

    # Choose one
    choice = Prompt.ask(
        "Select template by number or ID or any word to filter templates",
        default="1"
    )
    if not choice.isnumeric():
        return select_template(choice)

    # Check if it's a number (template selection)
    chosen_template = templates[int(choice) - 1]
    # Use markup=False to prevent Rich from interpreting version numbers as color codes
    from rich.text import Text
    text = Text(f"Selected: {chosen_template.docker_image}:{chosen_template.docker_image_tag}", style="dim")
    console.print(text, markup=False, highlight=False)
    return chosen_template



def show_pod_created(pod_info: dict) -> None:
    """Display created pod info."""
    pod_id = pod_info.get('huid', pod_info.get('id', pod_info.get('name', 'N/A')))
    console.print(f"[green]✓[/green] Pod '{pod_id}' created")
    
    if pod_info.get('ssh_cmd'):
        console.print(f"SSH: {pod_info['ssh_cmd']}")
    elif "ssh" in pod_info:
        console.print(f"SSH: {pod_info['ssh']}")
    
    console.print("[dim]Use 'lium ps' to check status[/dim]")


@click.command("up")
@click.argument("executor_id", required=False)
@click.option("--name", "-n", help="Custom pod name")
@click.option("--template_id", "-t", help="Template ID")
@click.option("--wait", "-w", is_flag=True, help="Wait for pod to be ready")
@click.option("--timeout", default=300, help="Wait timeout in seconds (default: 300)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def up_command(executor_id: Optional[str], name: Optional[str], template_id: Optional[str], wait: bool, timeout: int, yes: bool):
    """Create a new GPU pod on an executor.
    
    EXECUTOR_ID: Executor UUID or HUID (from 'lium ls'). If not provided, 
    shows interactive selection.
    
    Examples:
      lium up                       # Interactive executor selection
      lium up cosmic-hawk-f2        # Create pod on specific executor
      lium up -w cosmic-hawk-f2     # Create and wait for pod to be ready
      lium up --name my-pod         # Create with custom name
    """
    lium = Lium()

    # get or select executor
    executor = None
    if executor_id:
        with loading_status("Loading executor", "Executor loaded"):
            executor = lium.get_executor(executor_id)
    if not executor:
        executor = select_executor()

    # Get template or auto-select
    template = None
    if template_id:
        template = lium.get_template(template_id)
    if not template:
        template = select_template()


    if not executor or not template:
        console.print("[red]No executor or template selected[/red]")
        sys.exit(1)

    # set name.
    if not name:
        # Use executor HUID as base name, similar to parent lium
        name = executor.huid

    # Show confirmation
    if not yes:
        from rich.prompt import Confirm
        confirm_msg = f"Acquire pod on {executor.huid} ({executor.gpu_count}×{executor.gpu_type}) at ${executor.price_per_hour:.2f}/h?"
        if not Confirm.ask(confirm_msg, default=False):
            console.print("[yellow]Cancelled[/yellow]")
            sys.exit(0)
    
    with loading_status(f"Creating pod {name}", ""):
        pod_info = lium.up(executor_id=executor.id, pod_name=name, template_id=template.id)

    # Wait for pod to be ready if requested
    if wait:
        console.print(f"[dim]Pod created. Waiting for pod to be ready (timeout: {timeout}s)...[/dim]")
        
        with console.status("[bold green]Waiting for pod..."):
            pod_id = pod_info.get('id') or pod_info.get('name', '')
            pod = lium.wait_ready(pod_id, timeout=timeout)
        
        if pod:
            show_pod_created({"huid": pod.huid, "name": pod.name, "status": pod.status, "ssh_cmd": pod.ssh_cmd})
        else:
            console.print(f"[yellow]⚠ Pod not ready after {timeout}s timeout[/yellow]")
            show_pod_created(pod_info)
    else:
        show_pod_created(pod_info)


if __name__ == "__main__":
    select_template()
