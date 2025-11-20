"""Validation logic for rm command."""


def validate(
    targets: str | None,
    all_flag: bool,
    in_duration: str | None,
    at_time: str | None
) -> tuple[bool, str | None]:
    """Validate rm command options, returns (is_valid, error_message)."""
    # Require either targets or --all
    if not targets and not all_flag:
        return False, "Must specify either TARGETS or --all"

    # Check mutually exclusive options
    if in_duration and at_time:
        return False, "Cannot specify both --in and --at"

    return True, None
