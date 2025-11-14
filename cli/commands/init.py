"""Initialize Lium CLI configuration."""

import subprocess
from pathlib import Path

import click
from rich.prompt import Prompt

from ..auth import browser_auth
from cli.settings import config
from ..utils import console, handle_errors


def setup_api_key() -> None:
    """Setup API key using browser authentication."""
    # Check if already configured
    current_key = config.get('api.api_key')
    if current_key:
        return  # Already configured, skip silently
    
    # Browser authentication flow
    api_key = browser_auth()
    
    if api_key:
        config.set('api.api_key', api_key)
    else:
        console.error("Authentication failed")


def setup_ssh_key() -> None:
    """Setup SSH key path in config."""
    # Skip if already configured
    if config.get('ssh.key_path'):
        return
    
    ssh_dir = Path.home() / ".ssh"
    available_keys = [
        ssh_dir / key_name 
        for key_name in ["id_ed25519", "id_rsa", "id_ecdsa"]
        if (ssh_dir / key_name).exists()
    ]
    
    if not available_keys:
        # Generate new key silently
        key_path = ssh_dir / "id_ed25519"
        try:
            subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-f", str(key_path), "-N", "", "-q"],
                check=True, capture_output=True
            )
            selected_key = key_path
        except Exception:
            return
    elif len(available_keys) == 1:
        # Auto-select single key
        selected_key = available_keys[0]
    else:
        # Let user choose
        console.info("Multiple SSH keys found:")
        for i, key in enumerate(available_keys, 1):
            console.info(f"  {i}. {key}")
        
        choice = Prompt.ask(
            "Select SSH key",
            choices=[str(i) for i in range(1, len(available_keys) + 1)],
            default="1"
        )
        selected_key = available_keys[int(choice) - 1]
    
    config.set('ssh.key_path', str(selected_key))


@click.command("init")
@handle_errors
def init_command():
    """Initialize Lium CLI configuration.
    
    Sets up API key and SSH key configuration for first-time users.
    
    Example:
      lium init    # Interactive setup wizard
    """
    setup_api_key()
    setup_ssh_key()
    
    if config.get('api.api_key'):
        console.success("✓ Lium configured successfully")
