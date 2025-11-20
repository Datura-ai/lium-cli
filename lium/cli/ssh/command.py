"""SSH command implementation."""

import shutil
import subprocess
from typing import Tuple
import click

from lium.sdk import Lium, PodInfo
from lium.cli import ui
from lium.cli.utils import handle_errors, parse_targets
from . import validation, parsing
from .actions import SshAction


def get_ssh_method_and_pod(target: str) -> Tuple[str, PodInfo]:
    """Helper function that check method for SSH."""
    if not shutil.which("ssh"):
        ui.error("Error: 'ssh' command not found. Please install an SSH client.")
        return None, None

    lium = Lium()
    all_pods = lium.ps()

    pods = parse_targets(target, all_pods)
    pod = pods[0] if pods else None

    if not pod:
        return None, None

    if not pod.ssh_cmd:
        ui.error(f"No SSH connection available for pod '{pod.huid}'")
        return None, None

    try:
        ssh_cmd = lium.ssh(pod)
        ssh_cmd += " -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        return ssh_cmd, pod
    except ValueError:
        ssh_cmd = pod.ssh_cmd + " -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        return ssh_cmd, pod


def ssh_to_pod(ssh_cmd: str, pod: PodInfo) -> None:
    """Helper function to SSH to a pod."""
    try:
        result = subprocess.run(ssh_cmd, shell=True, check=False)

        if result.returncode != 0 and result.returncode != 255:
            ui.dim(f"\nSSH session ended with exit code {result.returncode}")
    except KeyboardInterrupt:
        ui.warning("\nSSH session interrupted")
    except Exception as e:
        ui.error(f"Error executing SSH: {e}")


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
