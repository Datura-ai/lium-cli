"""Validation logic for rsync command."""

import shutil
from pathlib import Path


def validate(local_path: str) -> tuple[bool, str | None]:
    """Validate rsync command options, returns (is_valid, error_message)."""

    # Check if rsync is installed
    if not shutil.which("rsync"):
        return False, "rsync command not found. Please install rsync locally"

    # Validate local path exists
    local_dir = Path(local_path).expanduser().resolve()
    if not local_dir.exists():
        return False, f"Local path does not exist: {local_path}"

    return True, None
