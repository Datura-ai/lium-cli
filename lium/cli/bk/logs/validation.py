"""Validation logic for bk logs command."""


def validate(pod_id: str | None, backup_id: str | None) -> tuple[bool, str]:
    """Validate bk logs arguments."""
    if not pod_id and not backup_id:
        return False, "Please specify either a pod ID or use --id for a specific backup"

    return True, ""
