"""Parsing logic for rsync command."""

from pathlib import Path
from typing import List

from lium.sdk import PodInfo
from lium.cli.utils import parse_targets


def parse(
    targets: str,
    all_pods: List[PodInfo],
    local_path: str,
    remote_path: str | None
) -> tuple[dict | None, str | None]:
    """Parse rsync command inputs, returns (parsed_data_dict, error_message)."""

    if not all_pods:
        return None, "No active pods"

    # Parse targets
    selected_pods = parse_targets(targets, all_pods)
    if not selected_pods:
        return None, f"No pods match targets: {targets}"

    # Resolve paths
    local_dir = Path(local_path).expanduser().resolve()
    resolved_remote_path = remote_path or f"/root/{local_dir.name}"

    return {
        "selected_pods": selected_pods,
        "local_dir": local_dir,
        "remote_path": resolved_remote_path
    }, None
