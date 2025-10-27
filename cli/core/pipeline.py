"""Pipeline orchestrator for executing actions in sequence."""

from typing import List

from .context import UpContext
from .actions.base import BaseAction


def run_pipeline(ctx: UpContext, actions: List[BaseAction]) -> None:
    """Execute a sequence of actions with the given context.

    Args:
        ctx: The context object containing state and dependencies
        actions: List of actions to execute in order

    The pipeline will:
    1. Calculate total steps (counting non-skipped actions)
    2. Execute each action in sequence
    3. Stop if any action returns False
    """
    # Count total steps for progress reporting (only actions that show progress)
    total_steps = sum(1 for action in actions if action.should_run(ctx) and action.counts_as_step(ctx))
    ctx.reporter.set_total_steps(total_steps)

    # Execute each action
    for action in actions:
        if not action.should_run(ctx):
            continue

        # Execute the action
        try:
            result = action.execute(ctx)
            if result is False:
                # Action signaled to stop the pipeline
                return
        except Exception as e:
            ctx.reporter.error(f"Action {action.__class__.__name__} failed: {e}")
            raise
