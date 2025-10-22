"""Remove pods command using Lium SDK."""
from __future__ import annotations

import os
import sys
from typing import Optional, List

import click
from rich.prompt import Confirm, Prompt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, PodInfo
from ..utils import console, handle_errors, loading_status, parse_targets
from .ps import show_pods


def select_targets_interactive(all_pods: List[PodInfo]) -> str:
    """Interactive pod selection."""
    console.warning("Select pods to remove:")
    show_pods(all_pods, short=True)
    
    choices = [str(i) for i in range(1, len(all_pods) + 1)]
    choices.append("all")
    
    selection = Prompt.ask(
        console.get_styled("Select pods by number, comma-separated, ranges like 1-3, or 'all')", "info"),
        default="1"
    )
    
    # Return the selection string directly for parse_targets to handle
    return selection


@click.command("rm")
@click.argument("targets", required=False)
@click.option("--all", "-a", is_flag=True, help="Remove all active pods")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--in", "in_duration", help="Schedule removal after duration (e.g., 45m, 6h, 2d)")
@click.option("--at", "at_time", help="Schedule removal at time in local timezone (e.g., 'today 23:00', 'tomorrow 01:00', '2025-10-20 15:30')")
@handle_errors
def rm_command(targets: Optional[str], all: bool, yes: bool, in_duration: Optional[str], at_time: Optional[str]):
    """Remove (terminate) GPU pods.
    
    \b
    TARGETS: Pod identifiers - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
      - Comma-separated (1,2,eager-wolf-aa)
      - All pods (all)
    
    \b
    Examples:
      lium rm 1                        # Remove pod #1 from ps immediately
      lium rm eager-wolf-aa            # Remove specific pod
      lium rm 1,2,3                    # Remove multiple pods
      lium rm all                      # Remove all pods
      lium rm --all                    # Remove all pods (alternative)
      lium rm 1 -y                     # Remove without confirmation
      lium rm 1 --in 45m               # Schedule removal in 45 minutes
      lium rm 1 --at "today 23:00"     # Schedule removal at 23:00 local time today
      lium rm 1 --at "tomorrow 01:00"  # Schedule removal at 01:00 local time tomorrow
    """
    # Validate --in/--at options (mutually exclusive)
    if in_duration and at_time:
        console.error("Cannot specify both --in and --at")
        return

    # Parse --in/--at to get termination time
    termination_time = None
    if in_duration:
        from .schedule import parse_duration
        from datetime import datetime, timezone
        duration = parse_duration(in_duration)
        if not duration:
            console.error(f"Invalid duration format: '{in_duration}'. Use format like '45m', '6h', '2d'")
            return
        termination_time = datetime.now(timezone.utc) + duration

    if at_time:
        from .schedule import parse_time_spec
        termination_time = parse_time_spec(at_time)
        if not termination_time:
            # Check if it's a "today" time that has passed
            if at_time.strip().lower().startswith('today '):
                console.error(f"Time '{at_time}' has already passed today. Use 'tomorrow HH:MM' or a future time.")
            else:
                console.error(f"Invalid time format: '{at_time}'. Use 'today HH:MM', 'tomorrow HH:MM', or 'YYYY-MM-DD HH:MM'")
            return

        # Validate it's in the future
        from datetime import datetime, timezone
        if termination_time <= datetime.now(timezone.utc):
            console.error("Removal time must be in the future")
            return

    # Get all pods
    lium = Lium()
    with loading_status("Loading pods", ""):
        all_pods = lium.ps()
    
    if not all_pods:
        console.warning("No active pods")
        return
    
    # Determine which pods to remove
    if all:
        selected_pods = all_pods
    elif targets:
        selected_pods = parse_targets(targets, all_pods)
    else:
        # Interactive mode when no targets specified
        targets = select_targets_interactive(all_pods)
        selected_pods = parse_targets(targets, all_pods)
    
    if not selected_pods:
        console.error(f"No pods match targets: {targets}")
        return
    
    # Calculate total cost
    total_cost = 0
    for pod in selected_pods:
        if pod.executor and pod.executor.price_per_hour and pod.created_at:
            try:
                from datetime import datetime, timezone
                if pod.created_at.endswith('Z'):
                    dt_created = datetime.fromisoformat(pod.created_at.replace('Z', '+00:00'))
                else:
                    dt_created = datetime.fromisoformat(pod.created_at)
                    if not dt_created.tzinfo:
                        dt_created = dt_created.replace(tzinfo=timezone.utc)
                
                now_utc = datetime.now(timezone.utc)
                hours = (now_utc - dt_created).total_seconds() / 3600
                total_cost += hours * pod.executor.price_per_hour
            except Exception:
                pass
    
    # Show what will be removed
    console.info(f"\nPods to remove:")
    for pod in selected_pods:
        price_info = ""
        if pod.executor and pod.executor.price_per_hour:
            price_info = f" (${pod.executor.price_per_hour:.2f}/h)"
        console.info(f"  {pod.huid} - {pod.status}{price_info}")
    
    if total_cost > 0:
        console.dim(f"\nTotal spent: ${total_cost:.2f}")
    
    # If scheduling removal, use schedule_termination instead of immediate removal
    if termination_time:
        from datetime import datetime, timezone
        time_str = termination_time.strftime("%Y-%m-%d %H:%M UTC")
        time_delta = termination_time - datetime.now(timezone.utc)
        hours_until = time_delta.total_seconds() / 3600

        # Show what will be scheduled
        console.info(f"\nPods to schedule for removal:")
        for pod in selected_pods:
            price_info = ""
            if pod.executor and pod.executor.price_per_hour:
                price_info = f" (${pod.executor.price_per_hour:.2f}/h)"
            console.info(f"  {pod.huid} - {pod.status}{price_info}")

        console.info(f"\nScheduled removal time: {time_str}")
        console.dim(f"({hours_until:.1f} hours from now)")

        # Confirm unless -y flag
        if not yes:
            confirm_msg = f"\nSchedule removal of {len(selected_pods)} pod{'s' if len(selected_pods) > 1 else ''}?"
            if not Confirm.ask(confirm_msg, default=False):
                console.warning("Cancelled")
                return

        # Schedule removal
        success_count = 0
        failed_pods = []

        for pod in selected_pods:
            try:
                termination_time_str = termination_time.isoformat()
                lium.schedule_termination(pod.id, termination_time_str)
                console.success(f"✓ Scheduled removal: {pod.huid}")
                success_count += 1
            except Exception as e:
                console.error(f"✗ Failed to schedule {pod.huid}: {e}")
                failed_pods.append(pod.huid)

        # Summary
        if len(selected_pods) > 1:
            console.dim(f"\nScheduled {success_count}/{len(selected_pods)} pods for removal")

        if failed_pods:
            console.error(f"Failed: {', '.join(failed_pods)}")

    else:
        # Immediate removal
        # Confirm unless -y flag
        if not yes:
            confirm_msg = f"\nRemove {len(selected_pods)} pod{'s' if len(selected_pods) > 1 else ''}?"
            if not Confirm.ask(confirm_msg, default=False):
                console.warning("Cancelled")
                return

        # Remove pods
        success_count = 0
        failed_pods = []

        for pod in selected_pods:
            try:
                lium.rm(pod)
                console.success(f"✓ Removed {pod.huid}")
                success_count += 1
            except Exception as e:
                console.error(f"✗ Failed to remove {pod.huid}: {e}")
                failed_pods.append(pod.huid)

        # Summary
        if len(selected_pods) > 1:
            console.dim(f"\nRemoved {success_count}/{len(selected_pods)} pods")

        if failed_pods:
            console.error(f"Failed: {', '.join(failed_pods)}")