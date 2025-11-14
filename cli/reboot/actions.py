"""Actions for reboot command."""

from typing import List

from cli.core import ActionResult
from cli.lium_sdk import Lium, PodInfo
from cli import ui


class RebootPodsAction:
    """Reboot pods."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute pod reboot."""
        pods: List[PodInfo] = ctx["pods"]
        lium: Lium = ctx["lium"]
        volume_id: str | None = ctx.get("volume_id")

        failed_huids = []

        for pod in pods:
            try:
                lium.reboot(pod, volume_id=volume_id)
            except Exception as e:
                ui.debug(f"Failed to reboot {pod.huid}: {e}")
                failed_huids.append(pod.huid)

        return ActionResult(
            ok=(len(failed_huids) == 0),
            data={"failed_huids": failed_huids}
        )
