"""Parsing logic for bk rm command."""

from typing import List

from lium.sdk import Lium, PodInfo
from lium.cli.utils import parse_targets


def parse(pod_id: str, all_pods: List[PodInfo]) -> tuple[dict | None, str]:
    """Parse bk rm arguments."""

    selected_pods = parse_targets(pod_id, all_pods)

    if not selected_pods:
        return None, f"Pod '{pod_id}' not found"

    pod = selected_pods[0]
    pod_name = pod.name or pod.huid

    return {"pod": pod, "pod_name": pod_name}, ""
