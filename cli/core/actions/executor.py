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
    """Resolve which executor to use for the pod.

    This is a pre-flight action that gathers executor information silently.
    The selected executor will be shown in the pre-flight summary block.
    """

    def execute(self, ctx: UpContext) -> Optional[bool]:
        """Resolve executor from ID, filters, or interactive selection."""
        opts = ctx.opts

        try:
            if opts.executor_id:
                # Explicit executor ID provided
                executor = _find_executor_by_id(ctx.lium, opts.executor_id, opts.ports)
                if not executor:
                    return False
            elif opts.gpu or opts.count or opts.country:
                # Use filters to auto-select
                executor = _auto_select_executor(
                    ctx.lium, opts.gpu, opts.count, opts.country, opts.ports
                )
                if not executor:
                    return False
            else:
                # Interactive selection
                executor = select_executor(ctx.lium, ports=opts.ports)
                if not executor:
                    return False

            ctx.executor = executor
            return True

        except Exception as e:
            ctx.reporter.error(f"Failed to resolve executor: {e}")
            return False


class ResolveTemplate(BaseAction):
    """Resolve template information for the pod.

    This is a pre-flight action that loads template details silently.
    The template info will be shown in the pre-flight summary block.
    """

    def should_run(self, ctx: UpContext) -> bool:
        """Only run if template_id is specified."""
        return ctx.opts.template_id is not None

    def execute(self, ctx: UpContext) -> Optional[bool]:
        """Load template information."""
        try:
            template = ctx.lium.get_template(ctx.opts.template_id)
            ctx.template = template
            return True
        except Exception as e:
            ctx.reporter.error(f"Failed to load template: {e}")
            return False
