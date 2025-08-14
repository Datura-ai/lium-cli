"""Docker image build and push command."""

import json
import subprocess
from pathlib import Path

import click
from lium_sdk import Lium, Template

from ..utils import console, handle_errors, loading_status


def get_docker_username() -> str:
    """Get Docker username from credential helper."""
    config_path = Path.home() / '.docker' / 'config.json'
    if not config_path.exists():
        raise RuntimeError("Docker not configured. Please run: docker login")
    
    with open(config_path) as f:
        config = json.load(f)
    
    creds_store = config.get('credsStore')
    if not creds_store:
        raise RuntimeError("No credential store configured. Please run: docker login")
    
    try:
        result = subprocess.run(
            [f'docker-credential-{creds_store}', 'list'],
            capture_output=True, text=True, check=True
        )
        creds = json.loads(result.stdout)
        
        for registry in ['https://index.docker.io/v1/', 'index.docker.io', 'docker.io']:
            if username := creds.get(registry):
                console.dim(f"Using Docker login for {username}")
                return username
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        pass
        
    raise RuntimeError("Docker authentication failed. Please run: docker login")


def build_and_push_image(image_name: str, path: str, username: str) -> tuple[str, str]:
    """Build and push Docker image, return tag and digest."""
    image_tag = f"{username}/{image_name}:latest"
    
    # Build
    console.dim(f"Building {image_tag}...")
    subprocess.run([
        'docker', 'buildx', 'build',
        '--platform', 'linux/amd64',
        '--tag', image_tag,
        '--load', path
    ], check=True)
    
    # Push
    console.dim(f"Pushing {image_tag}...")
    result = subprocess.run(['docker', 'push', image_tag], 
                          capture_output=True, text=True, check=True)
    
    for line in result.stdout.split('\n'):
        if 'digest:' in line:
            digest = line.split('digest: ')[1].split()[0]
            return image_tag, digest
            
    raise RuntimeError("Could not extract image digest")


def create_template(image_name: str, digest: str, ports: list[int], start_command: str, username: str) -> Template:
    """Create Lium template."""
    lium = Lium()
    return lium.upsert_template(
        name=image_name,
        docker_image=f"{username}/{image_name}",
        docker_image_digest=digest,
        docker_image_tag="latest",
        ports=ports,
        start_command=start_command,
        description=image_name,
        is_private=False
    )


@click.command("image")
@click.argument("image_name", required=True, type=str)
@click.argument("path", required=True, type=str)
@click.option("--ports", default="22,8000", help="Comma-separated list of ports (default: 22,8000)")
@click.option("--start-command", default="", help="Container start command (default: empty)")
@click.option("--timeout", default=600, help="Verification timeout in seconds (default: 600)")
@handle_errors
def image_command(image_name: str, path: str, ports: str, start_command: str, timeout: int):
    """Build Docker image and create Lium template.
    
    \b
    IMAGE_NAME: Name for the Docker image
    PATH: Path to the directory containing Dockerfile
    
    \b
    Examples:
      lium image my-app .              # Build from current directory
      lium image my-model ./models     # Build from models directory
      lium image my-app . --ports 22,8080 --start-command "/start.sh"
    """
    # Validate
    if not (Path(path) / 'Dockerfile').exists():
        raise ValueError(f"Dockerfile not found in {path}")
    
    try:
        port_list = [int(p.strip()) for p in ports.split(',')]
    except ValueError:
        raise ValueError(f"Invalid ports format: {ports}")

    # Get username and build/push
    username = get_docker_username()
    console.info("🔨 Building and pushing Docker image...")
    image_tag, digest = build_and_push_image(image_name, path, username)

    # Create template
    with loading_status("Creating Lium template", ""):
        template = create_template(image_name, digest, port_list, start_command, username)

    # Wait for verification
    with loading_status(f"Waiting for verification, {template.id}", ""):
        lium = Lium()
        verified_template = lium.wait_template_ready(template.id, timeout)

    if verified_template:
        console.info(f"Template ID: {verified_template.id}")
        console.dim(f"Use: lium up --template_id {verified_template.id}")
    else:
        console.warning(f"⚠ Template not verified after {timeout}s timeout")
        console.info(f"Template ID: {template.id}")
        console.dim("Check status later with 'lium templates'")
