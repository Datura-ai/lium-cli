"""Config get command implementation."""

import click

from lium.cli import ui
from lium.cli.utils import handle_errors
from . import validation
from .actions import GetConfigAction


def mask_value(value: str, key: str) -> str:
    """Mask sensitive values."""
    if key.endswith('api_key') and value:
        return value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
    return value


@click.command(name="get")
@click.argument("key")
@handle_errors
def config_get_command(key: str):
    """Get a configuration value."""

    # Validate
    valid, error = validation.validate(key)
    if not valid:
        ui.error(error)
        return

    # Execute
    ctx = {"key": key}

    action = GetConfigAction()
    result = action.execute(ctx)

    if not result.ok:
        ui.error(result.error)
        return

    value = result.data.get("value")
    styled_value = mask_value(value, key)
    ui.info(styled_value)
