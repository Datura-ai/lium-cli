from rich.table import Table
from celium_cli.src.services.api import api_client
from celium_cli.src.utils import console, pretty_minutes


def get_executors_and_print_table() -> list[dict]:
    with console.status("Fetching executors...", spinner="monkey"):
        executors = api_client.get("executors", require_auth=False)

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
    # api_client.post(
    #     f"executors/{executor_id}/rent",
    #     require_auth=True,
    #     json={
    #         "template_id": template["id"],
    #         "ssh_key_id": selected_ssh_key["id"]
    #     }
    # )
