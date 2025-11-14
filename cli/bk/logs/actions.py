"""Actions for bk logs command."""

from cli.core import ActionResult
from cli.lium_sdk import Lium


class GetBackupLogsAction:
    """Get backup logs."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute backup logs fetch."""
        lium: Lium = ctx["lium"]
        pod_name: str | None = ctx.get("pod_name")
        backup_id: str | None = ctx.get("backup_id")

        try:
            if backup_id:
                # Search for specific backup ID across all pods
                all_pods = lium.ps()
                for pod_info in all_pods:
                    pod_name_search = pod_info.name or pod_info.huid
                    logs = lium.backup_logs(pod=pod_name_search)
                    for log in logs:
                        if getattr(log, 'id', '').startswith(backup_id):
                            return ActionResult(
                                ok=True,
                                data={
                                    "single_backup": True,
                                    "pod_name": pod_name_search,
                                    "log": log
                                }
                            )
                return ActionResult(ok=False, error=f"Backup '{backup_id}' not found")

            # Get logs for specific pod
            backup_logs = lium.backup_logs(pod=pod_name)

            if not backup_logs:
                return ActionResult(ok=True, data={"logs": []})

            return ActionResult(ok=True, data={"logs": backup_logs[:10]})
        except Exception as e:
            return ActionResult(ok=False, error=str(e))
