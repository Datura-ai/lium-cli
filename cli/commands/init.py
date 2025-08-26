"""Initialize Lium CLI configuration."""

import os
import subprocess
import sys
from pathlib import Path

import click
from rich.prompt import Prompt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..config import config
from ..utils import console, handle_errors




def setup_api_key() -> None:
    """Setup API key in config."""
    # Check if already set
    current_key = config.get('api.api_key')
    if current_key:
        masked_key = current_key[:8] + '...' + current_key[-4:] if len(current_key) > 12 else '***'
        console.success(f"✓ API key already configured: {masked_key}")
        
        if Prompt.ask("[yellow]Update API key?[/yellow]", choices=["y", "n"], default="n") == "n":
            return
    
    # Prompt for new key
    api_key = Prompt.ask(
        "[cyan]Enter your Lium API key (get from https://lium.ai/api-keys)[/cyan]"
    )
    
    if not api_key:
        console.error("No API key provided")
        return
    
    # Save to config
    config.set('api.api_key', api_key)
    console.success(f"✓ API key saved")


def setup_ssh_key() -> None:
    """Setup SSH key path in config."""
    # Find available SSH keys
    ssh_dir = Path.home() / ".ssh"
    available_keys = []
    
    for key_name in ["id_ed25519", "id_rsa", "id_ecdsa"]:
        key_path = ssh_dir / key_name
        if key_path.exists():
            available_keys.append(key_path)
    
    if not available_keys:
        console.warning("⚠ No SSH keys found. Generating new SSH key...")
        key_path = ssh_dir / "id_ed25519"
        
        try:
            subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(key_path), "-N", "", "-q"], check=True)
            console.success(f"✓ SSH key generated: {key_path}")
            config.set('ssh.key_path', str(key_path))
            return
        except Exception as e:
            console.error(f"Failed to generate SSH key: {e}")
            return
    
    # Auto-select if only one
    if len(available_keys) == 1:
        selected_key = available_keys[0]
        console.success(f"✓ Using SSH key: {selected_key}")
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
    
    # Save to config
    config.set('ssh.key_path', str(selected_key))
    console.success(f"✓ SSH key configured")


def show_config() -> None:
    """Display current configuration."""
    from ..commands.config import _config_show
    _config_show()


@click.command("init")
@handle_errors
def init_command():
    """Initialize Lium CLI configuration.
    
    Sets up API key and SSH key configuration for first-time users.
    
    Example:
      lium init    # Interactive setup wizard
    """
    console.info("Lium CLI Setup\n")
    
    # Setup API key
    setup_api_key()
    
    # Setup SSH key
    setup_ssh_key()
    
    # Show final config
    show_config()
    
    console.dim("You can now use 'lium ls' to list available executors")