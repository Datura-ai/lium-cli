"""Update command implementation."""

from typing import Optional

import click

from cli.lium_sdk import Lium
from cli import ui
from cli.utils import handle_errors
from . import validation, parsing
from .actions import InstallJupyterAction


@click.command("update")
@click.argument("target")
@click.option("--jupyter", type=int, help="Install Jupyter Notebook on specified internal port")
@handle_errors
def update_command(target: str, jupyter: Optional[int]):
    """Update configuration of a running pod.

    \b
    TARGET: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)

    \b
    Examples:
      lium update 1 --jupyter 8888          # Install Jupyter on pod #1
      lium update eager-wolf-aa --jupyter 8889  # Install Jupyter on specific pod
    """

    # Validate
    valid, error = validation.validate(target, jupyter)
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
    ctx = {"lium": lium, "pod": pod, "port": jupyter}

    action = InstallJupyterAction()

    with ui.loading("Installing Jupyter Notebook"):
        result = action.execute(ctx)

    if not result.ok:
        ui.error(result.error or "Failed to install Jupyter Notebook")
        return

    jupyter_url = result.data.get("jupyter_url")
    if jupyter_url:
        ui.success("Jupyter Notebook installed successfully")
        ui.info(f"URL: {jupyter_url}")
