"""Validation logic for config set command."""


def validate(key: str) -> tuple[bool, str]:
    """Validate config set arguments."""
    if not key or not key.strip():
        return False, "Key required"

    return True, ""
