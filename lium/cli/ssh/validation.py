"""Validation logic for ssh command."""

import shutil


def validate(target: str) -> tuple[bool, str]:
    """Validate ssh command arguments."""
    if not shutil.which("ssh"):
        return False, "'ssh' command not found. Please install an SSH client"

    if not target or not target.strip():
        return False, "Target required"

    return True, ""
