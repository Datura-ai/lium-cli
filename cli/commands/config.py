"""Configuration management commands."""

import os
import sys
import click
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..config import config
from ..utils import console, handle_errors


def _config_show(show_all: bool = False) -> None:
    """Display entire configuration."""
    config_data = config.get_all()
    
    if not config_data:
        console.info("Configuration is empty")
        console.dim(f"Location: {config.get_config_path()}")
        return
    
    console.info("Configuration:")
    console.dim(f"Location: {config.get_config_path()}")
    
    # Skip internal sections that are not user-relevant (unless --all is used)
    skip_sections = {'last_selection'} if not show_all else set()
    
    # Show sections in logical order
    section_order = ['api', 'ssh', 'ui', 'template']
    shown_sections = set()
    
    for section_name in section_order:
        if section_name in config_data and section_name not in skip_sections:
            values = config_data[section_name]
            console.info(f"\n\\[{section_name}]")
            for key, value in values.items():
                # Mask sensitive values
                if key in ['api_key'] and value:
                    display_value = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
                elif key == 'data' and len(str(value)) > 100:
                    display_value = str(value)[:100] + '...'
                else:
                    display_value = value
                console.info(f"{key} = {display_value}")
            shown_sections.add(section_name)
    
    # Show remaining sections
    for section, values in config_data.items():
        if section in skip_sections or section in shown_sections:
            continue
        console.info(f"\n\\[{section}]")
        for key, value in values.items():
            if key == 'data' and len(str(value)) > 100:
                display_value = str(value)[:100] + '...'
            else:
                display_value = value
            console.info(f"{key} = {display_value}")
    
    # Show hidden sections summary (only if not showing all)
    if not show_all:
        hidden_sections = [s for s in config_data.keys() if s in {'last_selection'}]
        if hidden_sections:
            console.info(f"\nHidden: {', '.join(hidden_sections)} (use --all to show)")
    
    console.info("")  # Final newline


def _get_styled_value(value: str, key: str) -> str:
    """Get styled value for display."""
    if key.endswith('api_key') and value:
        # Mask API key
        return value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
    return value


@click.group(name="config", help="Manage Lium CLI configuration.")
def config_command():
    pass


@config_command.command(name="get", help="Get a configuration value.")
@click.argument("key")
@handle_errors
def config_get(key: str):
    """Get a configuration value."""
    value = config.get(key)
    if value is not None:
        styled_value = _get_styled_value(value, key)
        console.info(styled_value)
    else:
        console.error(f"Key '{key}' not found.")


@config_command.command(name="set", help="Set a configuration value. Run without value for interactive mode.")
@click.argument("key")
@click.argument("value", required=False)
@handle_errors
def config_set(key: str, value: Optional[str]):
    """Set a configuration value."""
    # Special handling for interactive keys
    if key in ['template.default_id', 'ui.theme', 'api.api_key'] and not value:
        console.info(f"Setting {key} interactively...")
    
    config.set(key, value or "")
    
    # Get the actual value that was set (might be different for interactive keys)
    new_value = config.get(key)
    if new_value:
        styled_value = _get_styled_value(new_value, key)
        console.success(f"✓ Set {key} = {styled_value}")
    else:
        console.error(f"Failed to set {key}")


@config_command.command(name="unset", help="Remove a configuration value.")
@click.argument("key")
@handle_errors
def config_unset(key: str):
    """Remove a configuration value."""
    if config.unset(key):
        console.success(f"✓ Removed {key}")
    else:
        console.warning(f"Key '{key}' not found")


@config_command.command(name="show", help="Show the entire configuration.")
@click.option("--all", is_flag=True, help="Show all sections including internal data.")
@handle_errors
def config_show(all: bool):
    """Show the entire configuration."""
    _config_show(show_all=all)


@config_command.command(name="path", help="Show the path to the configuration file.")
@handle_errors
def config_path():
    """Show the path to the configuration file."""
    console.info(str(config.get_config_path()))


@config_command.command(name="edit", help="Open configuration file in default editor.")
@handle_errors
def config_edit():
    """Open configuration file in default editor."""
    import subprocess
    import sys
    
    config_file = config.get_config_path()
    editor = os.environ.get('EDITOR', 'nano' if sys.platform != 'win32' else 'notepad')
    
    try:
        subprocess.run([editor, str(config_file)], check=True)
        console.success("✓ Configuration file opened")
    except subprocess.CalledProcessError:
        console.error(f"Failed to open editor: {editor}")
    except FileNotFoundError:
        console.error(f"Editor not found: {editor}")
        console.dim("Set EDITOR environment variable to use a different editor")


@config_command.command(name="reset", help="Reset configuration to defaults.")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt.")
@handle_errors
def config_reset(confirm: bool):
    """Reset configuration to defaults."""
    from rich.prompt import Confirm
    
    if not confirm:
        if not Confirm.ask("[yellow]This will delete all configuration. Continue?[/yellow]", default=False):
            console.info("Reset cancelled")
            return
    
    config_file = config.get_config_path()
    if config_file.exists():
        config_file.unlink()
        console.success("✓ Configuration reset to defaults")
    else:
        console.info("Configuration already empty")