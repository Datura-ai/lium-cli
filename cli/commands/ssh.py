"""SSH to pods command using Lium SDK."""
from __future__ import annotations

import os
import sys
import subprocess
import shutil
from typing import Optional, List, Tuple

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lium_sdk import Lium, PodInfo
from ..utils import handle_errors, loading_status, console, parse_targets

def get_ssh_method_and_pod(target: str) -> Tuple[str, PodInfo]:
    """Helper function that check method for SSH."""
    # Check if ssh is available
    if not shutil.which("ssh"):
        console.error("Error: 'ssh' command not found. Please install an SSH client.")
        return
    
    # Get pods and resolve target
    lium = Lium()
    all_pods = lium.ps()
    
    pods = parse_targets(target, all_pods)
    pod = pods[0] if pods else None
    
    
    # Check if SSH command is available
    if not pod.ssh_cmd:
        console.error(f"No SSH connection available for pod '{pod.huid}'")
        return ""
    
    # Get SSH command from SDK
    try:
        ssh_cmd = lium.ssh(pod)
        # Add SSH options to skip host key verification
        ssh_cmd += " -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        return ssh_cmd,pod
    except ValueError as e:
        # Fallback to using the raw ssh_cmd if SDK method fails
        ssh_cmd = pod.ssh_cmd + " -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        return ssh_cmd,pod
    


def ssh_to_pod(ssh_cmd: str, pod: PodInfo) -> None:
    """Helper function to SSH to a pod without Click decorators."""
    
    lium = Lium()
    
    # Get SSH command from SDK
    try:
        ssh_cmd = lium.ssh(pod)
    except ValueError as e:
        ssh_cmd = pod.ssh_cmd
    
    # Add SSH options to skip host key verification
    ssh_cmd += " -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" 

    # Execute SSH command interactively
    try:
        # Use subprocess.run to hand over terminal control for interactive session
        result = subprocess.run(ssh_cmd, shell=True, check=False)
        
        # Only show exit code if it's non-zero and not 255 (common disconnect code)
        if result.returncode != 0 and result.returncode != 255:
            console.dim(f"\nSSH session ended with exit code {result.returncode}")
    except KeyboardInterrupt:
        console.warning("\nSSH session interrupted")
    except Exception as e:
        console.error(f"Error executing SSH: {e}")


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
    # Check if ssh is available
    if not shutil.which("ssh"):
        console.error("Error: 'ssh' command not found. Please install an SSH client.")
        return
    
    # Get pods and resolve target
    lium = Lium()
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
        console.warning(f"Warning: Pod '{pod.huid}' is {pod.status}")
        if pod.status in ["STOPPED", "FAILED"]:
            console.error("Cannot SSH to a stopped or failed pod")
            return
    
    # Check if SSH command is available
    if not pod.ssh_cmd:
        console.error(f"No SSH connection available for pod '{pod.huid}'")
        return
    
    # Get SSH command from SDK
    try:
        ssh_cmd = lium.ssh(pod)
        console.dim(f"Connecting to {pod.huid}...")
    except ValueError as e:
        # Fallback to using the raw ssh_cmd if SDK method fails
        ssh_cmd = pod.ssh_cmd
        console.dim(f"Connecting to {pod.huid} (using default SSH)...")

    ssh_cmd += " -o StrictHostKeyChecking=no"
    
    # Execute SSH command interactively
    try:
        # Use subprocess.run to hand over terminal control for interactive session
        result = subprocess.run(ssh_cmd, shell=True, check=False)
        
        # Only show exit code if it's non-zero and not 255 (common disconnect code)
        if result.returncode != 0 and result.returncode != 255:
            console.dim(f"\nSSH session ended with exit code {result.returncode}")
    except KeyboardInterrupt:
        console.warning("\nSSH session interrupted")
    except Exception as e:
        console.error(f"Error executing SSH: {e}")