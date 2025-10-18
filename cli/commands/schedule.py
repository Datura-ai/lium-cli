"""Schedule pod termination commands using Lium SDK."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, List

import click
from rich.prompt import Confirm, Prompt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, PodInfo
from ..utils import console, handle_errors, loading_status, parse_targets
from .ps import show_pods


def select_target_interactive(all_pods: List[PodInfo]) -> str:
    """Interactive pod selection."""
    console.warning("Select a pod:")
    show_pods(all_pods, short=True)

    choices = [str(i) for i in range(1, len(all_pods) + 1)]

    selection = Prompt.ask(
        console.get_styled("Select pod by number", "info"),
        choices=choices,
        default="1"
    )

    return selection


def select_time_option() -> datetime:
    """Interactive time selection with preset options."""
    console.info("Select termination time:")
    options = [
        ("1", "1 hour", timedelta(hours=1)),
        ("2", "2 hours", timedelta(hours=2)),
        ("3", "3 hours", timedelta(hours=3)),
        ("4", "6 hours", timedelta(hours=6)),
        ("5", "12 hours", timedelta(hours=12)),
        ("6", "1 day", timedelta(days=1)),
        ("7", "Custom date/time", None),
    ]

    for num, label, _ in options:
        console.info(f"  {num}. {label}")

    choice = Prompt.ask(
        console.get_styled("Select option", "info"),
        choices=[opt[0] for opt in options],
        default="1"
    )

    selected_option = options[int(choice) - 1]

    if selected_option[2] is not None:
        # Preset time delta
        removal_time = datetime.now(timezone.utc) + selected_option[2]
    else:
        # Custom date/time
        console.info("\nEnter custom date/time (format: YYYY-MM-DD HH:MM or YYYY-MM-DD)")
        date_str = Prompt.ask("Date/time")

        try:
            # Try parsing with time
            if " " in date_str:
                removal_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            else:
                removal_time = datetime.strptime(date_str, "%Y-%m-%d")

            # Assume local timezone, convert to UTC
            removal_time = removal_time.replace(tzinfo=timezone.utc)

            # Validate it's in the future
            if removal_time <= datetime.now(timezone.utc):
                console.error("Date/time must be in the future")
                sys.exit(1)
        except ValueError:
            console.error("Invalid date format. Use YYYY-MM-DD HH:MM or YYYY-MM-DD")
            sys.exit(1)

    return removal_time


@click.command("schedule-terminate")
@click.argument("target", required=False)
@click.option("--time", "-t", help="Termination time (1h, 2h, 3h, 6h, 12h, 1d, or ISO datetime)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def schedule_terminate_command(target: Optional[str], time: Optional[str], yes: bool):
    """Schedule automatic pod termination at a future time.

    \b
    TARGET: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)

    \b
    TIME: Time format options:
      - 1h, 2h, 3h    (hours from now)
      - 6h, 12h       (hours from now)
      - 1d            (days from now)
      - YYYY-MM-DD    (specific date at midnight UTC)
      - YYYY-MM-DD HH:MM (specific date and time UTC)

    \b
    Examples:
      lium schedule-terminate 1 --time 6h       # Terminate pod #1 in 6 hours
      lium schedule-terminate eager-wolf --time 1d   # Terminate in 1 day
      lium schedule-terminate 2 --time "2025-10-20 15:30"  # Terminate at specific time
      lium schedule-terminate                   # Interactive mode
    """
    # Get all pods
    lium = Lium()
    with loading_status("Loading pods", ""):
        all_pods = lium.ps()

    if not all_pods:
        console.warning("No active pods")
        return

    # Determine which pod to schedule
    if target:
        selected_pods = parse_targets(target, all_pods)
        if not selected_pods:
            console.error(f"No pod matches target: {target}")
            return
        selected_pod = selected_pods[0]
    else:
        # Interactive mode
        target = select_target_interactive(all_pods)
        selected_pods = parse_targets(target, all_pods)
        selected_pod = selected_pods[0]

    # Determine removal time
    if time:
        # Parse time argument
        time_lower = time.lower()
        if time_lower.endswith('h'):
            hours = int(time_lower[:-1])
            removal_time = datetime.now(timezone.utc) + timedelta(hours=hours)
        elif time_lower.endswith('d'):
            days = int(time_lower[:-1])
            removal_time = datetime.now(timezone.utc) + timedelta(days=days)
        else:
            # Try parsing as ISO datetime
            try:
                if " " in time:
                    removal_time = datetime.strptime(time, "%Y-%m-%d %H:%M")
                else:
                    removal_time = datetime.strptime(time, "%Y-%m-%d")
                removal_time = removal_time.replace(tzinfo=timezone.utc)

                if removal_time <= datetime.now(timezone.utc):
                    console.error("Date/time must be in the future")
                    return
            except ValueError:
                console.error("Invalid time format. Use: 1h, 2h, 6h, 12h, 1d, YYYY-MM-DD, or 'YYYY-MM-DD HH:MM'")
                return
    else:
        # Interactive time selection
        removal_time = select_time_option()

    # Show what will be scheduled
    time_str = removal_time.strftime("%Y-%m-%d %H:%M UTC")
    time_delta = removal_time - datetime.now(timezone.utc)
    hours_until = time_delta.total_seconds() / 3600

    console.info(f"\nPod to schedule for termination:")
    price_info = ""
    if selected_pod.executor and selected_pod.executor.price_per_hour:
        price_info = f" (${selected_pod.executor.price_per_hour:.2f}/h)"
    console.info(f"  {selected_pod.huid} - {selected_pod.status}{price_info}")
    console.info(f"\nTermination time: {time_str}")
    console.dim(f"({hours_until:.1f} hours from now)")

    # Confirm unless -y flag
    if not yes:
        if not Confirm.ask(f"\nSet Schedule termination?", default=False):
            console.warning("Cancelled")
            return

    # Schedule termination
    try:
        with loading_status("Scheduling termination", "✓ Termination scheduled"):
            lium.schedule_termination(selected_pod.id, removal_time)
        console.success(f"Pod {selected_pod.huid} scheduled for termination at {time_str}")
    except Exception as e:
        console.error(f"Failed to schedule termination: {e}")


@click.command("cancel-schedule")
@click.argument("target", required=False)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def cancel_schedule_command(target: Optional[str], yes: bool):
    """Cancel a scheduled pod termination.

    \b
    TARGET: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)

    \b
    Examples:
      lium cancel-schedule 1          # Cancel schedule for pod #1
      lium cancel-schedule eager-wolf # Cancel schedule by name
      lium cancel-schedule            # Interactive mode
    """
    # Get all pods
    lium = Lium()
    with loading_status("Loading pods", ""):
        all_pods = lium.ps()

    if not all_pods:
        console.warning("No active pods")
        return

    # Determine which pod
    if target:
        selected_pods = parse_targets(target, all_pods)
        if not selected_pods:
            console.error(f"No pod matches target: {target}")
            return
        selected_pod = selected_pods[0]
    else:
        # Interactive mode
        target = select_target_interactive(all_pods)
        selected_pods = parse_targets(target, all_pods)
        selected_pod = selected_pods[0]

    # Show what will be cancelled
    console.info(f"\nPod to cancel scheduled termination:")
    console.info(f"  {selected_pod.huid} - {selected_pod.status}")

    # Confirm unless -y flag
    if not yes:
        if not Confirm.ask(f"\nCancel scheduled termination?", default=False):
            console.warning("Cancelled")
            return

    # Cancel scheduled termination
    try:
        with loading_status("Cancelling schedule", "✓ Schedule cancelled"):
            lium.cancel_scheduled_termination(selected_pod.id)
        console.success(f"Cancelled scheduled termination for pod {selected_pod.huid}")
    except Exception as e:
        console.error(f"Failed to cancel schedule: {e}")
