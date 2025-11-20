"""Validation logic for config get command."""


def validate(key: str) -> tuple[bool, str]:
    """Validate config get arguments."""
    if not key or not key.strip():
        return False, "Key required"

    return True, ""
