"""Parsing logic for bk logs command."""

from typing import List

from cli.lium_sdk import PodInfo
from cli.utils import parse_targets


def parse(pod_id: str | None, all_pods: List[PodInfo]) -> tuple[dict | None, str]:
    """Parse bk logs arguments."""

    if not pod_id:
        return {"pod_name": None}, ""

    selected_pods = parse_targets(pod_id, all_pods)

    if not selected_pods:
        return None, f"Pod '{pod_id}' not found"

    pod = selected_pods[0]
    pod_name = pod.name or pod.huid

    return {"pod": pod, "pod_name": pod_name}, ""
