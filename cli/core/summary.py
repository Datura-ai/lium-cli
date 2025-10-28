"""Summary builders for command output formatting."""

from abc import ABC, abstractmethod
from typing import Tuple, List


class SummaryBuilder(ABC):
    """Base class for building command-specific summaries.

    This keeps the Reporter generic and reusable while allowing
    each command to define its own pre-flight and completion displays.
    """

    @abstractmethod
    def build_preflight(self, ctx) -> List[Tuple[str, str]]:
        """Build pre-flight information display.

        Args:
            ctx: Command context containing gathered information

        Returns:
            List of (label, value) tuples to display
        """
        pass

    @abstractmethod
    def build_completion(self, ctx) -> Tuple[str, List[Tuple[str, str]]]:
        """Build completion summary display.

        Args:
            ctx: Command context with execution results

        Returns:
            Tuple of (title, items) where:
            - title: Success message (e.g., "✓ Pod ready: calm-eagle-38")
            - items: List of (label, value) tuples to display
        """
        pass
