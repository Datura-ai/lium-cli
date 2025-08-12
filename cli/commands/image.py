"""Docker image build and push command."""

import os
import subprocess
import sys

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lium_sdk import Lium, Template
from ..utils import console, handle_errors, loading_status
from ..config import config


class ImageManager:
    """Manages Docker image building, pushing and template creation."""
    
    def __init__(self):
        self.lium = Lium()
        self.username, self.token = self._get_docker_credentials()
        
    def _get_docker_credentials(self) -> tuple[str, str]:
        """Get or prompt for Docker credentials."""
        username = config.get_or_ask('docker.username', 'Docker Hub username')
        token = config.get_or_ask('docker.token', 'Docker Hub Access Token', password=True)
        return username, token
        
    def build_docker_image(self, image_name: str, path: str) -> str:
        """Build Docker image using buildx."""
        image_tag = f"{self.username}/{image_name}:latest"
        
        console.dim(f"Building {image_tag}...")
        
        cmd = [
            'docker', 'buildx', 'build',
            '--platform', 'linux/amd64',
            '--tag', image_tag,
            '--load',
            path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            for line in result.stdout.splitlines():
                if line.strip():
                    console.dim(f"  {line}")
                    
            return image_tag
            
        except subprocess.CalledProcessError as e:
            error_output = e.stderr if e.stderr else e.stdout
            raise RuntimeError(f"Error building Docker image: {error_output}")
            
    def push_docker_image(self, image_name: str) -> str:
        """Push Docker image using docker push."""
        image_tag = f"{self.username}/{image_name}:latest"
        
        console.dim(f"Pushing {image_tag}...")
        
        # Login first
        login_cmd = ['docker', 'login', '-u', self.username, '--password-stdin']
        try:
            subprocess.run(login_cmd, input=self.token, text=True, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Docker login failed: {e.stderr}")
        
        # Push image
        push_cmd = ['docker', 'push', image_tag]
        try:
            result = subprocess.run(push_cmd, capture_output=True, text=True, check=True)
            
            for line in result.stdout.splitlines():
                if line.strip():
                    console.dim(f"  {line}")
                    
            # Extract digest from output
            for line in result.stderr.splitlines() + result.stdout.splitlines():
                if 'digest:' in line:
                    digest = line.split('digest: ')[1].split()[0]
                    return digest
                    
            raise RuntimeError("Could not extract image digest from push response")
            
        except subprocess.CalledProcessError as e:
            error_output = e.stderr if e.stderr else e.stdout
            raise RuntimeError(f"Error pushing Docker image: {error_output}")
            
    def upsert_lium_template(self, image_name: str, digest: str, ports: list[int], start_command: str) -> Template:
        """Create Lium template and return template info."""
        docker_image = f"{self.username}/{image_name}"
        
        template = self.lium.upsert_template(
            name=image_name,
            docker_image=docker_image,
            docker_image_digest=digest,
            docker_image_tag="latest",
            ports=ports,
            start_command=start_command,
            description=image_name,
            is_private=False
        )
        
        return template
        
    def wait_for_verification(self, template, timeout: int = 600):
        """Wait for template verification using SDK wait_template_ready."""
        return self.lium.wait_template_ready(template, timeout)


@click.command("image")
@click.argument("image_name", required=True, type=str)
@click.argument("path", required=True, type=str)
@click.option("--ports", default="22,8000", help="Comma-separated list of ports (default: 22,8000)")
@click.option("--start-command", default="", help="Container start command (default: empty)")
@click.option("--timeout", default=600, help="Verification timeout in seconds (default: 600)")
@handle_errors
def image_command(image_name: str, path: str, ports: str, start_command: str, timeout: int):
    """Build Docker image and create Lium template.
    
    IMAGE_NAME: Name for the Docker image
    PATH: Path to the directory containing Dockerfile
    
    Examples:
      lium image my-app .              # Build from current directory
      lium image my-model ./models     # Build from models directory
      lium image my-app . --ports 22,8080 --start-command "/start.sh"
    """
    manager = ImageManager()
    
    # Parse ports
    try:
        port_list = [int(p.strip()) for p in ports.split(',')]
    except ValueError as e:
        raise ValueError(f"Invalid ports format: {ports}. Use comma-separated integers like '22,8000'")
    
    # Validate path
    dockerfile_path = os.path.join(path, 'Dockerfile')
    if not os.path.exists(dockerfile_path):
        raise ValueError(f"Dockerfile not found at {dockerfile_path}")
    
    # Step 1: Build Docker image
    console.info("🔨 Building Docker image...")
    image_tag = manager.build_docker_image(image_name, path)
    console.success("✓ Docker image built")
    
    # Step 2: Push to Docker Hub  
    console.info("📤 Pushing to Docker Hub...")
    digest = manager.push_docker_image(image_name)
    console.success("✓ Image pushed successfully")

    # Step 3: Create Lium template
    with loading_status("Creating Lium template", "Template created"):
        template = manager.upsert_lium_template(image_name, digest, port_list, start_command)

    # Step 4: Wait for verification
    with loading_status(f"Waiting for verification, {template.id}", "Image verified"):
        verified_template = manager.wait_for_verification(template.id, timeout)
    
    if verified_template:
        console.success(f"✓ Image verified and ready to use")
        console.info(f"Template ID: {verified_template.id}")
        console.dim(f"Use: lium up --template_id {verified_template.id}")
    else:
        console.warning(f"⚠ Template not verified after {timeout}s timeout")
        console.info(f"Template ID: {template.id}")
        console.dim("Check status later with 'lium templates'")
