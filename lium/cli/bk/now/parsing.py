"""Parsing logic for bk now command."""

from datetime import datetime
from typing import List

from lium.sdk import PodInfo
from lium.cli.utils import parse_targets


def parse(
    pod_id: str,
    name: str | None,
    description: str | None,
    all_pods: List[PodInfo]
) -> tuple[dict | None, str]:
    """Parse bk now arguments."""

    selected_pods = parse_targets(pod_id, all_pods)

    if not selected_pods:
        return None, f"Pod '{pod_id}' not found"

    pod = selected_pods[0]
    pod_name = pod.name or pod.huid

    # Generate default name if not provided
    if not name:
        name = f"manual-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Use provided description or default
    if not description:
        description = "Manual backup triggered from CLI"

    return {
        "pod": pod,
        "pod_name": pod_name,
        "name": name,
        "description": description
    }, ""
