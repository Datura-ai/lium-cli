from cli.actions import Action, ActionResult
from cli.lium_sdk import Lium, PodInfo


class RemovePodsAction(Action):
    name = "remove_pods"
    fatal = False

    def run(self, ctx) -> ActionResult:
        pods: list[PodInfo] = ctx["pods"]
        lium: Lium = ctx["lium"]

        failed_huids = []

        for pod in pods:
            try:
                lium.rm(pod)
            except Exception:
                failed_huids.append(pod.huid)

        if failed_huids:
            return ActionResult(
                ok=False,
                error=f"Failed to remove pods: {', '.join(failed_huids)}"
            )

        return ActionResult(ok=True)
