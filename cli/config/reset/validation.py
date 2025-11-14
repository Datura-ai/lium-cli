"""Validation logic for config reset command."""


def validate(confirm: bool) -> tuple[bool, str]:
    """Validate config reset arguments."""
    if not confirm:
        from rich.prompt import Confirm
        if not Confirm.ask("This will delete all configuration. Continue?", default=False):
            return False, "Reset cancelled"

    return True, ""
