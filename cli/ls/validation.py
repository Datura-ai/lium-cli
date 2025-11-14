"""Validation logic for ls command."""


def validate(sort_by: str, limit: int | None) -> tuple[bool, str | None]:
    """Validate ls command options, returns (is_valid, error_message)."""

    # Validate sort_by
    valid_sort_options = ["price_gpu", "price_total", "loc", "id", "gpu"]
    if sort_by not in valid_sort_options:
        return False, f"Invalid sort option: {sort_by}"

    # Validate limit
    if limit is not None and limit <= 0:
        return False, "Limit must be a positive integer"

    return True, None
