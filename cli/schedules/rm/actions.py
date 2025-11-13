"""Actions for schedules rm command."""

from typing import List

from cli.lium_sdk import Lium, PodInfo
from cli import ui


class ActionResult:
    """Result of an action execution."""

    def __init__(self, ok: bool, data: dict | None = None, error: str | None = None):
        self.ok = ok
        self.data = data or {}
        self.error = error


class CancelSchedulesAction:
    """Cancel scheduled terminations."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute schedule cancellations."""
        pods: List[PodInfo] = ctx["pods"]
        lium: Lium = ctx["lium"]

        failed_huids = []

        for pod in pods:
            try:
                lium.cancel_scheduled_termination(pod.id)
            except Exception as e:
                ui.debug(f"Failed to cancel schedule for {pod.huid}: {e}")
                failed_huids.append(pod.huid)

        return ActionResult(
            ok=(len(failed_huids) == 0),
            data={"failed_huids": failed_huids}
        )
