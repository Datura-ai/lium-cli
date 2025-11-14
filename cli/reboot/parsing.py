"""Parsing logic for reboot command."""

from typing import List

from cli.lium_sdk import PodInfo
from cli.utils import parse_targets


def parse(
    targets: str | None,
    all_flag: bool,
    all_pods: List[PodInfo]
) -> tuple[dict | None, str | None]:
    """Parse reboot command inputs, returns (parsed_data_dict, error_message)."""

    if not all_pods:
        return None, "No active pods"

    # Parse targets
    if all_flag:
        selected_pods = all_pods
    elif targets:
        selected_pods = parse_targets(targets, all_pods)
        if not selected_pods:
            return None, f"No pods match targets: {targets}"
    else:
        return None, "No targets specified"

    return {"selected_pods": selected_pods}, None
