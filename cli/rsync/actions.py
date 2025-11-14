"""Actions for rsync command."""

from pathlib import Path
from typing import List

from cli.actions import ActionResult
from cli.lium_sdk import Lium, PodInfo
from cli import ui


class RsyncPodsAction:
    """Rsync files to pods."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute rsync to pods."""
        pods: List[PodInfo] = ctx["pods"]
        lium: Lium = ctx["lium"]
        local_dir: Path = ctx["local_dir"]
        remote_path: str = ctx["remote_path"]

        failed_huids = []

        for pod in pods:
            try:
                # Check if rsync is installed on pod
                check_result = lium.exec(pod, "which rsync")
                if not check_result.get("success"):
                    ui.debug(f"Installing rsync on {pod.huid}")
                    install_result = lium.exec(pod, "apt-get update -qq && apt-get install -y rsync -qq")
                    if not install_result.get("success"):
                        ui.debug(f"Failed to install rsync on {pod.huid}")
                        failed_huids.append(pod.huid)
                        continue

                # Format path for directories
                local_formatted = str(local_dir) + ('/' if local_dir.is_dir() else '')

                # Rsync
                lium.rsync(pod, local_formatted, remote_path)

            except Exception as e:
                ui.debug(f"Failed to rsync to {pod.huid}: {e}")
                failed_huids.append(pod.huid)

        return ActionResult(
            ok=(len(failed_huids) == 0),
            data={"failed_huids": failed_huids}
        )
