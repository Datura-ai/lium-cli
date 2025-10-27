"""Executor-related actions."""

from typing import Optional

from cli.lium_sdk import ExecutorInfo
from ..context import UpContext
from .base import BaseAction
from ..helpers import (
    _find_executor_by_id,
    _auto_select_executor,
    select_executor,
)
from rich.prompt import Confirm


class ResolveExecutor(BaseAction):
    """Resolve which executor to use for the pod."""

    def counts_as_step(self, ctx: UpContext) -> bool:
        """Only counts as step for non-interactive executor resolution."""
        opts = ctx.opts
        # Only count as step if using filters (shows "Finding best executor")
        return opts.executor_id is not None or opts.gpu or opts.count or opts.country

    def execute(self, ctx: UpContext) -> Optional[bool]:
        """Resolve executor from ID, filters, or interactive selection."""
        opts = ctx.opts

        if opts.executor_id:
            # Explicit executor ID provided
            with ctx.reporter.step("Finding executor"):
                executor = _find_executor_by_id(ctx.lium, opts.executor_id, opts.ports)
            if not executor:
                return False  # Stop pipeline
        elif opts.gpu or opts.count or opts.country:
            # Use filters to auto-select
            with ctx.reporter.step("Finding best executor"):
                executor = _auto_select_executor(
                    ctx.lium, opts.gpu, opts.count, opts.country, opts.ports
                )
            if not executor:
                return False  # Stop pipeline
            # Show selection after step completes
            ctx.reporter.success(
                f"Selected: {executor.huid} ({executor.gpu_count}×{executor.gpu_type}) "
                f"at ${executor.price_per_hour:.2f}/h"
            )
        else:
            # Interactive selection (no step wrapper for interactive)
            executor = select_executor(ctx.lium, ports=opts.ports)
            if not executor:
                return False  # Stop pipeline
            # Show confirmation
            ctx.reporter.success(f"Selected: {executor.huid}")

        ctx.executor = executor
        return True


class ConfirmCreation(BaseAction):
    """Confirm pod creation with the user (unless --yes flag is set)."""

    def should_run(self, ctx: UpContext) -> bool:
        """Only run if confirmation is needed."""
        return not ctx.opts.skip_confirm

    def counts_as_step(self, ctx: UpContext) -> bool:
        """Confirmation doesn't count as a progress step."""
        return False

    def execute(self, ctx: UpContext) -> Optional[bool]:
        """Ask user to confirm pod creation."""
        executor = ctx.executor
        confirm_msg = (
            f"Proceed to rent {executor.huid} "
            f"({executor.gpu_count}×{executor.gpu_type}) "
            f"at ${executor.price_per_hour:.2f}/h?"
        )

        if not Confirm.ask(confirm_msg, default=True):
            ctx.reporter.warning("Cancelled")
            return False  # Stop pipeline

        return True
