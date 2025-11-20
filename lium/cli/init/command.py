"""Init command implementation."""

import click

from lium.cli import ui
from lium.cli.settings import config
from lium.cli.utils import handle_errors
from .actions import SetupApiKeyAction, SetupSshKeyAction


@click.command("init")
@handle_errors
def init_command():
    """Initialize Lium CLI configuration.

    Sets up API key and SSH key configuration for first-time users.

    Example:
      lium init    # Interactive setup wizard
    """

    # Setup API key
    api_action = SetupApiKeyAction()
    api_result = api_action.execute({})

    if not api_result.ok:
        ui.error(api_result.error)
        return

    # Setup SSH key
    ssh_action = SetupSshKeyAction()
    ssh_result = ssh_action.execute({})

    if not ssh_result.ok:
        ui.error(ssh_result.error)
