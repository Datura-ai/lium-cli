"""Reporter classes for controlling command output."""

import time
from contextlib import contextmanager
from typing import Optional, Generator

from ..utils import console, loading_status, timed_step_status


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


class NullReporter:
    """No-op reporter for testing or dry-run mode."""

    def set_total_steps(self, total: int) -> None:
        """No-op."""
        pass

    @contextmanager
    def step(self, title: str, done: Optional[str] = None) -> Generator[None, None, None]:
        """No-op context manager."""
        yield

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
