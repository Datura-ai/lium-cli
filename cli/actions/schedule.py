from cli.actions import Action, ActionResult
from cli.lium_sdk import Lium, PodInfo


class ScheduleRemovalAction(Action):
    name = "schedule_removal"
    fatal = False

    def run(self, ctx) -> ActionResult:
        pods: list[PodInfo] = ctx["pods"]
        lium: Lium = ctx["lium"]
        termination_time: str = ctx["termination_time"]

        failed_huids = []

        for pod in pods:
            try:
                lium.schedule_termination(pod.id, termination_time)
            except Exception:
                failed_huids.append(pod.huid)

        if failed_huids:
            return ActionResult(
                ok=False,
                error=f"Failed to schedule removal for pods: {', '.join(failed_huids)}"
            )

        return ActionResult(ok=True)
