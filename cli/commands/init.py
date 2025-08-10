"""Initialize Lium CLI configuration."""

import os
import sys
from configparser import ConfigParser
from pathlib import Path

import click
from rich.prompt import Prompt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..utils import console, handle_errors


def ensure_config_dir() -> Path:
    """Ensure ~/.lium directory exists."""
    config_dir = Path.home() / ".lium"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_or_create_config() -> ConfigParser:
    """Get existing config or create new one."""
    config_file = Path.home() / ".lium" / "config.ini"
    config = ConfigParser()
    
    if config_file.exists():
        config.read(config_file)
    
    return config


def save_config(config: ConfigParser) -> None:
    """Save config to file."""
    config_file = Path.home() / ".lium" / "config.ini"
    with open(config_file, 'w') as f:
        config.write(f)


def setup_api_key(config: ConfigParser) -> None:
    """Setup API key in config."""
    # Check if already set
    if config.has_section('api') and config.get('api', 'api_key', fallback=None):
        current_key = config.get('api', 'api_key')
        masked_key = current_key[:8] + '...' + current_key[-4:] if len(current_key) > 12 else '***'
        console.print(f"[green]✓[/green] API key already configured: {masked_key}")
        
        if Prompt.ask("[yellow]Update API key?[/yellow]", choices=["y", "n"], default="n") == "n":
            return
    
    # Prompt for new key
    api_key = Prompt.ask(
        "[cyan]Enter your Lium API key (get from https://lium.ai/api-keys)[/cyan]"
    )
    
    if not api_key:
        console.print("[red]No API key provided[/red]")
        return
    
    # Save to config
    if not config.has_section('api'):
        config.add_section('api')
    config.set('api', 'api_key', api_key)
    console.print(f"[green]✓[/green] API key saved")


def setup_ssh_key(config: ConfigParser) -> None:
    """Setup SSH key path in config."""
    # Find available SSH keys
    ssh_dir = Path.home() / ".ssh"
    available_keys = []
    
    for key_name in ["id_ed25519", "id_rsa", "id_ecdsa"]:
        key_path = ssh_dir / key_name
        if key_path.exists():
            available_keys.append(key_path)
    
    if not available_keys:
        console.print("[yellow]⚠[/yellow] No SSH keys found in ~/.ssh/")
        console.print("[dim]You may need to generate one with: ssh-keygen -t ed25519[/dim]")
        return
    
    # Auto-select if only one
    if len(available_keys) == 1:
        selected_key = available_keys[0]
        console.print(f"[green]✓[/green] Using SSH key: {selected_key}")
    else:
        # Let user choose
        console.print("[cyan]Multiple SSH keys found:[/cyan]")
        for i, key in enumerate(available_keys, 1):
            console.print(f"  {i}. {key}")
        
        choice = Prompt.ask(
            "Select SSH key",
            choices=[str(i) for i in range(1, len(available_keys) + 1)],
            default="1"
        )
        selected_key = available_keys[int(choice) - 1]
    
    # Save to config
    if not config.has_section('ssh'):
        config.add_section('ssh')
    config.set('ssh', 'key_path', str(selected_key))
    console.print(f"[green]✓[/green] SSH key configured")


def show_config(config: ConfigParser) -> None:
    """Display current configuration."""
    console.print("\n[bold]Current Configuration:[/bold]")
    console.print(f"[dim]Location: ~/.lium/config.ini[/dim]\n")
    
    for section in config.sections():
        console.print(f"[yellow][{section}][/yellow]")
        for key, value in config.items(section):
            # Mask API key
            if key == 'api_key' and value:
                display_value = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
            else:
                display_value = value
            console.print(f"  {key} = {display_value}")
        console.print()


@click.command("init")
@handle_errors
def init_command():
    """Initialize Lium CLI configuration.
    
    Sets up API key and SSH key configuration for first-time users.
    
    Example:
      lium init    # Interactive setup wizard
    """
    console.print("[bold]Lium CLI Setup[/bold]\n")
    
    # Ensure config directory exists
    ensure_config_dir()
    
    # Load or create config
    config = get_or_create_config()
    
    # Setup API key
    setup_api_key(config)
    
    # Setup SSH key
    setup_ssh_key(config)
    
    # Save config
    save_config(config)
    
    # Show final config
    show_config(config)
    
    console.print("[green]✓[/green] Lium CLI initialized successfully!")
    console.print("[dim]You can now use 'lium ls' to list available executors[/dim]")