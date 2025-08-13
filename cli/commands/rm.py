"""Remove pods command using Lium SDK."""
from __future__ import annotations

import os
import sys
from typing import Optional, List

import click
from rich.prompt import Confirm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, PodInfo
from ..utils import console, handle_errors, loading_status, parse_targets


@click.command("rm")
@click.argument("targets", required=False)
@click.option("--all", "-a", is_flag=True, help="Remove all active pods")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def rm_command(targets: Optional[str], all: bool, yes: bool):
    """Remove (terminate) GPU pods.
    
    \b
    TARGETS: Pod identifiers - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
      - Comma-separated (1,2,eager-wolf-aa)
      - All pods (all)
    
    \b
    Examples:
      lium rm 1                     # Remove pod #1 from ps
      lium rm eager-wolf-aa         # Remove specific pod
      lium rm 1,2,3                 # Remove multiple pods
      lium rm all                   # Remove all pods
      lium rm --all                 # Remove all pods (alternative)
      lium rm 1 -y                  # Remove without confirmation
    """
    # Validate inputs
    if not targets and not all:
        console.error("Error: Specify pod targets or use --all")
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
        selected_pods = []
    
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
            except:
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