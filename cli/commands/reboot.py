"""Reboot pods command using Lium SDK."""
from __future__ import annotations

from typing import Optional, List

import click
from rich.prompt import Confirm

from lium_sdk import Lium, PodInfo
from ..utils import console, handle_errors, loading_status, parse_targets
from .rm import select_targets_interactive


def _confirm_targets(selected_pods: List[PodInfo], yes: bool) -> bool:
    """Confirm reboot operation unless --yes flag is provided."""
    if yes:
        return True

    pods_text = f"{len(selected_pods)} pod{'s' if len(selected_pods) > 1 else ''}"
    confirm_msg = f"\nReboot {pods_text}?"
    return Confirm.ask(confirm_msg, default=False)


@click.command("reboot")
@click.argument("targets", required=False)
@click.option("--all", "-a", is_flag=True, help="Reboot all active pods")
@click.option("--volume-id", help="Volume ID to attach when rebooting")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def reboot_command(targets: Optional[str], all: bool, volume_id: Optional[str], yes: bool):
    """Reboot GPU pods.
    
    \b
    TARGETS: Pod identifiers - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
      - Comma-separated (1,2,eager-wolf-aa)
      - All pods (all)
    
    \b
    Examples:
      lium reboot 1                  # Reboot pod #1 from ps
      lium reboot eager-wolf-aa      # Reboot specific pod
      lium reboot 1,2,3              # Reboot multiple pods
      lium reboot all                # Reboot all pods
      lium reboot 1 --volume-id VID  # Reboot with specific volume
    """
    lium = Lium()
    with loading_status("Loading pods", ""):
        all_pods = lium.ps()

    if not all_pods:
        console.warning("No active pods")
        return

    # Determine selected pods
    if all:
        selected_pods = all_pods
    elif targets:
        selected_pods = parse_targets(targets, all_pods)
    else:
        selection = select_targets_interactive(all_pods)
        selected_pods = parse_targets(selection, all_pods)

    if not selected_pods:
        console.error(f"No pods match targets: {targets or 'selection'}")
        return

    console.info("\nPods to reboot:")
    for pod in selected_pods:
        console.info(f"  {console.get_styled(pod.huid, 'pod_id')} ({pod.status})")

    # Confirm operation
    if not _confirm_targets(selected_pods, yes):
        console.warning("Cancelled")
        return

    # Execute reboots
    success_count = 0
    failed_pods: List[str] = []
    payload_volume_id = volume_id.strip() if volume_id else None

    for pod in selected_pods:
        try:
            console.dim(f"Rebooting {pod.huid}...", end="")
            lium.reboot(pod, volume_id=payload_volume_id)
            console.success(" ✓")
            success_count += 1
        except Exception as exc:
            console.error(" ✗")
            console.error(f"  Error: {exc}")
            failed_pods.append(pod.huid)

    # Summary
    console.info("")
    if len(selected_pods) == 1:
        if success_count == 1:
            console.success("Pod reboot triggered")
        else:
            console.error("Failed to reboot pod")
    else:
        console.dim(f"Rebooted {success_count}/{len(selected_pods)} pods")
        if failed_pods:
            console.error(f"Failed pods: {', '.join(failed_pods)}")
        if success_count == len(selected_pods):
            console.success("All reboot requests sent successfully")
