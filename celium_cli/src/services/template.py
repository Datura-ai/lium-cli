import time
from rich.live import Live
from celium_cli.src.services.api import api_client
from celium_cli.src.utils import console


def create_template(docker_image: str, dockerfile: str | None = None) -> str:
    """
    Create a new template.

    Arguments:
        docker_image: The docker image to use for the template.
        dockerfile: The dockerfile to use for the template.

    Returns:
        The id of the template.
    """
    from celium_cli.src.services.docker import (
        build_and_push_docker_image_from_dockerfile,
        verify_docker_image_validity,
    )

    if dockerfile:
        # Build and push the docker image
        build_and_push_docker_image_from_dockerfile(dockerfile, docker_image)

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

    console.rule(f"[bold blue]Creating template and waiting for verification: [green]{docker_image}")

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
    }
    with console.status("Creating template...", spinner="monkey"):
        template = api_client.post("templates", json=payload)
        template_id = template["id"]
        console.print(f"Template created successfully with id: {template_id}")

    # Wait until the template passes the verification process.
    start_time = time.time()
    status_msg = console.status(
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
            status_msg = console.status(
                f"[cyan]Waiting until template pass verification (waiting for {int(time.time() - start_time)} seconds)...[/cyan] \n \n", spinner="earth"
            )
            live.update(status_msg)

    console.print(f"[bold green]Template verified successfully:[/bold green] {template_id}")
    return template_id