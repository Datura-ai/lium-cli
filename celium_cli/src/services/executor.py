import time
from datetime import datetime
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.console import Group
from celium_cli.src.services.api import api_client
from celium_cli.src.utils import console, pretty_minutes, pretty_seconds


def get_executors_and_print_table(count: int, machine_name: str) -> list[dict]:
    query_params = {
        'gpu_count_lte': count,
        'gpu_count_gte': count,
        'machine_names': machine_name
    }
    with console.status("Fetching executors...", spinner="monkey"):
        executors = api_client.get("executors", params=query_params, require_auth=False)

    table = Table(title="Available Executors")
    table.add_column("ID", style="bold blue")
    table.add_column("Name", style="bold green")
    table.add_column("Count", style="bold red")
    table.add_column("Price Per Hour", style="bold yellow")
    table.add_column("Uptime", style="bold magenta")

    sorted_executors = sorted(executors, key=lambda x: x["uptime_in_minutes"], reverse=True)
    for executor in sorted_executors[:5]:
        table.add_row(
            executor["id"],
            executor["machine_name"],
            f"{executor['specs']['gpu']['count']}",
            f"${executor['price_per_hour']}",
            pretty_minutes(executor['uptime_in_minutes'])
        )

    console.print(table)
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


def rent_executor(executor_id: str, docker_image: str, ssh_key_path: str | None):
    """Rent an executor for a given docker image
    
    Arguments:
        executor_id: The id of the executor to rent
        docker_image: The docker image to run on the executor
        ssh_key_path: The path to the ssh key to use for the executor
    """
    image, tag = docker_image.split(":")
    # Find a template with given docker image
    templates = api_client.get(f"templates")
    if len(templates) == 0:
        console.print("[bold red]Error:[/bold red] No templates found, please try again later.")
        return 
    
    template = next((
        t for t in templates if t["docker_image"] == image and t["docker_image_tag"] == tag
    ), None)
    if not template:
        console.print("[bold red]Error:[/bold red] No template found for given docker image")
        return
    
    # Find ssh keys
    ssh_keys = api_client.get("ssh-keys/me")
    selected_ssh_key = None

    if ssh_key_path:
        # Read the public key content from the file
        try:
            with open(ssh_key_path, "r") as f:
                public_key_content = f.read().strip()
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] Could not read SSH key file: {e}")
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
            console.print("[bold red]Error:[/bold red] No SSH keys found or available to use.")
            return
        
    console.print(f"[bold green]Using SSH key:[/bold green] {selected_ssh_key['id']}")

    # Rent the executor with the selected SSH key
    api_client.post(
        f"executors/{executor_id}/rent",
        json={
            "pod_name": "Pod " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "template_id": template["id"],
            "user_public_key": [
                selected_ssh_key["public_key"]
            ]
        }
    )
    console.print(f"[bold green]Executor rented:[/bold green] {executor_id}")

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
    status_msg = console.status("[cyan]Waiting until executor is ready...[/cyan] \n \n", spinner="earth")
    with Live(make_renderable(status_msg, table), refresh_per_second=10) as live:
        live.refresh_per_second = 1
        while True:
            time.sleep(4)
            uptime_in_seconds += 4
            table, pod = render_rented_executor_table(executor_id, uptime_in_seconds)
            live.update(make_renderable(status_msg, table))
            if pod["status"] == "RUNNING":
                console.print(f"[bold green]Executor is running:[/bold green] {executor_id}")
                break
