from typing import List

from cli.actions import ActionResult
from cli.lium_sdk import Lium, PodInfo
from cli import ui


class RemovePodsAction:
    """Remove pods immediately."""

    def execute(self, ctx: dict) -> ActionResult:
        pods: List[PodInfo] = ctx["pods"]
        lium: Lium = ctx["lium"]

        failed_huids = []

        for pod in pods:
            try:
                lium.rm(pod)
            except Exception as e:
                ui.debug(f"Failed to remove {pod.huid}: {e}")
                failed_huids.append(pod.huid)

        return ActionResult(
            ok=(len(failed_huids) == 0),
            data={"failed_huids": failed_huids}
        )


class ScheduleRemovalAction:
    """Schedule pod removal at a future time."""

    def execute(self, ctx: dict) -> ActionResult:
        pods: List[PodInfo] = ctx["pods"]
        lium: Lium = ctx["lium"]
        termination_time: str = ctx["termination_time"]

        failed_huids = []

        for pod in pods:
            try:
                lium.schedule_termination(pod.id, termination_time)
            except Exception as e:
                ui.debug(f"Failed to schedule {pod.huid}: {e}")
                failed_huids.append(pod.huid)

        return ActionResult(
            ok=(len(failed_huids) == 0),
            data={"failed_huids": failed_huids}
        )
