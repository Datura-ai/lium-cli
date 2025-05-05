from celium_cli.src.utils import console
import subprocess
import os


def build_and_push_docker_image_from_dockerfile(
    dockerfile_path: str, 
    image_name: str, 
    docker_username: str = None,
    docker_password: str = None
):
    """
    Build and push a docker image from a dockerfile.

    Args:
        dockerfile_path (str): Path to the Dockerfile
        image_name (str): Name of the Docker image
        docker_username (str, optional): Docker registry username. Defaults to None.
        docker_password (str, optional): Docker registry password. Defaults to None.

    Returns:
        bool: True if build and push successful, False otherwise
    """
    dockerfile_dir = os.path.dirname(os.path.abspath(dockerfile_path))

    try:
        console.rule(f"[bold blue]Building Docker Image: [green]{image_name}")
        build_cmd = [
            "docker", "build",
            "-f", dockerfile_path,
            "-t", image_name,
            dockerfile_dir
        ]
        result = subprocess.run(build_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[bold red]Docker build failed![/bold red]\n{result.stderr}")
            return False
        console.print(f"[bold green]Docker image built successfully![/bold green]")

        # Docker login if credentials are provided
        if docker_username and docker_password:
            console.rule(f"[bold blue]Logging in to Docker registry as [green]{docker_username}")
            login_cmd = ["docker", "login", "--username", docker_username, "--password-stdin"]
            login_proc = subprocess.run(
                login_cmd,
                input=docker_password,
                capture_output=True,
                text=True
            )
            if login_proc.returncode != 0:
                console.print(f"[bold red]Docker login failed![/bold red]\n{login_proc.stderr}")
                return False
            console.print(f"[bold green]Docker login successful![/bold green]")

        console.rule(f"[bold blue]Pushing Docker Image: [green]{image_name}")
        push_cmd = ["docker", "push", image_name]
        result = subprocess.run(push_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[bold red]Docker push failed![/bold red]\n{result.stderr}")
            return False
        console.print(f"[bold green]Docker image pushed successfully![/bold green]")
        return True
    except Exception as e:
        console.print(f"[bold red]An error occurred: {e}")
        return False


