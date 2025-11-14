"""Validation logic for scp command."""

from pathlib import Path


def validate(targets: str, source_path: str, download: bool) -> tuple[bool, str]:
    """Validate scp command arguments."""
    if not targets or not targets.strip():
        return False, "Targets required"

    if not source_path or not source_path.strip():
        return False, "Source path required"

    if not download:
        local_file = Path(source_path).expanduser().resolve()
        if not local_file.is_file():
            return False, f"'{source_path}' is not a file"

    return True, ""
