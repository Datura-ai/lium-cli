"""Base action class for the pipeline."""

from abc import ABC, abstractmethod
from typing import Optional

from ..context import UpContext


class BaseAction(ABC):
    """Base class for all pipeline actions.

    Actions are the building blocks of the command pipeline.
    Each action:
    1. Checks if it should run (should_run)
    2. Executes its logic (execute)
    3. Updates the context with results
    """

    def should_run(self, ctx: UpContext) -> bool:
        """Determine if this action should execute.

        Override this to conditionally skip actions based on context state.

        Args:
            ctx: The pipeline context

        Returns:
            True if the action should execute, False to skip
        """
        return True

    def counts_as_step(self, ctx: UpContext) -> bool:
        """Determine if this action counts as a progress step.

        Override this if the action doesn't always show a progress indicator.
        For example, interactive prompts or actions that only validate.

        Args:
            ctx: The pipeline context

        Returns:
            True if this action should count in the total steps
        """
        return True

    @abstractmethod
    def execute(self, ctx: UpContext) -> Optional[bool]:
        """Execute the action's main logic.

        Args:
            ctx: The pipeline context (read and modify as needed)

        Returns:
            - None or True: Continue pipeline
            - False: Stop pipeline execution
        """
        pass
