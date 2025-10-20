"""Schedule pod termination commands using Lium SDK."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, List

import click
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, PodInfo
from ..utils import console, handle_errors, loading_status


def parse_duration(duration_str: str) -> Optional[timedelta]:
    """Parse duration string like '6h', '45m', '2d' into timedelta.

    Returns None if parsing fails.
    """
    duration_str = duration_str.strip().lower()

    # Extract number and unit
    import re
    match = re.match(r'^(\d+(?:\.\d+)?)(m|h|d)$', duration_str)
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)

    if unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)

    return None


def parse_time_spec(time_spec: str) -> Optional[datetime]:
    """Parse time specification like 'today 23:00', 'tomorrow 01:00', '2025-10-20 15:30'.

    Parses times in local timezone and converts to UTC.
    Returns datetime in UTC or None if parsing fails.
    """
    import time

    time_spec = time_spec.strip().lower()

    try:
        # Get current time in local timezone (naive datetime)
        now_local = datetime.now()
        # Get local timezone offset
        utc_offset = timedelta(seconds=-time.timezone if not time.daylight else -time.altzone)

        # Handle "today HH:MM" or "today HH:MM:SS"
        if time_spec.startswith('today '):
            time_part = time_spec[6:].strip()

            if ':' in time_part:
                parts = time_part.split(':')
                hour = int(parts[0])
                minute = int(parts[1])
                second = int(parts[2]) if len(parts) > 2 else 0

                target = now_local.replace(hour=hour, minute=minute, second=second, microsecond=0)

                # If time has passed today, return None to trigger error
                if target <= now_local:
                    return None

                # Convert to UTC by subtracting local offset
                return target.replace(tzinfo=timezone.utc) - utc_offset

        # Handle "tomorrow HH:MM" or "tomorrow HH:MM:SS"
        elif time_spec.startswith('tomorrow '):
            time_part = time_spec[9:].strip()

            if ':' in time_part:
                parts = time_part.split(':')
                hour = int(parts[0])
                minute = int(parts[1])
                second = int(parts[2]) if len(parts) > 2 else 0

                target = now_local.replace(hour=hour, minute=minute, second=second, microsecond=0)
                target += timedelta(days=1)

                # Convert to UTC by subtracting local offset
                return target.replace(tzinfo=timezone.utc) - utc_offset

        # Handle absolute datetime "YYYY-MM-DD HH:MM" or "YYYY-MM-DD HH:MM:SS"
        elif ' ' in time_spec:
            # Parse as local time
            target = datetime.strptime(time_spec, "%Y-%m-%d %H:%M")
            # Convert to UTC by subtracting local offset
            return target.replace(tzinfo=timezone.utc) - utc_offset

        # Handle date only "YYYY-MM-DD" (midnight local time)
        elif '-' in time_spec and len(time_spec) == 10:
            target = datetime.strptime(time_spec, "%Y-%m-%d")
            # Convert to UTC by subtracting local offset
            return target.replace(tzinfo=timezone.utc) - utc_offset

    except (ValueError, IndexError):
        pass

    return None


# Schedules group commands

def show_schedules(pods: List[PodInfo]) -> None:
    """Display pods with scheduled terminations in a clean table."""
    # Filter to only pods with scheduled terminations
    scheduled_pods = [pod for pod in pods if getattr(pod, 'removal_scheduled_at', None)]

    if not scheduled_pods:
        console.warning("No scheduled terminations")
        console.info("")
        console.info(f"Tip: {console.get_styled('lium up 1 --ttl 6h', 'success')} to create pod with auto-termination")
        return

    # Title
    console.info(Text("Scheduled Terminations", style="bold"), end="")
    console.dim(f"  ({len(scheduled_pods)} total)")

    table = Table(
        show_header=True,
        header_style="dim",
        box=None,
        pad_edge=False,
        expand=True,
        padding=(0, 1),
    )

    # Add columns
    table.add_column("", justify="right", width=3, no_wrap=True, style="dim")  # Index
    table.add_column("Pod ID", justify="left", ratio=3, min_width=20, overflow="fold")
    table.add_column("Status", justify="left", width=12, no_wrap=True)
    table.add_column("Scheduled At", justify="left", ratio=2, min_width=18, no_wrap=True)
    table.add_column("Time Until", justify="right", width=12, no_wrap=True)

    for idx, pod in enumerate(scheduled_pods, 1):
        removal_scheduled_at = getattr(pod, 'removal_scheduled_at', None)

        # Format scheduled time
        try:
            scheduled_time = datetime.fromisoformat(removal_scheduled_at.replace('Z', '+00:00'))
            scheduled_str = scheduled_time.strftime("%Y-%m-%d %H:%M")
            time_delta = scheduled_time - datetime.now(timezone.utc)
            hours_until = time_delta.total_seconds() / 3600

            if hours_until > 24:
                time_until = f"{hours_until / 24:.1f}d"
            elif hours_until > 0:
                time_until = f"{hours_until:.1f}h"
            else:
                time_until = console.get_styled("overdue", 'warning')
        except Exception:
            scheduled_str = removal_scheduled_at
            time_until = "—"

        from ..utils import mid_ellipsize
        table.add_row(
            str(idx),
            console.get_styled(mid_ellipsize(pod.huid), 'id'),
            console.get_styled(pod.status, 'info'),
            scheduled_str,
            time_until,
        )

    console.info(table)
    console.info("")
    console.info(f"Tip: {console.get_styled('lium schedules rm <index>', 'success')} {console.get_styled('# cancel scheduled termination', 'dim')}")


@click.command("list")
@handle_errors
def schedules_list_command():
    """List all pods with scheduled terminations."""
    lium = Lium()

    with loading_status("Loading scheduled terminations", ""):
        all_pods = lium.ps()

    show_schedules(all_pods)


@click.command("rm")
@click.argument("indices")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def schedules_rm_command(indices: str, yes: bool):
    """\b
    Cancel scheduled terminations by index from 'lium schedules' output.

    \b
    INDICES: Schedule index or comma-separated indices (1, 2, 3, or 1,2,3)

    \b
    Examples:
      lium schedules rm 1          # Cancel schedule #1
      lium schedules rm 1,2,3      # Cancel schedules #1, #2, and #3
      lium schedules rm 2 --yes    # Cancel without confirmation
    """
    lium = Lium()

    # Get all pods with scheduled terminations
    with loading_status("Loading scheduled terminations", ""):
        all_pods = lium.ps()
        scheduled_pods = [pod for pod in all_pods if getattr(pod, 'removal_scheduled_at', None)]

    if not scheduled_pods:
        console.warning("No scheduled terminations found")
        return

    # Parse comma-separated indices
    index_list = [idx.strip() for idx in indices.split(',')]
    pods_to_cancel = []

    for index_str in index_list:
        try:
            idx = int(index_str)
            if idx < 1 or idx > len(scheduled_pods):
                console.error(f"Index {index_str} out of range (1..{len(scheduled_pods)})")
                console.info("Tip: Run 'lium schedules' to see available scheduled terminations")
                return
            pods_to_cancel.append((idx, scheduled_pods[idx - 1]))
        except ValueError:
            console.error(f"Invalid index: {index_str}. Must be a number.")
            return

    # Confirm cancellation
    if not yes:
        if len(pods_to_cancel) == 1:
            pod = pods_to_cancel[0][1]
            removal_scheduled_at = getattr(pod, 'removal_scheduled_at', None)

            try:
                scheduled_time = datetime.fromisoformat(removal_scheduled_at.replace('Z', '+00:00'))
                scheduled_str = scheduled_time.strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                scheduled_str = removal_scheduled_at

            if not Confirm.ask(f"Cancel scheduled termination for {pod.huid} (scheduled: {scheduled_str})?"):
                console.warning("Cancelled")
                return
        else:
            console.info(f"Schedules to cancel:")
            for idx, pod in pods_to_cancel:
                removal_scheduled_at = getattr(pod, 'removal_scheduled_at', None)
                try:
                    scheduled_time = datetime.fromisoformat(removal_scheduled_at.replace('Z', '+00:00'))
                    scheduled_str = scheduled_time.strftime("%Y-%m-%d %H:%M UTC")
                except Exception:
                    scheduled_str = removal_scheduled_at
                console.info(f"  [{idx}] {pod.huid} - {scheduled_str}")
            if not Confirm.ask(f"Cancel {len(pods_to_cancel)} scheduled terminations?"):
                console.warning("Cancelled")
                return

    # Cancel scheduled terminations
    success_count = 0
    for idx, pod in pods_to_cancel:
        try:
            with loading_status(f"Cancelling schedule for {pod.huid}", ""):
                lium.cancel_scheduled_termination(pod.id)
            console.success(f"Cancelled schedule: {pod.huid}")
            success_count += 1
        except Exception as e:
            console.error(f"Failed to cancel {pod.huid}: {e}")

    if len(pods_to_cancel) > 1:
        console.dim(f"\nCancelled {success_count}/{len(pods_to_cancel)} scheduled terminations")


@click.group(invoke_without_command=True)
@click.pass_context
def schedules_command(ctx):
    """Manage scheduled pod terminations.

    \b
    Commands:
      list - List all scheduled terminations (default)
      rm   - Cancel scheduled terminations by index
    """
    # If no subcommand is provided, default to list
    if ctx.invoked_subcommand is None:
        ctx.invoke(schedules_list_command)


# Add subcommands to the schedules group
schedules_command.add_command(schedules_list_command)
schedules_command.add_command(schedules_rm_command)
