"""Docker image build and push command."""

import os
import subprocess
import sys
import time
from typing import Optional

import click
import docker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lium_sdk import Lium, Template
from ..utils import console, handle_errors, loading_status
from ..config import config


class ImageManager:
    """Manages Docker image building, pushing and template creation."""
    
    def __init__(self):
        self.lium = Lium()
        self._docker = None
        
    def get_docker_credentials(self) -> tuple[str, str]:
        """Get or prompt for Docker credentials."""
        username = config.get_or_ask('docker.username', 'Docker Hub username')
        token = config.get_or_ask('docker.token', 'Docker Hub Access Token', password=True)
        return username, token
    
    @property
    def docker(self):
        """Get Docker client, initialize if needed."""
        if self._docker is None:
            try:
                # Try different Docker socket locations
                try:
                    self._docker = docker.from_env()
                except docker.errors.DockerException:
                    # Try Docker Desktop paths
                    for base_url in [
                        'unix:///var/run/docker.sock',
                        'unix:///$HOME/.docker/run/docker.sock',  
                        'unix:///Users/$USER/.docker/run/docker.sock'
                    ]:
                        try:
                            self._docker = docker.DockerClient(base_url=base_url.replace('$HOME', os.path.expanduser('~')).replace('$USER', os.environ.get('USER', '')))
                            self._docker.ping()
                            break
                        except:
                            continue
                    else:
                        raise RuntimeError("Could not connect to Docker daemon. Is Docker running?")
                
                # Test connection
                self._docker.ping()
                username, token = self.get_docker_credentials()
                self._docker.login(username=username, password=token)
                
            except docker.errors.DockerException as e:
                raise RuntimeError(f"Could not connect to Docker daemon: {e}")
            except Exception as e:
                raise RuntimeError(f"Docker connection error: {e}")
        return self._docker
        
    def build_docker_image(self, image_name: str, path: str) -> str:
        """Build Docker image and return digest."""
        username, _ = self.get_docker_credentials()
        image_tag = f"{username}/{image_name}:latest"
        
        try:
            console.dim(f"Building {image_tag}...")
            
            # Use buildx for cross-platform builds
            build_result = self.docker.api.build(
                path=path,
                tag=image_tag,
                rm=True,
                forcerm=True,
                platform="linux/amd64",
                decode=True
            )
            
            image_id = None
            for log_line in build_result:
                if 'stream' in log_line:
                    output = log_line['stream'].strip()
                    if output:
                        console.dim(f"  {output}")
                        # Extract image ID from final step
                        if 'Successfully built' in output:
                            image_id = output.split('Successfully built ')[1]
                elif 'aux' in log_line and 'ID' in log_line['aux']:
                    image_id = log_line['aux']['ID']
                        
            if not image_id:
                # Fallback: get image by tag
                image = self.docker.images.get(image_tag)
                image_id = image.id
                
            return image_id
            
        except docker.errors.BuildError as e:
            raise RuntimeError(f"Error building Docker image: {e}")
        except docker.errors.APIError as e:
            raise RuntimeError(f"Error communicating with Docker API: {e}")
            
    def push_docker_image(self, image_name: str) -> str:
        """Push Docker image and return digest."""
        username, _ = self.get_docker_credentials()
        image_tag = f"{username}/{image_name}:latest"
        
        try:
            console.dim(f"Pushing {image_tag}...")
            push_log_gen = self.docker.images.push(image_tag, stream=True, decode=True)
            digest = None
            
            for log_line in push_log_gen:
                if "status" in log_line:
                    status = log_line['status']
                    if "progress" in log_line:
                        console.dim(f"  {status} - {log_line['progress']}")
                    else:
                        console.dim(f"  {status}")
                        
                    if "digest" in status:
                        digest = status.split("digest: ")[1].split(" ")[0]
                elif "aux" in log_line and "Digest" in log_line["aux"]:
                    digest = log_line["aux"]["Digest"]
                elif "error" in log_line:
                    raise RuntimeError(f"Error during push: {log_line['errorDetail']['message']}")
                    
            if not digest:
                raise RuntimeError("Could not extract image digest from push response")
                
            return digest
            
        except docker.errors.APIError as e:
            raise RuntimeError(f"Error pushing Docker image: {e}")
            
    def create_lium_template(self, image_name: str, digest: str, ports: list[int], start_command: str) -> Template:
        """Create Lium template and return template info."""
        username, _ = self.get_docker_credentials()
        docker_image = f"{username}/{image_name}"
        
        template = self.lium.create_template(
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
    image_id = manager.build_docker_image(image_name, path)
    console.success("✓ Docker image built")
    
    # Step 2: Push to Docker Hub  
    console.info("📤 Pushing to Docker Hub...")
    digest = manager.push_docker_image(image_name)
    console.success("✓ Image pushed successfully")
    
    # Step 3: Create Lium template
    with loading_status("Creating Lium template", "Template created"):
        template = manager.create_lium_template(image_name, digest, port_list, start_command)

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
