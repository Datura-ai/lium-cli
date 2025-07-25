import time
import uuid
from rich.live import Live
from lium_cli.src.services.api import api_client
from lium_cli.src.styles import style_manager
from rich.prompt import Prompt


def create_template(docker_image: str | None, dockerfile: str | None = None) -> str:
    """
    Create a new template.

    Arguments:
        docker_image: The docker image to use for the template.
        dockerfile: The dockerfile to use for the template.

    Returns:
        The id of the template.
    """
    from lium_cli.src.services.docker import (
        build_and_push_docker_image_from_dockerfile,
        verify_docker_image_validity,
    )
    from lium_cli.src.services.docker_credential import get_docker_credential

    is_one_time_template = False
    image_size = None # built image size in bytes

    # Get docker hub credential
    docker_credential_id, docker_username, docker_password = get_docker_credential()

    if not docker_image and not dockerfile:
        raise Exception("No [blue]Docker image[/blue] or [blue]Dockerfile[/blue] provided.")

    if not docker_image:
        docker_image = f"{docker_username}/lium-template-{uuid.uuid4()}:latest"
        style_manager.console.print(f"[bold yellow]Warning:[/bold yellow] No [blue]Docker image[/blue] provided, generated new docker image: [green]{docker_image}[/green]")
        is_one_time_template = True
    else:
        # Verify if the docker image matches the Docker Hub credentials
        if not docker_image.startswith(docker_username):
            style_manager.console.print(f"[bold red]Error:[/bold red] Docker image '{docker_image}' does not match the Docker Hub credentials for user '{docker_username}'.")
            docker_image = Prompt.ask(
                f"  Please enter a valid Docker image name that starts with '{docker_username}'",
                console=style_manager.console
            )
            if not docker_image.startswith(docker_username):
                raise Exception(f"[bold red]Error:[/bold red] Provided Docker image '{docker_image}' still does not match the Docker Hub credentials for user '{docker_username}'.")
        else:
            style_manager.console.print(f"[bold green]Docker image matches the Docker Hub credentials: {docker_image}[/bold green]")

    if dockerfile:
        # Build and push the docker image
        is_success, built_image_size = build_and_push_docker_image_from_dockerfile(dockerfile, docker_image, docker_username, docker_password)
        if not is_success:
            raise Exception("Failed to build and push the docker image.")
        
        image_size = built_image_size

    # Verify the docker image is valid
    is_verified = verify_docker_image_validity(docker_image)
    if not is_verified:
        raise Exception("Docker image is not valid. Try to update your Dockerfile or provide a valid docker image.")

    # Check if the template exists with same docker image. If it does, return the template id.
    templates = api_client.get("templates")
    for template in templates:
        full_docker_image = f"{template['docker_image']}:{template['docker_image_tag']}"
        if full_docker_image == docker_image:
            return template["id"]

    style_manager.console.rule(f"[bold blue]Creating template and waiting for verification: [green]{docker_image}")

    # Create the template
    payload = {
        "category": "UBUNTU",
        "description": "",
        "docker_image": docker_image.split(":")[0],
        "docker_image_tag": docker_image.split(":")[1],
        "docker_image_digest": "",
        "entrypoint": "",
        "environment": {},
        "internal_ports": [],
        "is_private": True,
        "name": docker_image,
        "readme": "",
        "startup_commands": "",
        "volumes": ["/workspace"],
        "one_time_template": is_one_time_template,
        "is_temporary": is_one_time_template,
        "docker_image_size": image_size,
        "docker_credential_id": docker_credential_id,
    }
    with style_manager.console.status("Creating template...", spinner="monkey") as status:
        template = api_client.post("templates", json=payload)
        template_id = template["id"]
        style_manager.console.print(f"Template created successfully with id: {template_id}")

    # Wait until the template passes the verification process.
    start_time = time.time()
    status_msg = style_manager.console.status(
        f"[cyan]Waiting until template pass verification (waiting for {int(time.time() - start_time)} seconds)...[/cyan] \n \n", spinner="earth"
    )
    with Live(status_msg, refresh_per_second=10) as live:
        while True:
            template = api_client.get(f"templates/{template_id}")
            if "VERIFY_SUCCESS" in template["status"]:
                break

            if "VERIFY_FAILED" in template["status"]:
                api_client.delete(f"templates/{template_id}")
                raise Exception("Template verification failed. Please try again.")

            time.sleep(10)
            status_msg = style_manager.console.status(
                f"[cyan]Waiting until template pass verification (waiting for {int(time.time() - start_time)} seconds)...[/cyan] \n \n", spinner="earth"
            )
            live.update(status_msg)

    style_manager.console.print(f"[bold green]Template verified successfully:[/bold green] {template_id}")
    return template_id