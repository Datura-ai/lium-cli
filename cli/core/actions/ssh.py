"""SSH preparation action."""

from typing import Optional

from ..context import UpContext
from .base import BaseAction
from ...commands.ssh import get_ssh_method_and_pod


class PrepareSSH(BaseAction):
    """Prepare SSH connection details (does not actually connect)."""

    def execute(self, ctx: UpContext) -> Optional[bool]:
        """Prepare SSH command and store in context for summary."""
        with ctx.reporter.step("Preparing connection"):
            ssh_cmd, pod = get_ssh_method_and_pod(ctx.opts.name)
            ctx.ssh_cmd = ssh_cmd
            ctx.pod = pod

        return True
