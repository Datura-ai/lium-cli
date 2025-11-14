"""Validation logic for reboot command."""


def validate(targets: str | None, all_flag: bool) -> tuple[bool, str | None]:
    """Validate reboot command options, returns (is_valid, error_message)."""

    # Require either targets or --all
    if not targets and not all_flag:
        return False, "Must specify either TARGETS or --all"

    return True, None
