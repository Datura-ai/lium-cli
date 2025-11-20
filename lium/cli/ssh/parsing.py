"""Parsing logic for ssh command."""

from typing import List

from lium.sdk import PodInfo
from lium.cli.utils import parse_targets


def parse(target: str, all_pods: List[PodInfo]) -> tuple[dict | None, str]:
    """Parse ssh command arguments."""

    pods = parse_targets(target, all_pods)
    pod = pods[0] if pods else None

    if not pod:
        return None, f"Pod '{target}' not found"

    if pod.status not in ["RUNNING", "STARTING"]:
        if pod.status in ["STOPPED", "FAILED"]:
            return None, f"Cannot SSH to a stopped or failed pod '{pod.huid}'"
        return None, f"Pod '{pod.huid}' is {pod.status}"

    if not pod.ssh_cmd:
        return None, f"No SSH connection available for pod '{pod.huid}'"

    return {"pod": pod}, ""
