"""Validation logic for schedules rm command."""


def validate(indices: str) -> tuple[bool, str | None]:
    """Validate schedules rm command options, returns (is_valid, error_message)."""

    if not indices or not indices.strip():
        return False, "Must specify indices"

    return True, None
