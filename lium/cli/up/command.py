from typing import Optional
import click

from lium.sdk import Lium, ExecutorInfo
from lium.cli import ui
from lium.cli.utils import handle_errors, ensure_config
from lium.cli.completion import get_gpu_completions
from . import validation, parsing
from .actions import (
    ResolveExecutorAction,
    ResolveTemplateAction,
    CreateVolumeAction,
    RentPodAction,
    WaitReadyAction,
    ScheduleTerminationAction,
    InstallJupyterAction,
    PrepareSSHAction,
)


@click.command("up")
@click.argument("executor_id", required=False)
@click.option("--name", "-n", help="Custom pod name")
@click.option("--template_id", "-t", help="Template ID")
@click.option("--volume", "-v", help="Volume spec: 'id:<HUID>' or 'new:name=<NAME>[,desc=<DESC>]'")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--gpu", help="Filter executors by GPU type (e.g., H200, A6000)", shell_complete=get_gpu_completions)
@click.option("--count", "-c", type=int, help="Number of GPUs per pod")
@click.option("--country", help="Filter executors by ISO country code (e.g., US, FR)")
@click.option("--ports", "-p", type=int, help="Minimum number of available ports required")
@click.option("--ttl", help="Auto-terminate after duration (e.g., 6h, 45m, 2d)")
@click.option("--until", help="Auto-terminate at time in local timezone (e.g., 'today 23:00', 'tomorrow 01:00', '2025-10-20 15:30')")
@click.option("--jupyter", is_flag=True, help="Install Jupyter Notebook (automatically selects available port)")
@handle_errors
def up_command(
    executor_id: Optional[str],
    name: Optional[str],
    template_id: Optional[str],
    volume: Optional[str],
    yes: bool,
    gpu: Optional[str],
    count: Optional[int],
    country: Optional[str],
    ports: Optional[int],
    ttl: Optional[str],
    until: Optional[str],
    jupyter: bool
):
    """\b
    Create a new GPU pod on an executor.
    \b
    EXECUTOR_ID: Executor UUID, HUID, or index from last 'lium ls'.
    If not provided, uses filters to auto-select best executor.
    \b
    Examples:
      lium up cosmic-hawk-f2                # Create pod on specific executor
      lium up 1                             # Create pod on executor #1 from last ls
      lium up --gpu H200                    # Auto-select best H200 executor
      lium up --gpu A6000 -c 2              # Auto-select best 2×A6000 executor
      lium up --country US                  # Auto-select best executor in US
      lium up --gpu H200 --country FR       # Combine multiple filters
      lium up --ports 5                     # Auto-select with minimum 5 ports
      lium up 1 --name my-pod               # Create with custom name
      lium up 1 --volume id:brave-fox-3a    # Attach existing volume by HUID
      lium up 1 --volume new:name=my-data   # Create and attach new volume
      lium up 1 --volume new:name=my-data,desc="Training data"  # With description
      lium up 1 --ttl 6h                    # Auto-terminate after 6 hours
      lium up 1 --until "today 23:00"       # Auto-terminate at 23:00 local time today
      lium up 1 --until "tomorrow 01:00"    # Auto-terminate at 01:00 local time tomorrow
      lium up 1 --jupyter                   # Install Jupyter Notebook (auto-selects port)
      LIUM_DEBUG=1 lium up 1 --jupyter      # Show debug information
    """
    ensure_config()

    valid, error = validation.validate(executor_id, gpu, count, country, ttl, until)
    if not valid:
        ui.error(error)
        return

    parsed, error = parsing.parse(ttl, until, volume)
    if error:
        ui.error(error)
        return

    termination_time = parsed.get("termination_time")
    volume_id = parsed.get("volume_id")
    volume_create_params = parsed.get("volume_create_params")

    lium = Lium()

    action = ResolveExecutorAction()
    result = ui.load(
        "Finding executor",
        lambda: action.execute({
            "lium": lium,
            "executor_id": executor_id,
            "gpu": gpu,
            "count": count,
            "country": country,
            "ports": ports
        })
    )

    if not result.ok:
        ui.error(result.error)
        return

    executor: ExecutorInfo = result.data["executor"]

    if not yes:
        confirm_msg = (
            f"Acquire pod on {executor.huid} "
            f"({count or executor.available_gpu_count}×{executor.gpu_type}) "
            f"at ${(executor.price_per_gpu_hour * (count or executor.available_gpu_count)):.2f}/h?"
        )
        if not ui.confirm(confirm_msg):
            return

    action = ResolveTemplateAction()
    result = action.execute({
        "lium": lium,
        "template_id": template_id,
        "executor": executor
    })

    if not result.ok:
        ui.error(result.error)
        return

    template = result.data["template"]

    if volume_create_params:
        action = CreateVolumeAction()
        result = ui.load(
            f"Creating volume '{volume_create_params['name']}'",
            lambda: action.execute({
                "lium": lium,
                "volume_create_params": volume_create_params
            })
        )

        if not result.ok:
            ui.error(result.error)
            return

        volume_id = result.data["volume_id"]

    action = RentPodAction()
    result = ui.load(
        "Renting machine",
        lambda: action.execute({
            "lium": lium,
            "executor": executor,
            "template": template,
            "gpu_count": count or executor.available_gpu_count,
            "name": name,
            "volume_id": volume_id,
            "ports": ports
        })
    )

    if not result.ok:
        ui.error(result.error)
        return

    pod_id = result.data["pod_id"]
    pod_name = result.data["pod_name"]

    action = WaitReadyAction()
    result = ui.load(
        "Loading image",
        lambda: action.execute({
            "lium": lium,
            "pod_id": pod_id
        })
    )

    if not result.ok:
        ui.error(result.error)
        return

    pod = result.data["pod"]

    if termination_time:
        action = ScheduleTerminationAction()
        result = ui.load(
            "Scheduling termination",
            lambda: action.execute({
                "lium": lium,
                "pod": pod,
                "termination_time": termination_time
            })
        )

        if not result.ok:
            ui.error(result.error)

    if jupyter:
        action = InstallJupyterAction()
        result = ui.load(
            "Installing Jupyter",
            lambda: action.execute({
                "lium": lium,
                "pod": pod,
                "ui": ui
            })
        )

        if not result.ok:
            ui.error(result.error)

    action = PrepareSSHAction()
    result = ui.load(
        "Connecting SSH",
        lambda: action.execute({
            "pod_name": pod_name
        })
    )

    if not result.ok:
        ui.error(result.error)
        return

    ssh_cmd = result.data["ssh_cmd"]
    pod = result.data["pod"]

    from lium.cli.ssh.command import ssh_to_pod
    ssh_to_pod(ssh_cmd, pod)
