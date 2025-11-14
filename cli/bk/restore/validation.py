"""Validation logic for bk restore command."""


def validate(pod_id: str, backup_id: str) -> tuple[bool, str]:
    """Validate bk restore arguments."""
    if not pod_id or not pod_id.strip():
        return False, "Pod ID required"

    if not backup_id or not backup_id.strip():
        return False, "Backup ID required"

    return True, ""
