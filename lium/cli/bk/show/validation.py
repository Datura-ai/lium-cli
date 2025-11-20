"""Validation logic for bk show command."""


def validate(pod_id: str) -> tuple[bool, str]:
    """Validate bk show arguments."""
    if not pod_id or not pod_id.strip():
        return False, "Pod ID required"

    return True, ""
