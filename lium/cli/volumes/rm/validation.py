"""Volumes rm validation."""


def validate(indices: str) -> tuple[bool, str]:
    if not indices or not indices.strip():
        return False, "Indices required"
    return True, ""
