"""Parsing logic for update command."""

from typing import List

from lium.sdk import PodInfo
from lium.cli.utils import parse_targets


def parse(target: str, all_pods: List[PodInfo]) -> tuple[dict | None, str]:
    """Parse update command arguments."""

    pods = parse_targets(target, all_pods)
    pod = pods[0] if pods else None

    if not pod:
        return None, f"Pod '{target}' not found"

    if pod.status not in ["RUNNING", "STARTING"]:
        if pod.status in ["STOPPED", "FAILED"]:
            return None, f"Cannot update a stopped or failed pod '{pod.huid}'"
        return None, f"Pod '{pod.huid}' is {pod.status}"

    return {"pod": pod}, ""
