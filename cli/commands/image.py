"""Docker image build and push command."""

import json
import subprocess
from pathlib import Path

import click
from lium_sdk import Lium, Template

from ..utils import console, handle_errors, loading_status
from ..config import config

def _get_docker_credential_location_wsl_windows() -> str:
    try:
        # Use Windows `where` command via cmd.exe
        cmd = ["cmd.exe", "/c", "where", "docker-credential-desktop.exe"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
            check=True
        )

        # Take the first line of output (first path found)
        path = result.stdout.strip().splitlines()[0]
        return path
    except Exception as e:
        return None

def get_username_docker_username_wsl():
    try:
        # Use system-wide path
        docker_cred_path = _get_docker_credential_location_wsl_windows()
        if not docker_cred_path:
            return None

        cmd = ["cmd.exe", "/c", docker_cred_path, "get"]
        result = subprocess.run(
            cmd,
            input="https://index.docker.io/v1/\n",  # send registry URL to stdin
            capture_output=True,
            text=True,
            shell=False,
            check=True
        )

        creds = json.loads(result.stdout)
        return creds.get("Username")
    except Exception as e:
        return None

def _is_wsl()->bool:
    """Check if user is on WSL (works with all distros: Ubuntu, Debian, custom, etc.)"""
    import platform
    import os
    
    # Only run on Linux systems
    if platform.system() != "Linux":
        return False
    
    # Method 1: Check kernel release for WSL indicators
    try:
        uname_info = os.uname()
        release = uname_info.release.lower()
        
        # Check for various WSL indicators in kernel release
        wsl_indicators = ["microsoft", "wsl", "-microsoft-standard"]
        if any(indicator in release for indicator in wsl_indicators):
            return True
    except Exception:
        pass
    
    # Method 2: Check for WSL-specific files
    wsl_files = [
        "/proc/sys/fs/binfmt_misc/WSLInterop",  # WSL2
        "/proc/version"  # Check version file content
    ]
    
    for wsl_file in wsl_files:
        try:
            if os.path.exists(wsl_file):
                if wsl_file.endswith("WSLInterop"):
                    return True
                elif wsl_file.endswith("version"):
                    with open(wsl_file, 'r') as f:
                        content = f.read().lower()
                        if "microsoft" in content or "wsl" in content:
                            return True
        except Exception:
            continue
    
    # Method 3: Check environment variables
    try:
        # WSL sets these environment variables
        if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSLENV"):
            return True
    except Exception:
        pass
    
    return False

def get_docker_username() -> str:
    """Get Docker username with proper checks."""
    
    # Check if user is using WSL if yes get credential from windows layer 
    is_wsl = _is_wsl()
    if is_wsl:
        username = get_username_docker_username_wsl()
        if username:
            return username

   # 1. Try docker info first (works for some users)
    username = get_username_from_info()
    if username:
        return username

    # 2. Try credential helper (current implementation works well)
    username = get_username_from_credstore()
    if username:
        return username

    is_logged = is_logged_in()
    if not is_logged:
        raise RuntimeError("Docker authentication failed. Please run: docker login")

    # 3. Fallback to config or ask
    username = config.get_or_ask('docker.username', 'Enter your Docker Hub username')
    
    if not username:
        raise RuntimeError(
            "Docker username not found. Please:\n"
            "1. Run 'docker login' to authenticate\n"
            "2. Or provide username when prompted"
        )
    
    console.dim(f"Using Docker username: {username}")
    return username


def is_logged_in() -> bool | None:
    try:
        message = str(subprocess.run(['docker', 'login'], capture_output=True, text=True, timeout=0.5))
    except subprocess.TimeoutExpired as e:
        message = str(e.stdout)

    if "Authenticating" in message:
        return True
    elif "Cannot perform an interactive login" in message:
        return False
    return None


def get_username_from_credstore() -> str:
    config_path = Path.home() / '.docker' / 'config.json'
    if config_path.exists():
        with open(config_path) as f:
            config_data = json.load(f)

        creds_store = config_data.get('credsStore')
        if creds_store:
            try:
                result = subprocess.run(
                    [f'docker-credential-{creds_store}', 'list'],
                    capture_output=True, text=True, check=True
                )
                creds = json.loads(result.stdout)

                for registry in ['https://index.docker.io/v1/', 'index.docker.io', 'docker.io']:
                    if username := creds.get(registry):
                        return username
            except:
                pass


def get_username_from_info():
    try:
        result = subprocess.run(['docker', 'info'],
                                capture_output=True, text=True, timeout=5)
        # Use grep-like search for cross-platform compatibility
        for line in result.stdout.split('\n'):
            if 'Username:' in line:
                username = line.split('Username:')[1].strip()
                return username
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        # Docker not installed or command failed
        pass


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
