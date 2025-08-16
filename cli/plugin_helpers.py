"""Helper utilities for Lium CLI plugins."""

import click
from typing import Optional
from .themed_console import ThemedConsole


def get_console(ctx: Optional[click.Context] = None) -> ThemedConsole:
    """Get themed console instance from CLI context.
    
    This is the recommended way for plugins to get access to the themed console.
    
    Args:
        ctx: Click context (if None, will try to get current context)
        
    Returns:
        ThemedConsole instance with current theme settings
        
    Example:
        ```python
        @click.command()
        @click.pass_context
        def my_plugin_command(ctx):
            console = get_console(ctx)
            console.success("✓ Success message with theme!")
            console.error("✗ Error message with theme!")
        ```
    """
    if ctx is None:
        ctx = click.get_current_context()
    
    # Try to get console from context
    if ctx and ctx.obj and 'console' in ctx.obj:
        return ctx.obj['console']
    
    # Fallback: create new instance
    return ThemedConsole()


