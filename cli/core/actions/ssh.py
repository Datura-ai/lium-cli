"""SSH connection action."""

from typing import Optional

from ..context import UpContext
from .base import BaseAction
from ...commands.ssh import get_ssh_method_and_pod, ssh_to_pod


class ConnectSSH(BaseAction):
    """Connect to the pod via SSH."""

    def execute(self, ctx: UpContext) -> Optional[bool]:
        """Establish SSH connection and display summary."""
        with ctx.reporter.step("Connecting SSH"):
            ssh_cmd, pod = get_ssh_method_and_pod(ctx.opts.name)
            ctx.ssh_cmd = ssh_cmd
            ctx.pod = pod

        # Display summary after all steps are done
        ctx.reporter.success(f"✓ Pod ready: {ctx.opts.name}")

        if ctx.jupyter_url:
            ctx.reporter.info(f"Jupyter: {ctx.jupyter_url}")

        if ctx.opts.termination_time:
            time_str = ctx.opts.termination_time.strftime("%Y-%m-%d %H:%M UTC")
            ctx.reporter.info(f"Auto-terminate: {time_str}")

        # Connect to SSH
        ssh_to_pod(ssh_cmd, pod)

        return True
