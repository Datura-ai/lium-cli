"""Theme management command."""

import os
import sys
import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..themed_console import ThemedConsole
from ..utils import handle_errors


def _show_theme_preview(console: ThemedConsole, current_theme: str, resolved_theme: str) -> None:
    """Show a preview of colors in the current theme."""
    console.success("  ✓ Success messages")
    console.error("  ✗ Error messages") 
    console.warning("  ⚠ Warning messages")
    console.info("  ℹ Info messages")
    console.dim("  Dimmed/muted text")
    
    # Show pod status colors  
    console.print(f"  Pod statuses: ", end="")
    running_color = console.pod_status_color("RUNNING")
    stopped_color = console.pod_status_color("STOPPED") 
    pending_color = console.pod_status_color("PENDING")
    console.info(f"[{running_color}]RUNNING[/] [{stopped_color}]STOPPED[/] [{pending_color}]PENDING[/]")


@click.command("theme")
@click.argument("theme_name", type=click.Choice(["dark", "light", "auto"]), required=False)
@handle_errors
def theme_command(theme_name: str | None):
    """Manage CLI color theme.
    
    \b
    Available themes:
      auto   - Automatically detect OS theme (default)
      dark   - Dark theme for dark terminals
      light  - Light theme for light terminals
    
    \b
    Examples:
      lium theme         # Show current theme
      lium theme auto    # Enable auto-detection
      lium theme dark    # Force dark theme
      lium theme light   # Force light theme
    """
    console = ThemedConsole()
    
    if theme_name is None:
        # Show current theme info
        current = console.get_current_theme_name()
        resolved = console.get_resolved_theme_name()
        
        console.info(f"Current theme: {current}")
        if current == "auto":
            console.dim(f"  Detected: {resolved}")
        
        console.dim("\nAvailable themes:")
        console.dim("  auto   - Auto-detect OS theme")
        console.dim("  dark   - Dark theme for dark terminals") 
        console.dim("  light  - Light theme for light terminals")
        
        # Show color preview
        console.dim("\nColor preview:")
        _show_theme_preview(console, current, resolved)
        return
    
    # Switch theme
    try:
        old_theme = console.get_current_theme_name()
        console.switch_theme(theme_name)
        
        if theme_name == old_theme:
            console.info(f"Already using {theme_name} theme")
        else:
            console.success(f"✓ Switched to {theme_name} theme")
            
        if theme_name == "auto":
            resolved = console.get_resolved_theme_name() 
            console.dim(f"  Auto-detected: {resolved}")
            
    except ValueError as e:
        console.error(f"Error: {e}")
        return