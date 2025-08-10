"""Plugin loading system for Lium CLI."""
import importlib.metadata
import click
from typing import Optional


def load_plugins(cli_group: click.Group) -> None:
    """Load all installed plugins via entry points.
    
    Plugins are discovered through the 'lium.plugins' entry point group.
    Each plugin must provide a get_command() function that returns a Click command.
    
    Args:
        cli_group: The main CLI group to add plugin commands to
    """
    try:
        # Discover all plugins in the 'lium.plugins' namespace
        discovered = importlib.metadata.entry_points(group='lium.plugins')
        
        for entry_point in discovered:
            try:
                # Load the plugin module
                plugin = entry_point.load()
                
                # Plugin must have get_command() function
                if hasattr(plugin, 'get_command'):
                    command = plugin.get_command()
                    if isinstance(command, click.Command):
                        cli_group.add_command(command)
                        # Silent loading - only show errors
                else:
                    # Only warn if plugin exists but is malformed
                    pass
                    
            except Exception:
                # Silent fail - plugin not available
                pass
    except Exception:
        # If entry_points discovery fails, continue without plugins
        pass


def check_plugin_installed(plugin_name: str) -> bool:
    """Check if a specific plugin is installed.
    
    Args:
        plugin_name: Name of the plugin package to check
        
    Returns:
        True if plugin is installed, False otherwise
    """
    try:
        importlib.import_module(plugin_name)
        return True
    except ImportError:
        return False