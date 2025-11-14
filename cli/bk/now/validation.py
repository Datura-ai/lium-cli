"""Validation logic for bk now command."""


def validate(pod_id: str) -> tuple[bool, str]:
    """Validate bk now arguments."""
    if not pod_id or not pod_id.strip():
        return False, "Pod ID required"

    return True, ""
