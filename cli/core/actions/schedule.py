"""Termination scheduling action."""

from datetime import datetime, timezone
from typing import Optional

from ..context import UpContext
from .base import BaseAction


class ScheduleTerminationIfNeeded(BaseAction):
    """Schedule automatic pod termination if requested."""

    def should_run(self, ctx: UpContext) -> bool:
        """Only run if termination time was specified."""
        return ctx.opts.termination_time is not None

    def execute(self, ctx: UpContext) -> Optional[bool]:
        """Schedule the termination."""
        termination_time = ctx.opts.termination_time

        with ctx.reporter.step("Scheduling termination"):
            termination_time_str = termination_time.isoformat()
            ctx.lium.schedule_termination(ctx.pod_id, termination_time_str)

        # Display success message after the step completes
        time_str = termination_time.strftime("%Y-%m-%d %H:%M UTC")
        time_delta = termination_time - datetime.now(timezone.utc)
        hours_until = time_delta.total_seconds() / 3600
        ctx.reporter.success(f"Scheduled termination at {time_str} ({hours_until:.1f}h from now)")

        return True
