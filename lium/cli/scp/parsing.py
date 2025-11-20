"""Parsing logic for scp command."""

import os
from pathlib import Path
from typing import List

from lium.sdk import PodInfo
from lium.cli.utils import parse_targets


def parse(
    targets: str,
    source_path: str,
    destination_path: str | None,
    download: bool,
    all_pods: List[PodInfo]
) -> tuple[dict | None, str]:
    """Parse scp command arguments."""

    selected_pods = parse_targets(targets, all_pods)

    if not selected_pods:
        return None, f"No pods match targets: {targets}"

    if not download:
        local_file = Path(source_path).expanduser().resolve()
        remote_path = destination_path or f"/root/{local_file.name}"
        remote_path = remote_path.strip()

        return {
            "pods": selected_pods,
            "local_file": local_file,
            "remote_path": remote_path,
            "download": False
        }, ""

    else:
        remote_path = source_path.strip()
        remote_basename = Path(remote_path).name or "downloaded_file"
        destination_str = destination_path or ""
        destination_input = Path(destination_path).expanduser().resolve() if destination_path else None
        multiple_pods = len(selected_pods) > 1
        destination_is_dir_hint = bool(destination_str and destination_str.endswith(os.sep))

        destination_map = {}

        if multiple_pods:
            if destination_input and destination_input.exists() and not destination_input.is_dir():
                return None, "Destination must be a directory when downloading from multiple pods"

            base_dir = destination_input if destination_input else Path.cwd()
            destination_map = {
                pod.huid: (pod, (base_dir / f"{pod.huid}-{remote_basename}").resolve())
                for pod in selected_pods
            }
        else:
            pod = selected_pods[0]
            if destination_input:
                is_dir = (destination_input.exists() and destination_input.is_dir()) or destination_is_dir_hint
                if is_dir:
                    local_dest = (destination_input / remote_basename).resolve()
                else:
                    local_dest = destination_input.resolve()
            else:
                local_dest = (Path.cwd() / remote_basename).resolve()
            destination_map[pod.huid] = (pod, local_dest)

        return {
            "pods": selected_pods,
            "remote_path": remote_path,
            "destination_map": destination_map,
            "download": True
        }, ""
