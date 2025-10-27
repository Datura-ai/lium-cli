"""Backup management commands."""

import json
from datetime import datetime, timezone
from typing import Optional, List

import click
from rich.prompt import Confirm
from rich.table import Table

from cli.lium_sdk import Lium, BackupConfig
from cli.config import config
from ..utils import console, handle_errors, loading_status, ensure_config, parse_targets


def _resolve_pod_target(lium: Lium, target: str) -> Optional[str]:
    """Resolve pod target (name/index/huid) to pod name for SDK calls."""
    with loading_status(f"Resolving pod '{target}'", ""):
        all_pods = lium.ps()
    
    if not all_pods:
        console.error("No active pods found")
        return None
    
    # Use existing parse_targets function which handles indices and names
    selected_pods = parse_targets(target, all_pods)
    
    if not selected_pods:
        console.error(f"Pod '{target}' not found")
        console.info(f"Tip: {console.get_styled('lium ps', 'success')} to see available pods")
        return None
    
    # Return the name of the first matched pod
    return selected_pods[0].name or selected_pods[0].huid


@click.command("show")
@click.argument("pod_id")
@handle_errors
def bk_show_command(pod_id: str):
    """Show backup configuration for a specific pod.
    
    \b
    POD_ID: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
    
    \b
    Examples:
      lium bk show 1                 # Show backup config for pod #1
      lium bk show eager-wolf-aa     # Show backup config by name
    """
    ensure_config()
    lium = Lium()
    
    # Resolve pod target
    pod_name = _resolve_pod_target(lium, pod_id)
    if not pod_name:
        return
    
    console.info(f"Pod: {pod_id}")
    
    with loading_status("Loading backup config", ""):
        backup_config = lium.backup_config(pod=pod_name)
    
    if not backup_config:
        console.print("No backup configuration found.")
        return
    
    # Print config line
    console.print(f"Config: path={backup_config.backup_path}, every={backup_config.backup_frequency_hours}h, keep={backup_config.retention_days}d")
    
    # Get backup logs for last/next backup info
    with loading_status("Loading backup status", ""):
        backup_logs = lium.backup_logs(pod=pod_name)
    
    if backup_logs and len(backup_logs) > 0:
        last_log = backup_logs[0]  # Assuming most recent first
        status = getattr(last_log, 'status', 'UNKNOWN').upper()
        timestamp = getattr(last_log, 'created_at', 'Unknown')
        backup_id = getattr(last_log, 'id', '')[:8] if getattr(last_log, 'id', None) else 'unknown'
        console.print(f"Last Backup: {status} at {timestamp} (id={backup_id})")
    
    # Calculate next due time if we have frequency info
    if hasattr(backup_config, 'next_backup_at') and backup_config.next_backup_at:
        console.print(f"Next Due: {backup_config.next_backup_at}")
    elif backup_logs and len(backup_logs) > 0:
        # Calculate based on last backup + frequency
        from datetime import datetime, timedelta
        try:
            last_time = datetime.fromisoformat(getattr(backup_logs[0], 'created_at', '').replace('Z', '+00:00'))
            next_time = last_time + timedelta(hours=backup_config.backup_frequency_hours)
            console.print(f"Next Due: {next_time.strftime('%Y-%m-%d %H:%M')}")
        except:
            pass


@click.command("rm")
@click.argument("pod_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def bk_rm_command(pod_id: str, yes: bool):
    """Remove backup configuration for a pod.
    
    \b
    POD_ID: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
    
    \b
    Examples:
      lium bk rm 1                  # Remove backup for pod #1
      lium bk rm eager-wolf-aa      # Remove backup by name
      lium bk rm 1 --yes            # Remove without confirmation
    """
    ensure_config()
    lium = Lium()
    
    # Resolve pod target
    pod_name = _resolve_pod_target(lium, pod_id)
    if not pod_name:
        return
    
    with loading_status("Loading backup config", ""):
        backup_config = lium.backup_config(pod=pod_name)
    
    if not backup_config:
        console.warning(f"No backup configuration found for pod '{pod_id}'")
        return
    
    if not yes:
        if not Confirm.ask(f"Remove backup configuration for pod '{pod_id}'?"):
            console.warning("Cancelled")
            return
    
    with loading_status(f"Removing backup configuration", ""):
        lium.backup_delete(backup_config.id)
    
    console.success(f"Backup configuration removed for pod '{pod_id}'")


@click.command("set")
@click.argument("pod_id")
@click.option("--path", default="/root", help="Backup path (default: /root)")
@click.option("--every", help="Backup frequency (e.g., 1h, 6h, 24h)")
@click.option("--keep", help="Retention period (e.g., 1d, 7d, 30d)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def bk_set_command(pod_id: str, path: str, every: str, keep: str, yes: bool):
    """Set or update backup configuration for a pod.
    
    \b
    POD_ID: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
    
    \b
    Examples:
      lium bk set 1 --path /root --every 6h --keep 7d
      lium bk set eager-wolf-aa --every 1h --keep 1d
    """
    ensure_config()
    lium = Lium()
    
    # Resolve pod target
    pod_name = _resolve_pod_target(lium, pod_id)
    if not pod_name:
        return
    
    # Parse frequency and retention
    import re
    
    if every:
        match = re.match(r'(\d+)([hd])', every)
        if not match:
            console.error("Invalid frequency format. Use format like '1h' or '24h'")
            return
        frequency_hours = int(match.group(1))
        if match.group(2) == 'd':
            frequency_hours *= 24
    else:
        frequency_hours = config.default_backup_frequency
    
    if keep:
        match = re.match(r'(\d+)d', keep)
        if not match:
            console.error("Invalid retention format. Use format like '1d' or '7d'")
            return
        retention_days = int(match.group(1))
    else:
        retention_days = config.default_backup_retention
    
    # Check if backup already exists
    with loading_status("Checking existing backup config", ""):
        existing_config = lium.backup_config(pod=pod_name)
    
    if existing_config:
        if not yes:
            if not Confirm.ask(f"Backup configuration already exists. Replace it?"):
                console.warning("Cancelled")
                return
        # Delete existing config
        with loading_status("Removing existing configuration", ""):
            lium.backup_delete(existing_config.id)
    
    # Create new backup config
    with loading_status(f"Setting backup configuration", ""):
        lium.backup_create(
            pod=pod_name,
            path=path,
            frequency_hours=frequency_hours,
            retention_days=retention_days
        )
    
    console.success(f"Backup configured: path={path}, every={frequency_hours}h, keep={retention_days}d")


@click.command("now")
@click.argument("pod_id")
@click.option("-n", "--name", help="Backup name (e.g., 'pre-release')")
@click.option("-d", "--description", help="Backup description (e.g., 'before deploy')")
@handle_errors
def bk_now_command(pod_id: str, name: Optional[str], description: Optional[str]):
    """Trigger an immediate backup for a pod.
    
    \b
    POD_ID: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
    
    \b
    Examples:
      lium bk now 1                                    # Trigger backup for pod #1
      lium bk now 1 -n "pre-release"                   # With custom name
      lium bk now 1 -n "v2.0" -d "before deployment"   # With name and description
    """
    ensure_config()
    lium = Lium()
    
    # Resolve pod target
    pod_name = _resolve_pod_target(lium, pod_id)
    if not pod_name:
        return
    
    # Check if backup config exists
    with loading_status("Checking backup config", ""):
        backup_config = lium.backup_config(pod=pod_name)
    
    if not backup_config:
        console.error(f"No backup configuration found for pod '{pod_id}'")
        console.info("Tip: Set up backup first with 'lium bk set'")
        return
    
    # Generate default name if not provided
    if not name:
        from datetime import datetime
        name = f"manual-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Use provided description or default
    if not description:
        description = "Manual backup triggered from CLI"
    
    with loading_status(f"Triggering backup '{name}'", ""):
        result = lium.backup_now(
            pod=pod_name,
            name=name,
            description=description
        )
    
    console.success(f"Backup '{name}' triggered successfully")


@click.command("logs")
@click.argument("pod_id", required=False)
@click.option("--id", "backup_id", help="Specific backup ID to show details")
@handle_errors
def bk_logs_command(pod_id: Optional[str], backup_id: Optional[str]):
    """Show backup logs for a pod or specific backup.
    
    \b
    POD_ID: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
    
    \b
    Examples:
      lium bk logs 1                 # Show recent logs for pod #1
      lium bk logs eager-wolf        # Show logs by pod name
      lium bk logs --id abc123       # Show details for specific backup
    """
    ensure_config()
    lium = Lium()
    
    if backup_id:
        # Show specific backup details
        # Note: SDK may need a method to get single backup log by ID
        console.info(f"Backup ID: {backup_id}")
        # For now, we'll need to fetch all logs and filter
        with loading_status("Loading backup details", ""):
            # This is a workaround - ideally SDK would have backup_log(id=backup_id)
            all_pods = lium.ps()
            found = False
            for pod_info in all_pods:
                pod_name = pod_info.name or pod_info.huid
                logs = lium.backup_logs(pod=pod_name)
                for log in logs:
                    if getattr(log, 'id', '').startswith(backup_id):
                        found = True
                        # Display detailed log info
                        console.print(f"Pod: {pod_name}")
                        console.print(f"Status: {getattr(log, 'status', 'Unknown')}")
                        console.print(f"Created: {getattr(log, 'created_at', 'Unknown')}")
                        if hasattr(log, 'completed_at') and log.completed_at:
                            console.print(f"Completed: {log.completed_at}")
                        if hasattr(log, 'size_bytes') and log.size_bytes:
                            size_mb = log.size_bytes / (1024 * 1024)
                            console.print(f"Size: {size_mb:.2f} MB")
                        if hasattr(log, 'error') and log.error:
                            console.print(f"Error: {log.error}", style="red")
                        break
                if found:
                    break
            
            if not found:
                console.error(f"Backup '{backup_id}' not found")
        return
    
    if not pod_id:
        console.error("Please specify either a pod ID or use --id for a specific backup")
        return
    
    # Show logs for a specific pod
    pod_name = _resolve_pod_target(lium, pod_id)
    if not pod_name:
        return
    
    with loading_status(f"Loading backup logs for {pod_name}", ""):
        backup_logs = lium.backup_logs(pod=pod_name)
    
    if not backup_logs:
        console.warning(f"No backup logs found for pod '{pod_id}'")
        return
    
    # Display logs in a table
    from rich.table import Table
    
    table = Table(
        show_header=True,
        header_style="dim",
        box=None,
        padding=(0, 2)
    )
    
    table.add_column("#", style="dim")
    table.add_column("Backup ID", style="cyan")
    table.add_column("Status")
    table.add_column("Created")
    table.add_column("Size", justify="right")
    
    for idx, log in enumerate(backup_logs[:10], 1):  # Show last 10
        backup_id_full = getattr(log, 'id', 'unknown')
        status = getattr(log, 'status', 'Unknown')
        
        # Color status
        if status.upper() == 'COMPLETED':
            status = f"[green]{status}[/green]"
        elif status.upper() in ['FAILED', 'ERROR']:
            status = f"[red]{status}[/red]"
        else:
            status = f"[yellow]{status}[/yellow]"
        
        created = getattr(log, 'created_at', 'Unknown')
        if created != 'Unknown':
            # Format timestamp for readability
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                created = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass
        
        size = ""
        if hasattr(log, 'size_bytes') and log.size_bytes:
            size_mb = log.size_bytes / (1024 * 1024)
            size = f"{size_mb:.1f} MB"
        
        table.add_row(
            str(idx),
            backup_id_full,
            status,
            created,
            size
        )
    
    console.print(table)


@click.command("restore")
@click.argument("pod_id")
@click.option("--id", "backup_id", required=True, help="Backup ID to restore")
@click.option("--to", "restore_path", default="/root", help="Restore path (default: /root)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def bk_restore_command(pod_id: str, backup_id: str, restore_path: str, yes: bool):
    """Restore a backup to a pod.
    
    \b
    POD_ID: Pod identifier - can be:
      - Pod name/ID (eager-wolf-aa)
      - Index from 'lium ps' (1, 2, 3)
    
    \b
    Examples:
      lium bk restore 1 --id <backup-uuid>              # Restore to default /root
      lium bk restore 1 --id <backup-uuid> --to /home   # Restore to specific path
      lium bk restore eager-wolf --id <backup-uuid> -y  # Skip confirmation
    """
    ensure_config()
    lium = Lium()
    
    # Resolve pod target
    pod_name = _resolve_pod_target(lium, pod_id)
    if not pod_name:
        return
    
    if not yes:
        from rich.prompt import Confirm
        if not Confirm.ask(f"Restore backup to pod '{pod_id}' at {restore_path}?"):
            console.warning("Cancelled")
            return
    
    with loading_status(f"Restoring backup to {restore_path}", ""):
        result = lium.restore(
            pod=pod_name,
            backup_id=backup_id,
            restore_path=restore_path
        )
    
    console.success(f"Backup restored to {restore_path}")


@click.group()
def bk_command():
    """Manage pod backup configurations.
    
    \b
    Commands:
      show    - Display backup configuration for a pod
      rm      - Remove backup configuration
      set     - Set or update backup configuration
      now     - Trigger immediate backup
      logs    - Show backup logs
      restore - Restore a backup to a pod
    """
    pass


# Add subcommands to the bk group
bk_command.add_command(bk_show_command)
bk_command.add_command(bk_rm_command)
bk_command.add_command(bk_set_command)
bk_command.add_command(bk_now_command)
bk_command.add_command(bk_logs_command)
bk_command.add_command(bk_restore_command)