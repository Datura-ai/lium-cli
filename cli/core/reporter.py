"""Reporter classes for controlling command output."""

import time
from contextlib import contextmanager
from typing import Optional, Generator, List, Tuple

from ..utils import console, loading_status, timed_step_status
from rich.prompt import Confirm


class Reporter:
    """Default reporter that displays progress with spinners and timed steps."""

    def __init__(self):
        self.current_step = 0
        self.total_steps = 0

    def set_total_steps(self, total: int) -> None:
        """Set the total number of steps for progress tracking."""
        self.total_steps = total

    @contextmanager
    def step(self, title: str, done: Optional[str] = None) -> Generator[None, None, None]:
        """Execute a step with timed progress indicator.

        Args:
            title: Step description (e.g., "Renting machine")
            done: Optional completion message
        """
        if self.total_steps > 0:
            self.current_step += 1
            with timed_step_status(self.current_step, self.total_steps, title):
                yield
        else:
            # Fallback to simple loading status if no total steps set
            with loading_status(title, done or ""):
                yield

    def preflight_block(self, items: List[Tuple[str, str]]) -> None:
        """Display a pre-flight information block.

        Args:
            items: List of (label, value) tuples
                  - If label starts with "→", format as section header
                  - If label is empty, format as continuation line
                  - Otherwise, format as "   label: value"
        """
        for label, value in items:
            if label.startswith("→"):
                console.print(f"{label} {value}")
            elif label == "":
                console.print(f"   {value}")
            else:
                console.print(f"   {label}: {value}")
        console.print()

    def summary_block(self, title: str, items: List[Tuple[str, str]], separator: str = "─" * 50) -> None:
        """Display a summary block with separators.

        Args:
            title: Main title line (e.g., "✓ Pod ready: calm-eagle-38")
            items: List of (label, value) tuples to display
            separator: Line separator character/string
        """
        console.print(f"\n{separator}")
        console.success(title)
        for label, value in items:
            console.print(f"   {label}: {value}")
        console.print(f"{separator}\n")

    def confirm(self, message: str, default: bool = True) -> bool:
        """Ask for user confirmation.

        Args:
            message: Confirmation prompt
            default: Default response if user just presses enter

        Returns:
            True if user confirmed, False otherwise
        """
        return Confirm.ask(message, default=default)

    def info(self, message: str) -> None:
        """Display an info message."""
        console.info(message)

    def success(self, message: str) -> None:
        """Display a success message."""
        console.success(message)

    def error(self, message: str) -> None:
        """Display an error message."""
        console.error(message)

    def warning(self, message: str) -> None:
        """Display a warning message."""
        console.warning(message)

    def dim(self, message: str) -> None:
        """Display a dimmed/secondary message."""
        console.dim(message)

    def print(self, message: Optional[str] = "", style: Optional[str] = None) -> None:
        """Print a message with optional styling.

        Args:
            message: Message to print (empty string prints blank line)
            style: Optional rich style string (e.g., "bold cyan", "dim")
        """
        console.print(message, style=style)


class NullReporter:
    """No-op reporter for testing or dry-run mode."""

    def set_total_steps(self, total: int) -> None:
        """No-op."""
        pass

    @contextmanager
    def step(self, title: str, done: Optional[str] = None) -> Generator[None, None, None]:
        """No-op context manager."""
        yield

    def preflight_block(self, items: List[Tuple[str, str]]) -> None:
        """No-op."""
        pass

    def summary_block(self, title: str, items: List[Tuple[str, str]], separator: str = "─" * 50) -> None:
        """No-op."""
        pass

    def confirm(self, message: str, default: bool = True) -> bool:
        """No-op - always returns True."""
        return True

    def info(self, message: str) -> None:
        """No-op."""
        pass

    def success(self, message: str) -> None:
        """No-op."""
        pass

    def error(self, message: str) -> None:
        """No-op."""
        pass

    def warning(self, message: str) -> None:
        """No-op."""
        pass

    def dim(self, message: str) -> None:
        """No-op."""
        pass
