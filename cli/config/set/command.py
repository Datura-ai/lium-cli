"""Config set command implementation."""

from typing import Optional

import click

from cli import ui
from cli.utils import handle_errors
from . import validation
from .actions import SetConfigAction


def mask_value(value: str, key: str) -> str:
    """Mask sensitive values."""
    if key.endswith('api_key') and value:
        return value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
    return value


@click.command(name="set")
@click.argument("key")
@click.argument("value", required=False)
@handle_errors
def config_set_command(key: str, value: Optional[str]):
    """Set a configuration value. Run without value for interactive mode."""

    # Validate
    valid, error = validation.validate(key)
    if not valid:
        ui.error(error)
        return

    # Execute
    ctx = {"key": key, "value": value or ""}

    action = SetConfigAction()
    result = action.execute(ctx)

    if not result.ok:
        ui.error(result.error)
        return

    new_value = result.data.get("value")
    styled_value = mask_value(new_value, key)
    ui.success(f"Set {key} = {styled_value}")
