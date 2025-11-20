from typing import List

from lium.cli.actions import ActionResult
from lium.sdk import Lium, PodInfo
from lium.cli import ui


class CancelSchedulesAction:
    """Cancel scheduled terminations."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute schedule cancellations."""
        pods: List[PodInfo] = ctx["pods"]
        lium: Lium = ctx["lium"]

        failed_huids = []

        for pod in pods:
            try:
                lium.cancel_scheduled_termination(pod)
            except Exception as e:
                ui.debug(f"Failed to cancel schedule for {pod.huid}: {e}")
                failed_huids.append(pod.huid)

        return ActionResult(
            ok=(len(failed_huids) == 0),
            data={"failed_huids": failed_huids}
        )
