"""Validation logic for update command."""


def validate(target: str, jupyter: int | None) -> tuple[bool, str]:
    """Validate update command arguments."""
    if not target or not target.strip():
        return False, "Target required"

    if not jupyter:
        return False, "No updates specified. Use --jupyter to install Jupyter Notebook"

    if jupyter <= 0 or jupyter > 65535:
        return False, "Port must be between 1 and 65535"

    return True, ""
