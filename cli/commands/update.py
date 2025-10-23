"""Update pod configuration command."""
import os
import sys
from typing import Optional

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lium_sdk import Lium
from ..utils import console, handle_errors, loading_status, parse_targets


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
    # Validate that at least one option is provided
    if not jupyter:
        console.error("No updates specified. Use --jupyter to install Jupyter Notebook.")
        console.info("Example: lium update 1 --jupyter 8888")
        return

    lium = Lium()

    # Get pods and resolve target
    with loading_status("Loading pods", ""):
        all_pods = lium.ps()

    pods = parse_targets(target, all_pods)
    pod = pods[0] if pods else None

    if not pod:
        console.error(f"Pod '{target}' not found")
        # Show available pods
        if all_pods:
            console.dim("\nAvailable pods:")
            for i, p in enumerate(all_pods, 1):
                status_color = console.pod_status_color(p.status)
                console.info(f"  {i}. [{status_color}]{p.huid}[/{status_color}] ({p.status})")
        return

    # Check if pod is running
    if pod.status != "RUNNING":
        console.warning(f"Pod '{pod.huid}' is {pod.status}")
        if pod.status in ["STOPPED", "FAILED"]:
            console.error("Cannot update a stopped or failed pod")
            return

    # Install Jupyter if requested
    if jupyter:
        with loading_status(f"Installing Jupyter Notebook on {pod.huid}", ""):
            result = lium.install_jupyter(pod, jupyter)

        console.success(f"Jupyter Notebook installing... you can check the status with 'lium ps --details' ({pod.huid} (port {jupyter})")
