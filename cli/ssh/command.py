"""SSH command implementation."""

import click

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors
from . import validation, parsing
from .actions import SshAction


@click.command("ssh")
@click.argument("target")
@handle_errors
def ssh_command(target: str):
    """Open SSH session to a GPU pod.

    \b
    TARGET: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)

    \b
    Examples:
      lium ssh 1                    # SSH to pod #1 from ps
      lium ssh eager-wolf-aa        # SSH to specific pod
    """

    # Validate
    valid, error = validation.validate(target)
    if not valid:
        ui.error(error)
        return

    # Load data
    lium = Lium()
    all_pods = ui.load("Loading pods", lambda: lium.ps())

    if not all_pods:
        ui.warning("No active pods")
        return

    # Parse
    parsed, error = parsing.parse(target, all_pods)
    if error:
        ui.error(error)
        return

    pod = parsed.get("pod")

    # Execute
    ctx = {"lium": lium, "pod": pod}

    action = SshAction()
    result = action.execute(ctx)

    if not result.ok:
        if result.error:
            ui.error(result.error)
        elif result.data.get("exit_code"):
            ui.dim(f"SSH session ended with exit code {result.data['exit_code']}")
