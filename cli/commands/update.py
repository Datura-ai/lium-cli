"""Update pod configuration command."""
import os
import sys
import json
import re
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
        try:
            # Install Jupyter without loading status to avoid showing raw errors
            result = lium.install_jupyter(pod, jupyter)

            all_pods = lium.ps()
            updated_pod = next((p for p in all_pods if p.id == pod.id), None)

            # Display Jupyter information
            if updated_pod and hasattr(updated_pod, 'jupyter_url') and updated_pod.jupyter_url:
                console.info(f"Jupyter URL: {updated_pod.jupyter_url}")

            if updated_pod and hasattr(updated_pod, 'jupyter_installation_status') and updated_pod.jupyter_installation_status:
                status_color = "green" if updated_pod.jupyter_installation_status == "SUCCESS" else "yellow"
                console.info(f"Installation Status: [{status_color}]{updated_pod.jupyter_installation_status}[/{status_color}]")

        except Exception as e:
            # Try to extract clean error message from API response
            error_msg = str(e)

            # Look for JSON in the error message and extract the "message" field
            json_match = re.search(r'"message"\s*:\s*"([^"]+)"', error_msg)
            if json_match:
                clean_message = json_match.group(1)
                console.error(clean_message)
            else:
                # Fallback to generic message if we can't parse it
                console.error("Failed to install Jupyter Notebook. Ensure port is avaialble on the pod")

            return
