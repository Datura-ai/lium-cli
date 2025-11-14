"""Validation logic for bk set command."""

import re


def validate(pod_id: str, every: str | None, keep: str | None) -> tuple[bool, str]:
    """Validate bk set arguments."""
    if not pod_id or not pod_id.strip():
        return False, "Pod ID required"

    if every:
        match = re.match(r'(\d+)([hd])', every)
        if not match:
            return False, "Invalid frequency format. Use format like '1h' or '24h'"

    if keep:
        match = re.match(r'(\d+)d', keep)
        if not match:
            return False, "Invalid retention format. Use format like '1d' or '7d'"

    return True, ""
