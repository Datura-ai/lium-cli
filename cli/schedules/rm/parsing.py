"""Parsing logic for schedules rm command."""

from typing import List

from cli.lium_sdk import PodInfo


def parse(indices: str, all_pods: List[PodInfo]) -> tuple[dict | None, str | None]:
    """Parse schedules rm command inputs, returns (parsed_data_dict, error_message)."""

    # Filter to only pods with scheduled terminations
    scheduled_pods = [pod for pod in all_pods if getattr(pod, 'removal_scheduled_at', None)]

    if not scheduled_pods:
        return None, "No scheduled terminations found"

    # Parse comma-separated indices
    index_list = [idx.strip() for idx in indices.split(',')]
    pods_to_cancel = []

    for index_str in index_list:
        try:
            idx = int(index_str)
            if idx < 1 or idx > len(scheduled_pods):
                return None, f"Index {index_str} out of range (1..{len(scheduled_pods)})"
            pods_to_cancel.append(scheduled_pods[idx - 1])
        except ValueError:
            return None, f"Invalid index: {index_str}. Must be a number"

    return {"pods_to_cancel": pods_to_cancel}, None
