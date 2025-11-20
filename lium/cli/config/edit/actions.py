import os
import sys
import subprocess

from lium.cli.actions import ActionResult
from lium.cli.settings import config


class EditConfigAction:
    """Edit config file."""

    def execute(self, ctx: dict) -> ActionResult:
        """Execute config edit."""
        config_file = config.get_config_path()
        editor = os.environ.get('EDITOR', 'nano' if sys.platform != 'win32' else 'notepad')

        try:
            subprocess.run([editor, str(config_file)], check=True)
            return ActionResult(ok=True, data={})
        except subprocess.CalledProcessError:
            return ActionResult(ok=False, data={}, error=f"Failed to open editor: {editor}")
        except FileNotFoundError:
            return ActionResult(ok=False, data={}, error=f"Editor not found: {editor}")
