"""CLI utilities and decorators."""
from functools import wraps
from contextlib import contextmanager
from rich.console import Console
from rich.status import Status
from lium_sdk import LiumError

console = Console()


@contextmanager
def loading_status(message: str, success_message: str = ""):
    """Universal context manager to show loading status."""
    status = Status(f"[cyan]{message}...[/cyan]", console=console)
    status.start()
    try:
        yield
        if success_message:
            console.print(f"[green]✓[/green] {success_message}")
    except Exception as e:
        console.print(f"[red]✗ Failed: {e}[/red]")
        raise
    finally:
        status.stop()


def handle_errors(func):
    """Decorator to handle CLI errors gracefully."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except LiumError as e:
            console.print(f"[red]Error: {e}[/red]")
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
    return wrapper