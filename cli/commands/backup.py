"""Backup management commands."""

import json
from datetime import datetime, timezone
from typing import Optional, List

import click
from rich.prompt import Confirm
from rich.table import Table

from lium_sdk import Lium, BackupConfig
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


def _get_pod_name_for_backup_config(lium: Lium, config: BackupConfig) -> str:
    """Get pod huid for backup config using pod_executor_id."""
    all_pods = lium.ps()
    
    # Match by pod_executor_id (which is pod.id)
    for pod in all_pods:
        if pod.id == config.pod_executor_id:
            return pod.huid or pod.name
    
    # If pod not found in active pods, return huid from config
    return getattr(config, 'huid', 'Unknown')


def _format_frequency(hours: int) -> str:
    """Format frequency for display."""
    if hours == 24:
        return "daily"
    elif hours == 12:
        return "12h"
    elif hours == 6:
        return "6h"
    elif hours == 1:
        return "hourly"
    else:
        return f"{hours}h"


def _format_retention(days: int) -> str:
    """Format retention for display."""
    if days == 1:
        return "1 day"
    elif days == 7:
        return "1 week"
    elif days == 30:
        return "1 month"
    else:
        return f"{days} days"


def _store_backup_configs(configs: List[BackupConfig]) -> None:
    """Store backup configs for index-based operations."""
    
    selection_data = {
        'timestamp': datetime.now().isoformat(),
        'configs': []
    }
    
    for backup_config in configs:
        selection_data['configs'].append({
            'id': backup_config.id,
            'huid': backup_config.huid,
            'pod_executor_id': backup_config.pod_executor_id,
            'backup_path': backup_config.backup_path,
            'backup_frequency_hours': backup_config.backup_frequency_hours,
            'retention_days': backup_config.retention_days,
            'is_active': backup_config.is_active
        })
    
    # Store in config directory
    config_file = config.config_dir / "last_backup_configs.json"
    with open(config_file, 'w') as f:
        json.dump(selection_data, f, indent=2)


def _get_last_backup_configs() -> Optional[List[dict]]:
    """Retrieve the last backup configs selection."""
    
    config_file = config.config_dir / "last_backup_configs.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
                return data.get('configs', [])
        except (json.JSONDecodeError, IOError):
            return None
    return None


def _resolve_backup_config_id(config_target: str) -> Optional[str]:
    """Resolve backup config target (index or ID) to actual config ID."""
    # If it looks like a UUID, return as-is
    if len(config_target) >= 8 and not config_target.isdigit():
        return config_target
    
    # Try as index
    if config_target.isdigit():
        last_configs = _get_last_backup_configs()
        if not last_configs:
            console.error("No recent backup configurations found. Please run 'lium backup ls' first.")
            return None
        
        index = int(config_target)
        if 1 <= index <= len(last_configs):
            return last_configs[index - 1]['id']
        else:
            console.error(f"Index {config_target} is out of range (1..{len(last_configs)}). Try: lium backup ls")
            return None
    
    return config_target



@click.command("up")
@click.argument("pod_target", required=True)
@click.option("--path", default="/root", help="Backup path (default: /root)")
@click.option("--frequency", type=int, default=6, help="Backup frequency in hours (default: 6)")
@click.option("--retention", type=int, default=7, help="Backup retention in days (default: 7)")
@click.option("--yes", "-y", is_flag=True, help="Skip interactive prompts")
@handle_errors
def backup_up_command(pod_target: str, path: str, frequency: int, retention: int, yes: bool):
    """Set up automated backups for an existing pod.
    
    \b
    Examples:
      lium backup up pod-name                           # Interactive setup
      lium backup up 1 --path /home --frequency 12     # By index with custom params
      lium backup up pod-name --frequency 6 --retention 7 --path /root
    """
    from ..utils import ensure_backup_params, setup_backup, BackupParams
    
    ensure_config()
    lium = Lium()
    
    # Resolve pod target to actual pod name
    pod_name = _resolve_pod_target(lium, pod_target)
    if not pod_name:
        return
    
    try:
        # Ensure backup parameters (prompts if using defaults and not --yes)
        backup_params = ensure_backup_params(
            enabled=True,
            path=path, 
            frequency=frequency, 
            retention=retention, 
            skip_prompts=yes
        )
        
        # Setup backup using SDK
        setup_backup(lium, pod_name, backup_params)
        
    except ValueError as e:
        # Validation errors are already logged by ensure_backup_params
        return



@click.command("ls")
@click.option("--pod", help="Filter by pod name")
@handle_errors
def backup_ls_command(pod: Optional[str]):
    """List backup configurations.
    
    \b
    Examples:
      lium backup ls                    # List all backup configs
      lium backup ls --pod my-pod       # List backups for specific pod
      lium backup ls --pod 1            # List backups for pod #1 (from lium ps)
    """
    ensure_config()
    lium = Lium()
    
    # Resolve pod parameter if provided
    resolved_pod = None
    if pod:
        resolved_pod = _resolve_pod_target(lium, pod)
        if not resolved_pod:
            return
    
    with loading_status("Loading backup configurations", ""):
        backup_configs = lium.backup_list(pod=resolved_pod)
    
    if not backup_configs:
        if pod:
            console.warning(f"No backup configurations found for pod '{pod}'")
        else:
            console.warning("No backup configurations found")
        return
    
    # Title with count
    console.info(f"Backup Configurations  ({len(backup_configs)} active)")
    
    table = Table(
        show_header=True,
        header_style="dim",
        box=None,        # no ASCII borders
        pad_edge=False,
        expand=False,    # don't expand to full width
        padding=(0, 1),  # tight padding
    )
    
    table.add_column("#", justify="right", width=3, no_wrap=True)
    table.add_column("Pod", justify="left", width=18, overflow="ellipsis")
    table.add_column("Path", justify="left", width=15, overflow="ellipsis")
    table.add_column("Frequency", justify="left", width=10, no_wrap=True)
    table.add_column("Retention", justify="left", width=10, no_wrap=True)
    table.add_column("Status", justify="left", width=8, no_wrap=True)
    table.add_column("ID", justify="left", width=8, overflow="ellipsis")
    
    for idx, config in enumerate(backup_configs, 1):
        # Get proper pod name using helper function
        pod_name = _get_pod_name_for_backup_config(lium, config)
        path = config.backup_path
        frequency = config.backup_frequency_hours
        retention = config.retention_days
        status = "Active" if config.is_active else "Inactive"
        config_id_short = config.id[:8] if len(config.id) > 8 else config.id
        
        table.add_row(
            str(idx),
            pod_name,
            path,
            _format_frequency(frequency),
            _format_retention(retention),
            status,
            config_id_short
        )
    
    console.print(table)
    
    # Store backup configs for index-based operations
    _store_backup_configs(backup_configs)


@click.command("trigger")
@click.argument("pod_target", required=True)
@click.option("--name", help="Backup name")
@handle_errors
def backup_trigger_command(pod_target: str, name: Optional[str]):
    """Trigger a manual backup for a pod.
    
    \b
    Examples:
      lium backup trigger my-pod                    # Trigger backup with auto name
      lium backup trigger 1 --name "before-update" # By index from 'lium ps'
    """
    ensure_config()
    lium = Lium()
    
    # Resolve pod target to actual pod name
    pod_name = _resolve_pod_target(lium, pod_target)
    if not pod_name:
        return
    
    if not name:
        name = f"manual-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    with loading_status(f"Triggering backup '{name}' for pod '{pod_name}'", ""):
        result = lium.backup_now(
            pod=pod_name,
            name=name,
            description=f"Manual backup triggered from CLI"
        )
    
    console.success(f"Backup '{name}' triggered successfully")


@click.command("logs")
@click.argument("pod_target", required=True)
@handle_errors
def backup_logs_command(pod_target: str):
    """Show backup logs for a pod.
    
    \b
    Examples:
      lium backup logs my-pod        # By pod name
      lium backup logs 1             # By index from 'lium ps'
    """
    ensure_config()
    lium = Lium()
    
    # Resolve pod target to actual pod name
    pod_name = _resolve_pod_target(lium, pod_target)
    if not pod_name:
        return
    
    with loading_status(f"Loading backup logs for pod '{pod_name}'", ""):
        logs = lium.backup_logs(pod=pod_name)
    
    if not logs:
        console.warning(f"No backup logs found for pod '{pod_name}'")
        return
    
    # Title with count
    console.info(f"Backup Logs for {pod_name}  ({len(logs)} entries)")
    
    table = Table(
        show_header=True,
        header_style="dim",
        box=None,        # no ASCII borders
        pad_edge=False,
        expand=False,    # don't expand to full width
        padding=(0, 1),  # tight padding
    )
    
    table.add_column("Started", justify="left", width=12, no_wrap=True)
    table.add_column("Backup ID", justify="left", width=20, overflow="ellipsis")
    table.add_column("Status", justify="left", width=10, no_wrap=True)
    table.add_column("Duration", justify="right", width=8, no_wrap=True)
    
    for log in logs:
        # Format started_at timestamp as relative time (like ps command)
        started_at = getattr(log, 'started_at', '')
        if started_at:
            try:
                if started_at.endswith('Z'):
                    dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                else:
                    dt = datetime.fromisoformat(started_at)
                    if not dt.tzinfo:
                        dt = dt.replace(tzinfo=timezone.utc)
                
                duration = datetime.now(timezone.utc) - dt
                hours = duration.total_seconds() / 3600
                
                if hours < 1:
                    mins = duration.total_seconds() / 60
                    timestamp = f"{mins:.0f}m ago"
                elif hours < 24:
                    timestamp = f"{hours:.1f}h ago"
                else:
                    days = hours / 24
                    timestamp = f"{days:.1f}d ago"
            except:
                timestamp = started_at[:16] if len(started_at) > 16 else started_at
        else:
            timestamp = '—'
        
        # Use huid as backup identifier
        backup_id = getattr(log, 'huid', '—')
        status = getattr(log, 'status', 'Unknown')
        
        # Calculate duration
        started = getattr(log, 'started_at', '')
        completed = getattr(log, 'completed_at', '')
        duration_str = '—'
        if started and completed:
            try:
                start_dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(completed.replace('Z', '+00:00'))
                duration = end_dt - start_dt
                total_seconds = duration.total_seconds()
                if total_seconds >= 60:
                    duration_str = f"{int(total_seconds//60)}m{int(total_seconds%60)}s"
                else:
                    duration_str = f"{int(total_seconds)}s"
            except:
                duration_str = '—'
        
        # Color status
        if status.lower() in ['success', 'completed']:
            status_style = "green"
        elif status.lower() in ['error', 'failed']:
            status_style = "red"
        else:
            status_style = "yellow"
        
        table.add_row(
            timestamp,
            backup_id,
            f"[{status_style}]{status}[/{status_style}]",
            duration_str
        )
    
    console.print(table)


@click.command("rm")
@click.argument("config_id", required=True)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@handle_errors
def backup_rm_command(config_id: str, yes: bool):
    """Remove backup configuration.
    
    \b
    Examples:
      lium backup rm 1              # Remove config by index (from backup ls)
      lium backup rm config-123     # Remove config by ID
      lium backup rm config-123 -y  # Skip confirmation
    """
    ensure_config()
    lium = Lium()
    
    # Resolve config ID (support index or actual ID)
    resolved_config_id = _resolve_backup_config_id(config_id)
    if not resolved_config_id:
        return
    
    if not yes:
        if not Confirm.ask(f"Remove backup configuration '{config_id}'?", default=False):
            console.warning("Cancelled")
            return
    
    with loading_status(f"Removing backup configuration '{config_id}'", ""):
        result = lium.backup_delete(config_id=resolved_config_id)
    
    console.success(f"Backup configuration '{config_id}' removed")


@click.group("backup")
def backup_command():
    """Manage pod backups.
    
    Automated backup system for your pods with configurable frequency and retention.
    """
    pass


# Add subcommands to the backup group
backup_command.add_command(backup_up_command)
backup_command.add_command(backup_ls_command)
backup_command.add_command(backup_trigger_command)
backup_command.add_command(backup_logs_command)
backup_command.add_command(backup_rm_command)