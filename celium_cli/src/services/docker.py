import subprocess
import os
import socket
import time
import uuid
import paramiko
import io
from celium_cli.src.styles import style_manager


CUSTOM_TEMPLATE_VERIFY_CONTAINER_PREFIX = "celium-cli-test-container"


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Bind to port 0 means "let the OS pick a free port"
        s.bind(('', 0))
        return s.getsockname()[1]
    

def generate_ssh_key_pair() -> tuple[str, str]:
    """
    Generate a new SSH key pair.
    """
    # Generate a new RSA key
    key = paramiko.RSAKey.generate(2048)
    
    # Private key as string
    private_key_io = io.StringIO()
    key.write_private_key(private_key_io)
    private_key = private_key_io.getvalue()
    
    # Public key as string (OpenSSH format)
    public_key = f"{key.get_name()} {key.get_base64()}"
    
    return private_key, public_key


def build_and_push_docker_image_from_dockerfile(
    dockerfile_path: str, 
    image_name: str, 
    docker_username: str = None,
    docker_password: str = None
) -> tuple[bool, int]:
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
    image_size = None # built image size in bytes

    try:
        style_manager.console.rule(f"[bold blue]Building Docker Image and pushing to registry: [green]{image_name}")
        build_cmd = [
            "docker", "build",
            "-f", dockerfile_path,
            "-t", image_name,
            dockerfile_dir
        ]
        with style_manager.console.status("[bold cyan]Building Docker Image...[/bold cyan]", spinner="earth") as status:
            result = subprocess.run(build_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                style_manager.console.print(f"[bold red]Docker build failed![/bold red]\n{result.stderr}")
                return False, image_size
        
        style_manager.console.print(f"[bold green]Docker image built successfully![/bold green]")

        # Get the image size in bytes
        size_cmd = ["docker", "image", "inspect", "-f", "{{.Size}}", image_name]
        size_result = subprocess.run(size_cmd, capture_output=True, text=True)
        if size_result.returncode == 0:
            image_size = int(size_result.stdout.strip())
            style_manager.console.print(f"[bold blue]Docker image size:[/bold blue] {image_size / (1024*1024):.2f} MB")
        else:
            raise Exception("Failed to get the image size.")

        # Docker login if credentials are provided
        if docker_username and docker_password:
            login_cmd = ["docker", "login", "--username", docker_username, "--password-stdin"]
            with style_manager.console.status("[bold cyan]Logging in to Docker registry...[/bold cyan]", spinner="earth") as status:
                login_proc = subprocess.run(
                    login_cmd,
                    input=docker_password,
                    capture_output=True,
                    text=True
                )
                if login_proc.returncode != 0:
                    style_manager.console.print(f"[bold red]Docker login failed![/bold red]\n{login_proc.stderr}")
                    return False, image_size

            style_manager.console.print(f"[bold green]Docker login successful![/bold green]")

        # Push the docker image
        with style_manager.console.status("[bold cyan]Pushing Docker Image...[/bold cyan]", spinner="earth") as status:
            push_cmd = ["docker", "push", image_name]
            result = subprocess.run(push_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                style_manager.console.print(f"[bold red]Docker push failed![/bold red]\n{result.stderr}")
                return False, image_size
            
        style_manager.console.print(f"[bold green]Docker image pushed successfully![/bold green]")
        return True, image_size
    except Exception as e:
        style_manager.console.print(f"[bold red]An error occurred: {e}")
        return False, None


def create_docker_container(image_name: str, public_key: str) -> tuple[str, int]:
    # Find a free port 
    available_port = find_free_port()
    container_name = f"{CUSTOM_TEMPLATE_VERIFY_CONTAINER_PREFIX}-{uuid.uuid4()}"
    # Run the container
    run_cmd = [
        "docker", "run",
        "-d",
        "-p", f"{available_port}:22",
        "-e", f"PUBLIC_KEY={public_key}",
        "--name", container_name,
        image_name
    ]
    subprocess.run(run_cmd, check=True)
    # Check if the container is running
    status_cmd = ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"]
    status = subprocess.run(status_cmd, capture_output=True, text=True)
    if status.returncode != 0:
        style_manager.console.print(f"[bold red]Docker container is not running![/bold red]")
        raise Exception("Docker container is not running")
    return container_name, available_port


def install_openssh_server(container_name: str, public_key: str):
    # Step 1: check openssh-server is installed
    command = f"docker exec {container_name} dpkg -l | grep openssh-server"
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        # Step 1.1: install if it's not installed in docker container.
        command = f"docker exec {container_name} sh -c 'apt-get update && apt-get install -y openssh-server'"
        install_result = subprocess.run(command, shell=True)
        if install_result.returncode != 0:
            raise RuntimeError("Failed to install openssh-server in the container.")

    # Step 2: start SSH service and prepare .ssh directory
    command = f"docker exec {container_name} sh -c 'ssh-keygen -A && mkdir -p /root/.ssh && chmod 700 /root/.ssh && service ssh start'"
    start_result = subprocess.run(command, shell=True)
    if start_result.returncode != 0:
        raise RuntimeError("Failed to start SSH service or prepare .ssh directory.")

    # Step 3: add ssh key (append, not overwrite) and set permissions
    # Use printf and proper quoting to avoid issues with special characters
    safe_pubkey = public_key.replace('"', '\"')
    command = (
        f'docker exec {container_name} sh -c '
        f'"echo \"{safe_pubkey}\" >> /root/.ssh/authorized_keys && '
        f'chmod 600 /root/.ssh/authorized_keys"'
    )
    key_result = subprocess.run(command, shell=True)
    if key_result.returncode != 0:
        raise RuntimeError("Failed to add public key to authorized_keys.")


def clean_up_template_verify_docker_resources() -> None:
    """Clean up all containers and volumes which are created for custom template verification."""
    # delete docker containers
    try:
        command = f"docker ps -a --filter 'name={CUSTOM_TEMPLATE_VERIFY_CONTAINER_PREFIX}' --format '{{{{.ID}}}}'"
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        container_ids = result.stdout.strip()
        if container_ids:
            for container_id in container_ids.splitlines():
                remove_command = f"docker rm -f {container_id}"
                subprocess.run(remove_command, shell=True)
                style_manager.console.print(f"Removed container with ID: {container_id}")
        else:
            style_manager.console.print(f"No containers found with '{CUSTOM_TEMPLATE_VERIFY_CONTAINER_PREFIX}' prefix.")
    except Exception as e:
        style_manager.console.print(f"Error cleaning up containers: {e}")


def verify_ssh_connection(port: int, private_key_str: str, username: str = "root", timeout: int = 30) -> bool:
    """
    Attempt to SSH into a host using the provided private key.
    Returns True if connection is successful, False otherwise.
    """
    try:
        # Load private key from string
        private_key = paramiko.RSAKey.from_private_key(io.StringIO(private_key_str))
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Retry logic in case SSH service is not up yet
        start_time = time.time()
        while True:
            try:
                client.connect(hostname='127.0.0.1', port=port, username=username, pkey=private_key, timeout=10)
                break
            except Exception as e:
                if time.time() - start_time > timeout:
                    raise e
                time.sleep(1)
        
        # Optionally, run a simple command to verify
        stdin, stdout, stderr = client.exec_command("echo SSH connection successful")
        output = stdout.read().decode().strip()
        client.close()
        return output == "SSH connection successful"
    except Exception as e:
        style_manager.console.print(f"SSH connection failed: {e}")
        return False


def verify_docker_image_validity(image_name: str) -> bool:
    """
    Verify the validity of a docker image.
    """
    try:
        style_manager.console.rule(f"[bold blue]Verifying docker image validity: [green]{image_name}")
        clean_up_template_verify_docker_resources()

        # Generate a new SSH key pair
        private_key, public_key = generate_ssh_key_pair()

        # Create a docker container from the image
        with style_manager.console.status("[bold cyan]Creating docker container...[/bold cyan]", spinner="earth") as status:
            container_name, port = create_docker_container(image_name, public_key)
        style_manager.console.print(f"[bold green]Docker container created successfully![/bold green]")

        # Install the openssh-server 
        with style_manager.console.status("[bold cyan]Installing openssh-server...[/bold cyan]", spinner="earth") as status:
            install_openssh_server(container_name, public_key)
        style_manager.console.print(f"[bold green]Openssh-server installed successfully![/bold green]")

        # Verify the SSH connection
        with style_manager.console.status("[bold cyan]Verifying SSH connection...[/bold cyan]", spinner="earth") as status:
            is_verified = verify_ssh_connection(port, private_key)

            if not is_verified:
                style_manager.console.print(f"[bold red]SSH connection failed![/bold red]")
                return False
            style_manager.console.print(f"[bold green]SSH connection verified successfully![/bold green]")
            return True
    except Exception as e:
        style_manager.console.print(f"[bold red]An error occurred: {e}")
        return False    
    finally:
        # clean_up_template_verify_docker_resources()
        pass
    