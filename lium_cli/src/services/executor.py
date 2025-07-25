import time
from datetime import datetime
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.console import Group
from lium_cli.src.services.api import api_client
from lium_cli.src.styles import style_manager
from lium_cli.src.utils import pretty_minutes, pretty_seconds


def get_executors_and_print_table(count: int, machine_name: str) -> list[dict]:
    query_params = {
        'gpu_count_lte': count,
        'gpu_count_gte': count,
        'machine_names': machine_name
    }
    with style_manager.console.status("Fetching executors...", spinner="monkey") as status:
        executors = api_client.get("executors", params=query_params, require_auth=False)

    table = Table(title="Available Executors")
    table.add_column("ID", style="bold blue")
    table.add_column("Name", style="bold green")
    table.add_column("Count", style="bold red")
    table.add_column("Price Per Hour", style="bold yellow")
    table.add_column("Uptime", style="bold magenta")
    table.add_column("Down (Mbps)", style="bold cyan")
    table.add_column("Up (Mbps)", style="bold cyan")
    table.add_column("DinD Support", justify="center")

    sorted_executors = sorted(executors, key=lambda x: x["uptime_in_minutes"], reverse=True)
    for executor in sorted_executors[:5]:
        dind_support = executor.get("specs", {}).get("sysbox_runtime", False)
        dind_display = "[green]✅[/green]" if dind_support else "[red]❌[/red]"
        table.add_row(
            executor["id"],
            executor["machine_name"],
            f"{executor['specs']['gpu']['count']}",
            f"${executor['price_per_hour']}",
            pretty_minutes(executor['uptime_in_minutes']),
            f"{executor.get('specs', {}).get('network', {}).get('download_speed', 'N/A')}",
            f"{executor.get('specs', {}).get('network', {}).get('upload_speed', 'N/A')}",
            dind_display
        )

    style_manager.console.print(table)
    return sorted_executors


def render_rented_executor_table(executor_id: str, uptime_in_seconds: int) -> tuple[Table, dict]:
    table = Table(title="Rented Executor")
    table.add_column("ID", style="bold blue")
    table.add_column("Name", style="bold green")
    table.add_column("Status", style="bold red")
    table.add_column("Uptime", style="bold white")

    pod = api_client.get(f"pods/{executor_id}")
    status_color = {
        "RUNNING": "green",
        "STOPPED": "red",
        "FAILED": "red",
        "PENDING": "yellow"
    }.get(pod["status"], "white")
    
    table.add_row(
        pod["id"],
        pod["pod_name"], 
        f"[{status_color}]{pod['status']}[/{status_color}]",
        pretty_seconds(uptime_in_seconds)
    )
    return table, pod


def rent_executor(executor_id: str, docker_image: str | None, template_id: str | None, ssh_key_path: str | None, pod_name_override: str | None = None):
    """Rent an executor for a given docker image or template ID.
    
    Arguments:
        executor_id: The id of the executor to rent
        docker_image: The docker image to run (used if template_id is None, for template lookup by image name)
        template_id: The specific template ID to use. If provided, docker_image lookup is skipped.
        ssh_key_path: The path to the ssh key to use for the executor
        pod_name_override: Optional specific name for the pod.
    """
    style_manager.console.rule(f"[bold blue]Renting executor:[/bold blue] {executor_id}")
    
    actual_template_id = template_id

    if not actual_template_id and docker_image: # Only look up by docker_image if no template_id was given
        style_manager.console.print(f"[cyan]Attempting to find template by Docker image: {docker_image}[/cyan]")
        image_parts = docker_image.split(":")
        image_name = image_parts[0]
        tag = image_parts[1] if len(image_parts) > 1 else "latest"
        
        try:
            templates = api_client.get("templates")
            if not templates:
                style_manager.console.print("[bold red]Error:[/bold red] No templates found on the system to match against the Docker image.")
                return
            
            found_template = next((
                t for t in templates if t.get("docker_image") == image_name and t.get("docker_image_tag") == tag
            ), None)

            if not found_template:
                style_manager.console.print(f"[bold red]Error:[/bold red] No template found matching Docker image '{docker_image}'. Please specify a template ID or ensure a template with this image exists.")
                return
            actual_template_id = found_template["id"]
            style_manager.console.print(f"[green]Found matching template ID: {actual_template_id} for image {docker_image}[/green]")
        except Exception as e:
            style_manager.console.print(f"[bold red]Error querying templates: {e}[/bold red]")
            return
    
    if not actual_template_id:
        style_manager.console.print("[bold red]Error: A Template ID is required to rent an executor. None was provided, found, or created.[/bold red]")
        return
    
    # Find ssh keys
    with style_manager.console.status("[cyan]Finding SSH keys...[/cyan]", spinner="earth") as status:
        ssh_keys = api_client.get("ssh-keys/me")
        selected_ssh_key = None

        if ssh_key_path:
            # Read the public key content from the file
            try:
                with open(ssh_key_path, "r") as f:
                    public_key_content = f.read().strip()
            except Exception as e:
                style_manager.console.print(f"[bold red]Error:[/bold red] Could not read SSH key file: {e}")
                return
            
            # Try to find a key matching the public key content
            selected_ssh_key = next((k for k in ssh_keys if k.get("public_key", "").strip() == public_key_content), None)
            if not selected_ssh_key:
                # Create a new SSH key if not found
                new_key = api_client.post("ssh-keys", json={"public_key": public_key_content})
                selected_ssh_key = new_key
        else:
            if ssh_keys:
                selected_ssh_key = ssh_keys[0]
            else:
                style_manager.console.print("[bold red]Error:[/bold red] No SSH keys found or available to use.")
                return
            
        style_manager.console.print(f"[bold green]Using SSH key:[/bold green] {selected_ssh_key['id']}")

    # Determine pod name
    final_pod_name = pod_name_override
    if not final_pod_name:
        # Default naming convention (can be made more sophisticated, e.g., using HUID part of executor)
        final_pod_name = "LiumPod-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        style_manager.console.print(f"[cyan]No pod name specified, using default: {final_pod_name}[/cyan]")

    # Rent the executor with the selected SSH key and resolved template ID
    with style_manager.console.status("[cyan]Renting executor...[/cyan]", spinner="earth") as status:
        api_client.post(
            f"executors/{executor_id}/rent",
            json={
                "pod_name": final_pod_name, # Use determined pod name
                "template_id": actual_template_id, # Use resolved template ID
                "user_public_key": [
                    selected_ssh_key["public_key"]
                ]
            }
        )
    style_manager.console.print(f"[bold green]Executor rented:[/bold green] {executor_id} as pod '{final_pod_name}'")

    # Wait until the pod is running.
    uptime_in_seconds = 0
    def make_renderable(status_msg, table):
        return Panel(
            Group(
                status_msg,
                table
            ),
            title="Executor Status",
            border_style="blue"
        )
    
    table, pod = render_rented_executor_table(executor_id, uptime_in_seconds)
    status_msg = style_manager.console.status("[cyan]Waiting until executor is ready...[/cyan] \n \n", spinner="earth")
    with Live(make_renderable(status_msg, table), refresh_per_second=10) as live:
        live.refresh_per_second = 1
        while True:
            time.sleep(4)
            uptime_in_seconds += 4
            table, pod = render_rented_executor_table(executor_id, uptime_in_seconds)
            live.update(make_renderable(status_msg, table))
            if pod["status"] == "RUNNING":
                style_manager.console.print(f"[bold green]Executor is running:[/bold green] {executor_id}")
                break
